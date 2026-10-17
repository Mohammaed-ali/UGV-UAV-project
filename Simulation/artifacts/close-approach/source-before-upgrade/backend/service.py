"""Operator-triggered overhead close hold using image identity and rendered depth.

No actor IDs or actor poses enter this controller. No payload action is simulated.
"""
import math
import numpy as np
from .transport import quaternion_matrix

AIRCRAFT_RADIUS = .50  # Conservative spherical envelope, including gear/rotors.
RANGE_TOPIC = '/fieldlab/{did}/proximity'
FOV = 1.22
ACTIVE = {'APPROACHING','HOLDING','RETREATING'}


def decode_depth(msg):
    """Read the Gazebo depth camera's row-strided float32 image, never RGB."""
    if msg.width < 2 or msg.height < 2 or msg.step < msg.width*4:
        return None
    descriptor = msg.DESCRIPTOR.fields_by_name['pixel_format_type'].enum_type
    fmt = descriptor.values_by_number.get(msg.pixel_format_type)
    if fmt is None or fmt.name != 'R_FLOAT32':
        return None
    if len(msg.data) < msg.height*msg.step:
        return None
    return np.ndarray((msg.height,msg.width),dtype='<f4',buffer=msg.data,
                      strides=(msg.step,4)).copy()


def depth_observation(packet,pose,current,target,now):
    """Metric clearance to observed surfaces and a camera-ROI surface anchor."""
    if packet is None or pose is None or target is None:
        return None
    stamp=packet['time']
    if not 0 <= now-stamp <= .4 or abs(stamp-target['last_seen']) > .3:
        return None
    image=packet['image'];height,width=image.shape
    valid=np.isfinite(image)&(image>.05)&(image<100.)
    if valid.sum()<32:
        return None
    image=np.where(valid,image,0.)
    yy,xx=np.indices(image.shape)
    focal=width/(2*math.tan(FOV/2))
    # Camera optical (right, down, forward) -> aircraft body (-down,-right,-forward).
    points=np.stack((-(yy-height/2)/focal*image,
                     -(xx-width/2)/focal*image,-image-.08),axis=-1)
    rotation=quaternion_matrix(pose['quaternion'])
    world=points@rotation.T+np.asarray(pose['position'])
    gaps=np.linalg.norm(world[valid]-np.asarray(current),axis=1)-AIRCRAFT_RADIUS
    nearest=float(np.min(gaps));nearest_point=world[valid][np.argmin(gaps)].tolist()
    x,y,w,h=target['box']
    x0=max(0,int((x+w*.15)/640*width));x1=min(width,int((x+w*.85)/640*width)+1)
    y0=max(0,int((y+h*.10)/480*height));y1=min(height,int((y+h*.90)/480*height)+1)
    if x1-x0<2 or y1-y0<2:
        return None
    roi=valid[y0:y1,x0:x1]
    surface=world[y0:y1,x0:x1][roi]
    # Use the visible object's upper surface, not surrounding ground in its box.
    surface=surface[surface[:,2]>.30]
    if len(surface)<4:
        return None
    top=surface[surface[:,2]>=np.percentile(surface[:,2],65)]
    anchor=np.median(top,axis=0)
    tilt=math.acos(float(np.clip(rotation[2,2],-1,1)))
    return {'surface_point':anchor.tolist(),'nearest_point':nearest_point,'clearance_m':nearest,
            'alignment_m':float(np.linalg.norm(anchor[:2]-np.asarray(current[:2]))),
            'range_age':now-stamp,'time':stamp,'tilt':tilt}


