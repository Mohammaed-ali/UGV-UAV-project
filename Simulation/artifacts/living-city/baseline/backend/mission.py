"""Measured-state mission authority for the independent simulation."""
from __future__ import annotations
import math,time,uuid,json
from pathlib import Path
from .config import Mission,scene,slot,wrap
from .rack import Carousel,BASE_Z,PAD_Z,UPPER_Z

TERMINAL={'STORED','DOCKED','FAULT'}
GROUND={'STORED','DOCKED','PREPARING','ARMING','RELEASING'}

def distance(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

class Engine:
    def __init__(self,root,runtime,vision):
        self.root=root;self.runtime=runtime;self.vision=vision;self.config=Mission();self.run_id=str(uuid.uuid4());self.state='DRAFT';self.stop_index=0;self.events=[];self.drones={};self.dock_owner=None;self.launch_owner=None;self.last_launch=-100.;self.last_time=0.;self.hold=False;self.abort=False;self.tracks=[];self.seen_commands={};self.last_log=0.;self.carousel=Carousel();self.drive_watch=None;self.reset_drones()
    def reset_drones(self):
        self.drones={s['id']:{**s,'state':'STORED','entered':0.,'battery':None,'target':None,'reason':None,'deployed':False,'retry':0,'search_start':None,'goal':None,'contact_since':None} for s in [slot(i) for i in range(8)]}
    def event(self,message,kind='info',drone=None):
        row={'id':len(self.events)+1,'time':round(self.now(),2),'message':message,'kind':kind,'drone':drone};self.events.append(row)
        if len(self.events)>200:self.events=self.events[-200:]
    def now(self):return self.runtime.gz.sim_time if self.runtime.gz else 0.
    def configure(self,config):
        if self.runtime.state in ('starting','running','stopping'):raise ValueError('Reset the simulation before editing its world or mission.')
        self.config=config;self.vision.confidence=config.confidence;self.run_id=str(uuid.uuid4());self.reset_drones();self.events=[];self.state='DRAFT';self.stop_index=0;self.tracks=[]
        # Simulation time restarts at zero. Corridor reservations and timers
        # belong to the old run, including when it ended during recovery.
        self.dock_owner=None;self.launch_owner=None;self.last_launch=-100.;self.last_time=0.;self.last_log=0.
        self.hold=False;self.abort=False;self.seen_commands.clear();self.carousel=Carousel();self.drive_watch=None
        self.event('Mission configuration saved')
    def command(self,name,did=None):
        if name=='initialize':self.runtime.initialize(self.config);self.state='INITIALIZING';self.event('Initializing Gazebo and PX4')
        elif name=='start':
            if self.runtime.state!='running':raise ValueError('Initialize the physics runtime first.')
            if self.state not in ('READY',):raise ValueError('Mission cannot start from the current state.')
            active=[d for s in self.config.stops for d in s.drones]
            if active and not self.vision.detector_ready:raise ValueError('The object detector model is missing or unavailable. Prepare the detector before flight.')
            if active and not self.vision.tag_ready:raise ValueError('The AprilTag detector is unavailable.')
            self.state='DRIVING';self.event('Mission started · following route')
        elif name=='hold':
            if self.state not in ('DRIVING','DEPLOYING','RECOVERING'):raise ValueError('No active mission to hold.')
            self.hold=True
            for d in self.drones.values():
                if d['state'] not in TERMINAL:
                    p=self.runtime.fleet.status(d['id'])['position'] if self.runtime.fleet else None
                    if p:self.set_goal(d,p)
            self.event('Mission held')
        elif name=='resume':self.hold=False;self.drive_watch=None;self.event('Mission resumed')
        elif name in ('recall','recall_all','abort'):
            if name=='recall' and did not in self.drones:raise ValueError('Select a valid drone.')
            self.hold=False
            if name=='abort':self.abort=True;self.state='RECOVERING'
            for d in self.drones.values():
                if name!='recall' or d['id']==did:
                    if d['deployed'] and d['state'] not in TERMINAL and d['state'] not in ('LANDING','LATCHING','RETRACTING'):
                        self.transition(d,'RETURNING','Operator recall')
                    elif d['state']=='PREPARING':
                        self.transition(d,'STORED','Launch cancelled');self.launch_owner=None
            self.event('Mission abort requested' if name=='abort' else 'Return requested')
        elif name=='pause_world':
            if not self.runtime.gz:raise ValueError('Simulation is offline.')
            self.runtime.gz.pause(not self.runtime.gz.paused)
        else:raise ValueError('Unknown command.')
    def pose(self,did):return self.runtime.gz.poses.get(did) if self.runtime.gz else None
    def tray_pose(self,d):
        ugv=self.pose('carrier')
        if not ugv:return None
        measured=self.carousel.measured(self.runtime.gz,d['level'])
        x=d['x'];y=d['y']+measured['y'];a=ugv['yaw']
        return [ugv['position'][0]+x*math.cos(a)-y*math.sin(a),ugv['position'][1]+x*math.sin(a)+y*math.cos(a),ugv['position'][2]+measured['z']+PAD_Z+.0295]
    def carousel_can_move(self):
        gz=self.runtime.gz;fleet=self.runtime.fleet;ugv=self.pose('carrier')
        if not gz or not ugv or self.launch_owner or self.dock_owner or abs((gz.odom or {}).get('speed',0))>.03:return False
        for d in self.drones.values():
            if d['state'] in ('STORED','DOCKED'):
                if gz.latches.get(d['id'])!='attached':return False
                if fleet and d['id'] in fleet.ids and fleet.status(d['id'])['armed']:return False
            else:
                p=self.pose(d['id'])
                if p and math.hypot(p['position'][0]-ugv['position'][0],p['position'][1]-ugv['position'][1])<4.5 and p['position'][2]<ugv['position'][2]+UPPER_Z+2:return False
        return True
    def index_carousel(self,level):
        if self.carousel.request(level,self.carousel_can_move()):
            self.event(f'Carousel indexing · original {level} tray moving to flight deck')
        return self.carousel.ready(self.runtime.gz,level)
    def recovery_level(self,stop):
        group=[self.drones[did] for did in stop.drones]
        lower_pending=any(d['level']=='lower' and d['deployed'] and d['state'] not in ('DOCKED','FAULT') for d in group)
        return 'lower' if lower_pending else 'upper'
    def transition(self,d,state,reason=None):
        d['state']=state;d['entered']=self.now()
        if state in ('RETURNING','DOCKED','FAULT') and self.runtime.gz:self.runtime.gz.camera(d['id'],False)
        if reason:d['reason']=reason
        self.event(f'{d["id"].upper()} · {state.replace("_"," ").lower()}'+(f' · {reason}' if reason else ''),'warning' if state=='FAULT' else 'info',d['id'])
    def set_goal(self,d,p):
        d['goal']=list(p)
        if self.runtime.fleet:self.runtime.fleet.goal(d['id'],p,self.pose('carrier')['yaw'] if self.pose('carrier') else 0.)
    def tick(self):
        if self.runtime.state=='error':
            if self.state!='ERROR':self.state='ERROR';self.event(self.runtime.error or 'Runtime error','error')
            return
        if self.runtime.state!='running' or self.runtime.gz is None:return
        gz=self.runtime.gz;now=gz.sim_time;dt=max(0,min(.25,now-self.last_time));self.last_time=now
        if not gz.paused:
            was_moving=self.carousel.moving;self.carousel.tick(gz,0 if self.hold or self.state=='FAULT' else dt)
            if was_moving and not self.carousel.moving:self.event(f'Carousel locked · original {self.carousel.active} tray at flight deck')
            if self.carousel.error:
                if self.state!='FAULT':self.state='FAULT';self.event(self.carousel.error,'error')
                return
        self.vision.searching={d['id'] for d in self.drones.values() if d['state'] in ('TAKEOFF','SEARCHING','HOVERING','LOITERING','OBSERVING')}
        if self.state=='INITIALIZING':self.state='READY';self.event('Simulation ready · physical telemetry connected')
        if self.state in ('DRAFT','READY','COMPLETE','ABORTED','FAULT'):return
        if gz.paused:return
        if time.monotonic()-gz.received>3:
            self.state='FAULT';self.event('Physics telemetry lost. Mission stopped.','error');return
        if self.hold:
            self.drive_watch=None
            gz.drive(0,0)
            for d in self.drones.values():
                d['entered']+=dt
                if d['search_start'] is not None:d['search_start']+=dt
            return
        carrier=self.pose('carrier')
        if not carrier:return
        stop=self.config.stops[min(self.stop_index,len(self.config.stops)-1)]
        if self.state=='DRIVING':
            x,y,_=carrier['position'];dx,dy=stop.x-x,stop.y-y;dist=math.hypot(dx,dy);err=wrap(math.atan2(dy,dx)-carrier['yaw'])
            if dist>.45:
                speed=min(self.config.ugv_speed,dist*.8)*max(0,math.cos(err))
                if speed>.08:
                    if self.drive_watch is None or self.drive_watch[2]!=self.stop_index or self.drive_watch[1]-dist>.25:self.drive_watch=(now,dist,self.stop_index)
                    elif now-self.drive_watch[0]>8:
                        self.hold=True;gz.drive(0,0);self.event(f'Carrier blocked toward {stop.label}: no measured forward progress for 8 seconds. Mission held.','warning');return
                else:self.drive_watch=None
                gz.drive(speed,max(-.6,min(.6,err*1.3)))
            else:
                self.drive_watch=None
                gz.drive(0,0)
                if gz.odom and abs(gz.odom['speed'])<.04:
                    self.state='DEPLOYING';self.event(f'Arrived at {stop.label} · {len(stop.drones)} drones scheduled')
            return
        gz.drive(0,0)
        if self.state=='DEPLOYING' and not self.abort:
            pending=sorted([self.drones[d] for d in stop.drones if self.drones[d]['state']=='STORED'],key=lambda d:(d['level']!='upper',d['bay']))
            if pending and not self.launch_owner and not self.dock_owner and now-self.last_launch>=self.config.launch_interval:
                d=pending[0]
                if self.index_carousel(d['level']):self.launch_owner=d['id'];self.transition(d,'PREPARING')
        for d in self.drones.values():
            if d['state'] not in TERMINAL:self.tick_drone(d,stop,dt)
        group=[self.drones[did] for did in stop.drones]
        if (self.abort or all(d['state']=='DOCKED' for d in group)) and not any(d['state'] not in TERMINAL for d in self.drones.values()):
            if any(d['state']=='FAULT' for d in self.drones.values()):self.state='FAULT';return
            if not self.index_carousel('upper'):return
            if self.abort:self.state='ABORTED';self.event('Mission aborted · deployed aircraft recovered')
            elif self.stop_index+1<len(self.config.stops):self.stop_index+=1;self.state='DRIVING';self.event('Recovery complete · proceeding to next stop')
            else:self.state='COMPLETE';self.event('Mission complete · all deployed aircraft docked','success')
        if now-self.last_log>.5:
            self.last_log=now;path=self.root/'artifacts/runs'/f'{self.run_id}.jsonl';path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('a') as f:f.write(json.dumps(self.snapshot())+'\n')
    def tick_drone(self,d,stop,dt):
        gz=self.runtime.gz;fleet=self.runtime.fleet;did=d['id'];now=self.now();state=d['state'];p=self.pose(did);tray=self.tray_pose(d)
        if not p or not tray or not fleet:return
        health=fleet.status(did);d['battery']=health['battery'];pos=health['position'] or p['position'];age=now-d['entered']
        if health['battery'] is not None and health['battery']<self.config.battery_return and state in ('SEARCHING','OBSERVING','HOVERING','LOITERING'):
            self.transition(d,'RETURNING','Battery reserve');state='RETURNING'
        if d['deployed'] and not health['fresh']:
            fleet.stop_control(did);self.transition(d,'FAULT','PX4 telemetry stale; native failsafe owns aircraft');self.state='FAULT';return
        if age>120 and state not in ('SEARCHING','OBSERVING','LOITERING','HOVERING','RETURNING'):
            self.transition(d,'FAULT',f'{state.lower()} timed out');self.state='FAULT';return
        alt=self.config.altitude+(int(did[-2:])-1)*.9
        if state=='PREPARING':
            if self.carousel.ready(gz,d['level']) and health['ready'] and abs((gz.odom or {}).get('speed',0))<.04:
                gz.camera(did);d['launch_xy']=list(pos[:2]);d['camera_started']=now
                self.set_goal(d,[*d['launch_xy'],alt]);self.transition(d,'ARMING')
        elif state=='ARMING':
            self.set_goal(d,[*d.get('launch_xy',pos[:2]),alt]);fleet.launch(did)
            if health['armed'] and health['offboard']:self.transition(d,'RELEASING')
        elif state=='RELEASING':
            gz.latch(did,False)
            if gz.latches.get(did)=='detached':
                d['deployed']=True;d['search_start']=now;self.transition(d,'TAKEOFF')
        elif state=='TAKEOFF':
            self.set_goal(d,[*d.get('launch_xy',pos[:2]),alt])
            if p['position'][2]>tray[2]+2:
                if self.launch_owner==did:self.launch_owner=None;self.last_launch=now
                self.check_detection(d,stop)
            if d['state']=='TAKEOFF' and abs(pos[2]-alt)<.5:
                d['search_start']=now;self.transition(d,'SEARCHING')
        elif state in ('SEARCHING','HOVERING','LOITERING'):
            if state=='SEARCHING':
                radius=min(stop.search_radius,6+int(did[-2:])*.6)
                theta=((int(did[-2:])-1)%8)*math.pi/4+(now-d['search_start'])*self.config.flight_speed/radius
                self.set_goal(d,[stop.x+radius*math.cos(theta),stop.y+radius*math.sin(theta),alt])
            elif state=='LOITERING':
                theta=age*self.config.flight_speed/self.config.loiter_radius;center=d['loiter_center'];self.set_goal(d,[center[0]+self.config.loiter_radius*math.cos(theta),center[1]+self.config.loiter_radius*math.sin(theta),alt])
            self.check_detection(d,stop)
            if d['state'] not in ('SEARCHING','HOVERING','LOITERING'):return
            timeout=stop.search_timeout if stop.search_timeout is not None else self.config.search_timeout
            if state=='SEARCHING' and now-d['search_start']>=timeout:
                policy=self.config.no_target_policy
                if policy=='return':self.transition(d,'RETURNING','Search timed out')
                else:
                    d['loiter_center']=list(pos);self.set_goal(d,pos);self.transition(d,'HOVERING' if policy=='hover' else 'LOITERING','No matching target')
            if state in ('HOVERING','LOITERING') and age>=(stop.loiter_seconds if stop.loiter_seconds is not None else self.config.loiter_seconds):self.transition(d,'RETURNING','No-target duration finished')
        elif state=='OBSERVING':
            target=d['target'];x,y,_=target['position'];angle=math.atan2(pos[1]-y,pos[0]-x);self.set_goal(d,[x+self.config.standoff*math.cos(angle),y+self.config.standoff*math.sin(angle),alt])
            if age>=self.config.observation_seconds:self.transition(d,'RETURNING','Observation complete')
        elif state=='RETURNING':
            # Reserve a distinct holding point while awaiting the single final approach corridor.
            ugv=self.pose('carrier')['position'];idx=int(did[-2:])-1;a=idx*math.pi/4;holding=[ugv[0]+8*math.cos(a),ugv[1]+8*math.sin(a),alt]
            self.set_goal(d,holding)
            waiting_to_launch=not self.abort and any(self.drones[x]['state'] in ('STORED','PREPARING','ARMING','RELEASING','TAKEOFF') for x in stop.drones)
            if not waiting_to_launch and d['level']==self.recovery_level(stop) and self.dock_owner is None and self.launch_owner is None:
                if self.index_carousel(d['level']) and distance(pos,holding)<1:
                    self.dock_owner=did;self.vision.landing.add(did);self.transition(d,'RECOVERY_QUEUE')
        elif state=='RECOVERY_QUEUE':
            if self.carousel.ready(gz,d['level']):
                gz.camera(did);d.pop('descent_z',None);self.set_goal(d,[tray[0],tray[1],tray[2]+3]);self.transition(d,'TAG_ACQUIRE')
        elif state in ('TAG_ACQUIRE','ALIGNING','DESCENDING'):
            obs=getattr(self.vision,'tag_latest',self.vision.latest).get(did,{});tag=next((t for t in obs.get('tags',[]) if t['id']==d['tag_id'] and t.get('relative_position') is not None),None)
            fresh=now-obs.get('time',-100)<.5 and obs.get('sync_error',999)<.25
            if not tag or not fresh:
                if state!='TAG_ACQUIRE':
                    if d.get('tag_lost_since') is None:
                        d['tag_lost_since']=now;self.set_goal(d,list(pos))
                    # Stop descending immediately. A brief delayed frame must not
                    # consume a complete recovery attempt, or relax freshness.
                    if now-d['tag_lost_since']<2:return
                    d['retry']+=1;d['tag_lost_since']=None;d.pop('descent_z',None)
                    self.set_goal(d,[pos[0],pos[1],max(pos[2],tray[2]+3)])
                    if d['retry']>self.config.landing_retries:
                        reason='Landing camera observations stayed stale' if not fresh else 'Assigned landing tag stayed out of view'
                        self.transition(d,'FAULT',reason+'; recovery requires operator');self.state='FAULT'
                    else:self.transition(d,'TAG_ACQUIRE','Reacquiring landing tag')
                return
            d['tag_lost_since']=None
            offset=tag['relative_position'];ex,ey=offset[:2];height=-offset[2];error=math.hypot(ex,ey);d['tag_error']=error
            # Relative image displacement is applied in the PX4 control frame.
            # Never subtract an EKF position from a Gazebo-world tag position.
            if state=='TAG_ACQUIRE' and height>3.5:
                self.set_goal(d,[pos[0]+max(-.8,min(.8,ex)),pos[1]+max(-.8,min(.8,ey)),pos[2]-height+3]);return
            # Altitude follows the vision-derived tag plane; coarse tray telemetry never substitutes for a missing tag.
            if error<.07:
                d['descent_z']=max(pos[2]-height+.49,max(pos[2]-.35,d.get('descent_z',pos[2])-.28*dt))
            else:d['descent_z']=pos[2]
            desired_z=d['descent_z']
            self.set_goal(d,[pos[0]+max(-.4,min(.4,ex)),pos[1]+max(-.4,min(.4,ey)),desired_z])
            if state=='TAG_ACQUIRE':self.transition(d,'ALIGNING')
            if error<.07 and state=='ALIGNING':self.transition(d,'DESCENDING')
            if error<.06 and height<.55 and math.hypot(*health['velocity'][:2])<.15:
                fleet.command(did,21);fleet.stop_control(did);d['last_tag_time']=obs['time'];self.transition(d,'LANDING')
        elif state=='LANDING':
            touching,stamp=gz.contacts.get(did,(False,-100))
            if touching and now-stamp<.5 and math.sqrt(sum(v*v for v in health['velocity']))<.25:
                if d['contact_since'] is None:d['contact_since']=now
                if now-d['contact_since']>.7 and health['landed']:
                    fleet.disarm(did)
                    if not health['armed']:gz.latch(did,True);self.transition(d,'LATCHING')
            else:d['contact_since']=None
        elif state=='LATCHING':
            gz.latch(did,True)
            if gz.latches.get(did)=='attached':
                self.transition(d,'DOCKED');self.dock_owner=None;self.vision.landing.discard(did);fleet.stop_control(did)
    def check_detection(self,d,stop):
        if d.get('target'):return
        obs=getattr(self.vision,'object_latest',self.vision.latest).get(d['id'],{})
        if self.now()-obs.get('time',-100)>1 or obs.get('sync_error',999)>.25:return
        candidates=[x for x in obs.get('detections',[]) if x['class']==(stop.target_class or self.config.target_class) and x['position'] is not None]
        if not candidates:return
        previous=d.get('candidate')
        associated=[x for x in candidates if previous and distance(previous['position'],x['position'])<3]
        candidate=min(associated,key=lambda x:distance(previous['position'],x['position'])) if associated else max(candidates,key=lambda x:x['confidence'])
        # Require separate image observations, not repeated reads of one frame.
        if d.get('candidate_time')==obs['time']:return
        continuous=previous and obs['time']-d.get('candidate_time',-100)<2 and distance(previous['position'],candidate['position'])<3
        d['confirmations']=d.get('confirmations',0)+1 if continuous else 1
        d['candidate']=candidate;d['candidate_time']=obs['time']
        required=2 if candidate['confidence']>=.65 else 3
        if d['confirmations']>=required:
            d['detection_latency']=round(obs['time']-d.get('camera_started',d['entered']),2)
            target={**candidate,'id':f'track-{len(self.tracks)+1:03d}','drone':d['id'],'time':obs['time']};self.tracks.append(target);d['target']=target;self.transition(d,'OBSERVING',f'{candidate["class"]} confirmed from camera')
    def snapshot(self):
        gz=self.runtime.gz;fleet=self.runtime.fleet;now=self.now();rows=[]
        for did,d in self.drones.items():
            p=self.pose(did);health=fleet.status(did) if fleet and did in fleet.ids else {}
            fallback=[self.config.start.x+d['x'],self.config.start.y+d['y'],BASE_Z+d['z']+.26]
            rows.append({'id':did,'bay':d['bay'],'level':d['level'],'tag_id':d['tag_id'],'state':d['state'],'position':p['position'] if p else fallback,'quaternion':p['quaternion'] if p else [0,0,0,1],'measured':p is not None,'battery':health.get('battery'),'ready':health.get('ready',False),'armed':health.get('armed',False),'mode':health.get('mode'),'telemetry_age':health.get('age'),'target':d['target'],'reason':d['reason'],'extension':abs(self.carousel.measured(gz,d['level'])['y']),'tray_position':self.tray_pose(d),'estimated_position':health.get('position'),'detection_latency':d.get('detection_latency'),'camera_active':did in getattr(gz,'enabled_cameras',set()) if gz else False,'latched':gz.latches.get(did)=='attached' if gz else True,'tag_error':d.get('tag_error'),'phase_seconds':round(max(0,now-d['entered']),1),'vision':self.vision.latest.get(did)})
        carrier=self.pose('carrier') or {'position':[self.config.start.x,self.config.start.y,BASE_Z],'quaternion':[0,0,0,1],'yaw':0}
        return {'run_id':self.run_id,'state':self.state,'hold':self.hold,'sim_time':round(now,2),'stop_index':self.stop_index,'runtime':self.runtime.health(),'physics':{'real_time_factor':round(gz.rtf,2) if gz else 0,'paused':gz.paused if gz else False,'age':round(time.monotonic()-gz.received,2) if gz and gz.received else None},'carrier':{**carrier,'speed':round((gz.odom or {}).get('speed',0),2) if gz else 0},'carousel':self.carousel.snapshot(gz),'wheel_angles':{k:v for k,v in (gz.joints if gz else {}).items() if k.startswith('wheel_')},'drones':rows,'tracks':self.tracks,'events':self.events[-60:],'perception':{'detector_ready':self.vision.detector_ready,'tag_ready':self.vision.tag_ready,'error':self.vision.error}}