class CloseApproach:
    def __init__(self,config):
        self.config=config;self.state='IDLE';self.reason=None;self.target_point=None
        self.clearance=config.approach_clearance;self.started=0.;self.last_time=0.
        self.ready_since=None;self.alt_goal=None;self.observation=None;self.events=[];self.range_missing_since=None

    @property
    def active(self):return self.state in ACTIVE

    def phase(self,state,now,detail):
        if state!=self.state:
            self.state=state;self.events.append({'time':round(now,2),'state':state,'detail':detail})
            self.events=self.events[-20:]
        self.reason=detail

    def start(self,now,pos,clearance):
        if self.active:raise ValueError('A close-approach operation is already active.')
        self.clearance=clearance;self.started=now;self.last_time=now
        self.alt_goal=pos[2];self.ready_since=None
        self.observation=None;self.target_point=None;self.range_missing_since=None
        self.phase('APPROACHING',now,'Waiting for aligned RGB and depth observations')

    def retreat(self,now,reason):
        if not self.active:return
        self.ready_since=None;self.phase('RETREATING',now,reason)

    def stop(self,now,reason):
        if self.active:self.phase('CANCELLED',now,reason)

    def freeze(self,now):
        self.last_time=now;self.ready_since=None

    def sample(self,engine,d,pos,target,now):
        packet=getattr(engine.runtime.gz,'depth_packets',{}).get(d['id'])
        if not packet:return None
        pose,sync=engine.runtime.fleet.perception_pose(d['id'],packet['time'])
        if sync>.25:return None
        return depth_observation(packet,pose,pos,target,now)

    def identity_ok(self,target,did):
        return bool(target and target['age']<=.5 and not target['ambiguous']
                    and target['identity_confidence']>=self.config.reacquire_confidence
                    and target['drone']==did)

    def tick(self,engine,d,pos,alt,target):
        if not self.active:return False
        now=engine.now();dt=max(0.,min(.25,now-self.last_time));self.last_time=now
        if self.state=='RETREATING':
            # Climb vertically before resuming normal survey-altitude tracking.
            engine.set_goal(d,[pos[0],pos[1],max(alt,pos[2])])
            if pos[2]>=alt-.35:
                engine.runtime.gz.proximity(d['id'],False)
                self.phase('CANCELLED',now,'Normal tracking resumed')
            return True
        if not self.identity_ok(target,d['id']):
            self.retreat(now,'Camera identity lost or uncertain; climb before reacquisition')
            return self.tick(engine,d,pos,alt,target)
        if max(abs(target['position'][0]),abs(target['position'][1]))>self.config.flight_boundary-2:
            self.retreat(now,'Target is too close to the operating boundary')
            return self.tick(engine,d,pos,alt,target)
        velocity=target['velocity']
        if math.hypot(*velocity)>self.config.flight_speed*.8:
            self.retreat(now,'Target is moving too fast for a controlled close approach')
            return self.tick(engine,d,pos,alt,target)
        obs=self.sample(engine,d,pos,target,now);self.observation=obs
        if obs is None:
            self.ready_since=None
            if self.range_missing_since is None:self.range_missing_since=now
            if now-self.started>3 and now-self.range_missing_since>.35:
                self.retreat(now,'Fresh synchronized target depth is unavailable')
                return self.tick(engine,d,pos,alt,target)
            self.alt_goal=max(self.alt_goal,pos[2])
            self.reason='Holding altitude while waiting for synchronized target depth'
            engine.set_goal(d,list(pos));return True
        self.range_missing_since=None
        self.target_point=obs['surface_point'];gap=obs['clearance_m']
        if gap<self.clearance+.12:
            self.retreat(now,'Measured depth clearance reached the protective buffer')
            return self.tick(engine,d,pos,alt,target)
        if obs['tilt']>math.radians(18):
            self.retreat(now,'Aircraft tilt is too large for close operation')
            return self.tick(engine,d,pos,alt,target)
        point=self.target_point
        wanted=[point[0]+velocity[0]*.15,point[1]+velocity[1]*.15,
                point[2]+AIRCRAFT_RADIUS+self.clearance+.25]
        if wanted[2]>alt:
            self.retreat(now,'Observed surface is too high for the configured tracking altitude')
            return self.tick(engine,d,pos,alt,target)
        aligned=obs['alignment_m']<.35
        # Slow descent only while centred; range and identity are checked every tick.
        if aligned:self.alt_goal=max(wanted[2],self.alt_goal-self.config.approach_speed*dt)
        else:self.alt_goal=max(pos[2],self.alt_goal,wanted[2])
        wanted[2]=self.alt_goal
        ready=aligned and abs(pos[2]-wanted[2])<.18 and abs(gap-(self.clearance+.25))<.22 and obs['tilt']<math.radians(10)
        health=engine.runtime.fleet.status(d['id'])
        measured_v=health.get('velocity',[0.,0.,0.])
        relative=math.hypot(measured_v[0]-velocity[0],measured_v[1]-velocity[1])
        ready=ready and relative<.6 and abs(measured_v[2])<.25
        if ready:
            if self.ready_since is None:self.ready_since=now
        else:self.ready_since=None
        if self.ready_since is not None and now-self.ready_since>=.75:
            self.phase('HOLDING',now,'Holding above the selected target at the requested minimum clearance')
        elif self.state=='HOLDING':self.phase('APPROACHING',now,'Restabilizing close hold')
        else:self.reason='Descending slowly' if aligned else 'Aligning above the selected camera target'
        d['target']=target;engine.set_goal(d,wanted)
        return True

    def snapshot(self,now):
        obs=self.observation or {}
        age=now-obs['time'] if 'time' in obs else None
        return {'state':self.state,'reason':self.reason,'requested_clearance_m':self.clearance,
                'aircraft_radius_m':AIRCRAFT_RADIUS,
                'measured_clearance_m':obs.get('clearance_m') if age is not None and 0<=age<=.4 else None,
                'range_age':age,'alignment_m':obs.get('alignment_m'),'target_point':self.target_point,'nearest_point':obs.get('nearest_point'),
                'events':self.events,'approach_direction':'overhead'}
