"""Measured-state mission authority for the independent simulation."""
from __future__ import annotations
import math,time,uuid,json
from pathlib import Path
from .config import Mission,scene,slot,wrap,spawn_pose
from .city import search_classes,matches_class
from .rack import Carousel,BASE_Z,PAD_Z,UPPER_Z

TERMINAL={'STORED','DOCKED','FAULT'}
GROUND={'STORED','DOCKED','PREPARING','ARMING','RELEASING'}

def distance(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

class Engine:
    def __init__(self,root,runtime,vision):
        self.root=root;self.runtime=runtime;self.vision=vision;self.config=Mission();self.run_id=str(uuid.uuid4());self.state='DRAFT';self.stop_index=0;self.events=[];self.drones={};self.dock_owner=None;self.launch_owner=None;self.last_launch=-100.;self.last_time=0.;self.hold=False;self.abort=False;self.tracks=[];self.seen_commands={};self.last_log=0.;self.carousel=Carousel();self.drive_watch=None;self.world_was_paused=False;self.resume_deadline=None;self.reset_drones()
    def reset_drones(self):
        self.city=None;self.drive_waypoint=1;self.follow=None;self.flight_planner=None;self.follow_stop=None
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
        self.dock_owner=None;self.launch_owner=None;self.last_launch=-100.;self.last_time=0.;self.last_log=0.;self.logged_event_id=0
        self.hold=False;self.abort=False;self.seen_commands.clear();self.carousel=Carousel();self.drive_watch=None;self.world_was_paused=False;self.resume_deadline=None
        self.city=None;self.follow=None;self.follow_stop=None;self.flight_planner=None;self.drive_waypoint=1;self.log_limited=False
        from .storage import prune_mission_logs
        prune_mission_logs(self.root,keep=self.run_id)
        self.event('Mission configuration saved')
        if hasattr(self.vision,'registry'):self.vision.registry.clear()
        if config.living_city:
            from .navigation import FlightPlanner
            self.flight_planner=FlightPlanner(scene(config)['objects'],config.flight_boundary)
    def select_target(self,key):
        if self.state=='TRACKING':raise ValueError('Stop the current tracking flight before selecting another target; use identity confirmation for reacquisition.')
        if not self.config.living_city or not self.config.tracking_enabled:raise ValueError('Enable living-city tracking in the mission configuration.')
        self.vision.registry.select(key,self.now());self.event(f'Selected {key} from camera catalogue')
    def start_tracking(self,key=None):
        if self.runtime.state!='running' or not self.runtime.fleet:raise ValueError('Initialize a tracking-capable runtime first.')
        if not self.config.living_city or not self.config.tracking_enabled:raise ValueError('Enable living-city tracking in the mission configuration.')
        key=key or self.vision.registry.selected
        target=self.vision.registry.get(key,self.now()) if key else None
        if target is None:raise ValueError('Select a confirmed camera target first.')
        if self.follow and self.follow.state not in ('DOCKED','FINISHED'):raise ValueError('A tracking mission is already active.')
        if self.state not in ('DEPLOYING','RECOVERING','COMPLETE') or self.abort:raise ValueError('Start a survey flight before tracking a camera target.')
        airborne=[];available=[]
        for candidate in self.drones.values():
            did=candidate['id']
            if did not in self.runtime.fleet.ids:continue
            if self.config.tracking_uav!='auto' and did!=self.config.tracking_uav:continue
            health=self.runtime.fleet.status(did)
            flying=health['fresh'] and health['armed'] and health['offboard'] and health['position'] is not None
            if flying and candidate['state'] in ('TAKEOFF','SEARCHING','OBSERVING','HOVERING','LOITERING','RETURNING') and self.dock_owner!=did:
                tray=self.tray_pose(candidate)
                if candidate['state']!='TAKEOFF' or tray and health['position'][2]>tray[2]+2:airborne.append(candidate)
            recovered=health['fresh'] and not health['armed'] and health['landed'] and health['position'] is not None and self.runtime.gz.latches.get(did)=='attached'
            if candidate['level']=='upper' and candidate['state'] in ('STORED','DOCKED') and (health['ready'] or recovered):available.append(candidate)
        # The latest camera observer keeps its image lock. A lower-tray aircraft
        # already in flight is equally eligible; no carousel move is needed.
        airborne.sort(key=lambda d:(d['id']!=target['drone'],d['state']!='OBSERVING'))
        if not (airborne or available):raise ValueError('No healthy airborne or ready upper-tray aircraft is available for tracking.')
        d=(airborne or available)[0];in_flight=d in airborne
        if not in_flight:
            if any(other['state'] not in TERMINAL for other in self.drones.values() if other['id']!=d['id']) or self.launch_owner or self.dock_owner:
                raise ValueError('No airborne tracking aircraft is available. Finish recovery before relaunching from the tray.')
            if not self.carousel.ready(self.runtime.gz,'upper'):raise ValueError('The upper tray must be locked before relaunching.')
        from .follow import Follow
        from .config import Stop
        public_paths=[{'kind':p['kind'],'points':p['points']} for p in scene(self.config).get('networks',[]) if p['kind'] in ('sidewalk','vehicle')]
        self.vision.registry.select(key,self.now())
        self.follow=Follow(key,d['id'],self.now(),self.config,public_paths);self.follow.initial_ground=d['state']
        if hasattr(self.vision,'depth_targets'):self.vision.depth_targets[d['id']]=key
        if hasattr(self.runtime.gz,'proximity'):self.runtime.gz.proximity(d['id'],True)
        carrier=self.pose('carrier')['position']
        group=[other['id'] for other in self.drones.values() if other['state'] not in TERMINAL or other['id']==d['id']]
        self.follow_stop=Stop(id='tracking',label='Tracking bay',x=carrier[0],y=carrier[1],drones=group)
        d.update(tracking=True,target=None,reason=None,retry=0,contact_since=None)
        self.state='TRACKING';self.hold=False;self.abort=False;self.runtime.gz.drive(0,0)
        if self.launch_owner==d['id']:self.launch_owner=None;self.last_launch=self.now()
        for other in self.drones.values():
            if other['id']==d['id']:continue
            if other['state']=='PREPARING':
                self.runtime.fleet.stop_control(other['id']);self.transition(other,'STORED','Survey launch cancelled for tracking')
                if self.launch_owner==other['id']:self.launch_owner=None
            elif other['state'] in ('SEARCHING','OBSERVING','HOVERING','LOITERING'):
                self.transition(other,'RETURNING','Survey ended; selected target is being followed')
            # An aircraft already arming/releasing finishes its safe takeoff,
            # then returns. An existing AprilTag approach keeps its reservation.
        if not in_flight:
            d['deployed']=False;d['search_start']=None;self.launch_owner=d['id'];self.transition(d,'PREPARING','Selected-target flight')
        else:
            self.transition(d,'TARGET_SEARCHING','Selected-target flight')
            health=self.runtime.fleet.status(d['id'])
            self.follow.tick(self,d,health['position'],self.config.tracking_altitude)
        self.vision.sites[d['id']]='tracking';self.event(f'Tracking mission · {key} · {d["id"].upper()}')
    def start_approach(self,clearance=None):
        if self.runtime.state!='running' or self.state!='TRACKING' or not self.follow or self.follow.cancelled:
            raise ValueError('Start tracking a camera target before closing in.')
        if self.hold or self.runtime.gz.paused:
            raise ValueError('Resume the mission before closing in.')
        if self.follow.state!='TRACKING':
            raise ValueError('Wait for a fresh confirmed tracking lock before closing in.')
        clearance=self.config.approach_clearance if clearance is None else clearance
        if not math.isfinite(clearance) or not .5<=clearance<=10:
            raise ValueError('Minimum clearance must be between 0.5 and 10 meters.')
        d=self.drones[self.follow.drone_id];health=self.runtime.fleet.status(d['id'])
        if not health['fresh'] or not health['armed'] or not health['offboard'] or health['position'] is None or d['state']!='TARGET_TRACKING':
            raise ValueError('The tracking aircraft must have fresh, armed Offboard telemetry.')
        target=self.vision.registry.get(self.follow.target_id,self.now())
        if not self.follow.close.identity_ok(target,d['id']):
            raise ValueError('Wait for a fresh, unambiguous observation from the tracking aircraft.')
        self.follow.close.start(self.now(),health['position'],clearance)
        self.runtime.gz.proximity(d['id'],True)
        self.event(f'{d["id"].upper()} · close approach requested · minimum clearance {clearance:.2f} m')
    def stop_approach(self):
        if self.state!='TRACKING' or not self.follow or not self.follow.close.active:
            raise ValueError('No close approach is active.')
        self.follow.close.retreat(self.now(),'Operator requested a return to normal tracking')
        self.event('Backing off vertically to normal tracking altitude')
    def confirm_target(self,key):
        if not self.follow or self.follow.state not in ('REACQUIRING','SEARCHING','OCCLUDED'):raise ValueError('No uncertain tracking identity to confirm.')
        row=self.vision.registry.get(key,self.now())
        if not row or row['age']>1:raise ValueError('Confirm a candidate with a fresh camera observation.')
        if key not in [c['id'] for c in self.follow.candidates(self.vision.registry,self.now())]:raise ValueError('Candidate does not have matching visual evidence.')
        self.vision.registry.confirm(key,self.now());self.follow.target_id=key;self.event(f'Operator reconfirmed identity as {key}')
        if hasattr(self.vision,'depth_targets'):self.vision.depth_targets[self.follow.drone_id]=key
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
            if self.state not in ('DRIVING','DEPLOYING','RECOVERING','TRACKING'):raise ValueError('No active mission to hold.')
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
            if self.follow and self.state=='TRACKING':
                self.follow.finish(self,'Operator recall' if name!='abort' else 'Operator abort','aborted' if name=='abort' else 'stopped')
            elif name=='abort':self.abort=True;self.state='RECOVERING'
            for d in self.drones.values():
                if name!='recall' or d['id']==did:
                    if d['deployed'] and d['state'] not in TERMINAL and d['state'] not in ('RETURNING','RECOVERY_QUEUE','TAG_ACQUIRE','ALIGNING','DESCENDING','LANDING','LATCHING','RETRACTING'):
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
        if self.flight_planner and d['state'] not in ('PREPARING','ARMING','RELEASING','TAKEOFF','RECOVERY_QUEUE','TAG_ACQUIRE','ALIGNING','DESCENDING','LANDING','LATCHING'):
            health=self.runtime.fleet.status(d['id']) if self.runtime.fleet else {}
            current=health.get('position')
            if current:p=self.flight_planner.goal(d['id'],current,p)
        d['goal']=list(p)
        if self.runtime.fleet:self.runtime.fleet.goal(d['id'],p,d.get('follow_yaw',self.pose('carrier')['yaw'] if self.pose('carrier') else 0.))
    def tick(self):
        if self.runtime.state=='error':
            if self.state!='ERROR':self.state='ERROR';self.event(self.runtime.error or 'Runtime error','error')
            return
        if self.runtime.state!='running' or self.runtime.gz is None:return
        gz=self.runtime.gz
        if hasattr(self.vision,'observer_keys'):
            self.vision.observer_keys={d['id']:d['target']['id'] for d in list(self.drones.values()) if d['state']=='OBSERVING' and d.get('target',{}).get('id')}
            self.vision.observer_keys=dict(list(self.vision.observer_keys.items())[:2])
        now=gz.sim_time;dt=max(0,min(.25,now-self.last_time));self.last_time=now
        if self.config.living_city:
            from .city import City
            if self.city is None:self.city=City(self.config,gz)
            self.city.tick()
        if not gz.paused:
            was_moving=self.carousel.moving;self.carousel.tick(gz,0 if self.hold or self.state=='FAULT' else dt)
            if was_moving and not self.carousel.moving:self.event(f'Carousel locked · original {self.carousel.active} tray at flight deck')
            if self.carousel.error:
                if self.state!='FAULT':self.state='FAULT';self.event(self.carousel.error,'error')
                return
        self.vision.searching={d['id'] for d in self.drones.values() if d['state'] in ('TAKEOFF','SEARCHING','HOVERING','LOITERING','OBSERVING','TARGET_SEARCHING','TARGET_TRACKING','TARGET_LOITERING')}
        if hasattr(self.vision,'sites'):
            for did in self.vision.searching:
                if not self.drones[did].get('tracking'):self.vision.sites[did]=self.config.stops[min(self.stop_index,len(self.config.stops)-1)].label
        if self.state=='INITIALIZING':self.state='READY';self.event('Simulation ready · physical telemetry connected')
        if self.state in ('DRAFT','READY','COMPLETE','ABORTED','FAULT'):return
        if gz.paused:
            self.world_was_paused=True;return
        if self.world_was_paused:
            self.world_was_paused=False;self.resume_deadline=time.monotonic()+2.
        if self.resume_deadline is not None:
            fresh=not self.runtime.fleet or all(self.runtime.fleet.status(d['id'])['fresh'] for d in self.drones.values() if d['state'] not in TERMINAL and d['deployed'])
            if not fresh and time.monotonic()<self.resume_deadline:
                gz.drive(0,0);return
            self.resume_deadline=None
        if time.monotonic()-gz.received>3:
            self.state='FAULT';self.event('Physics telemetry lost. Mission stopped.','error');return
        if self.hold:
            self.drive_watch=None
            gz.drive(0,0)
            for d in self.drones.values():
                d['entered']+=dt
                if d['search_start'] is not None:d['search_start']+=dt
            if self.follow:
                self.follow.close.freeze(now)
                if self.follow.close.active:
                    self.follow.close.retreat(now,'Close approach cancelled by mission hold')
                    aircraft=self.drones[self.follow.drone_id];health=self.runtime.fleet.status(aircraft['id'])
                    if health['fresh'] and health['position'] is not None:
                        p=health['position'];self.set_goal(aircraft,[p[0],p[1],max(p[2],self.config.tracking_altitude)])
                self.follow.started+=dt
                if self.follow.tracking_started is not None:self.follow.tracking_started+=dt
                if self.follow.lost_since is not None:self.follow.lost_since+=dt
            return
        carrier=self.pose('carrier')
        if not carrier:return
        stop=self.config.stops[min(self.stop_index,len(self.config.stops)-1)]
        if self.state=='TRACKING':
            gz.drive(0,0);d=self.drones[self.follow.drone_id]
            if self.follow.cancelled and not d['deployed'] and gz.latches.get(d['id'])=='attached':
                health=self.runtime.fleet.status(d['id']);self.runtime.fleet.disarm(d['id']);self.runtime.fleet.stop_control(d['id'])
                if not health['armed']:
                    self.transition(d,'DOCKED' if self.follow.initial_ground=='DOCKED' else 'STORED','Tracking cancelled before flight');self.launch_owner=None;self.follow.phase('FINISHED',now,'Cancelled before flight')
            for active in self.drones.values():
                if active['state'] not in TERMINAL:self.tick_drone(active,self.follow_stop,dt)
                if self.state!='TRACKING':break
            if self.state=='TRACKING' and d['state'] in ('DOCKED','STORED') and all(other['state'] in TERMINAL for other in self.drones.values()):
                if d['state']=='DOCKED':self.follow.phase('DOCKED',now,'Physical contact, disarm and latch verified')
                if self.index_carousel('upper'):
                    self.state='COMPLETE';d['tracking']=False;self.event('Tracking flight complete · all aircraft recovered','success')
            self.record_snapshot();return
        if self.state=='DRIVING':
            self.record_snapshot()
            x,y,_=carrier['position'];goal=(stop.x,stop.y)
            if self.config.living_city:
                from .city import service_route,SERVICE_X,SERVICE_Y
                route=service_route(self.config.start if self.stop_index==0 else self.config.stops[self.stop_index-1],stop)
                if min(abs(x-SERVICE_X),abs(y-SERVICE_Y))>1.:
                    self.hold=True;gz.drive(0,0);self.event('Carrier left its protected lane. Mission held.','warning');return
                if getattr(gz,'city_contacts',[]):
                    self.hold=True;gz.drive(0,0);self.event('Carrier city contact detected. Mission held.','warning');return
                if self.city and any(key.endswith('-carrier') for key in self.city.violations):
                    self.hold=True;gz.drive(0,0);self.event('An actor entered the carrier safety envelope. Mission held before further travel.','warning');return
                self.drive_waypoint=min(self.drive_waypoint,len(route)-1);goal=route[self.drive_waypoint]
                if self.drive_waypoint<len(route)-1 and math.dist((x,y),goal)<.5:
                    self.drive_waypoint+=1;goal=route[self.drive_waypoint];self.drive_watch=None
            dx,dy=goal[0]-x,goal[1]-y;dist=math.hypot(dx,dy);err=wrap(math.atan2(dy,dx)-carrier['yaw'])
            if dist>.45:
                speed=min(self.config.ugv_speed,dist*.8)*max(0,math.cos(err))
                angular=max(-.6,min(.6,err*1.3))
                if self.config.living_city:
                    from .driving import city_drive
                    odom=gz.odom or {};speed,angular=city_drive(dist,err,odom.get('speed',0.),odom.get('yaw_rate',0.),self.config.ugv_speed)
                if speed>.08:
                    if self.drive_watch is None or self.drive_watch[2]!=self.stop_index or self.drive_watch[1]-dist>.25:self.drive_watch=(now,dist,self.stop_index)
                    elif now-self.drive_watch[0]>8:
                        self.hold=True;gz.drive(0,0);self.event(f'Carrier blocked toward {stop.label}: no measured forward progress for 8 seconds. Mission held.','warning');return
                else:self.drive_watch=None
                gz.drive(speed,angular)
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
            elif self.stop_index+1<len(self.config.stops):self.stop_index+=1;self.drive_waypoint=1;self.state='DRIVING';self.event('Recovery complete · proceeding to next stop')
            else:self.state='COMPLETE';self.event('Mission complete · all deployed aircraft docked','success')
        self.record_snapshot()
    def record_snapshot(self):
        now=self.now()
        if now-self.last_log>.5:
            self.last_log=now;path=self.root/'artifacts/runs'/f'{self.run_id}.jsonl';path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists() and path.stat().st_size>=32*1024**2:
                if not self.log_limited:self.log_limited=True;self.event('Detailed mission trace reached its 32 MiB limit. Live telemetry continues.','info')
                return
            row=self.snapshot()
            # Repeated target histories dominate fleet traces. Keep measured
            # poses and all safety fields; retain only new mission events and
            # shallow observed target rows without mutating live catalogue data.
            row['events']=[event for event in row['events'] if event['id']>getattr(self,'logged_event_id',0)]
            if row['events']:self.logged_event_id=max(event['id'] for event in row['events'])
            for key in ('catalogue','tracks'):
                row[key]=[{k:v for k,v in target.items() if k!='history'} for target in row[key]]
            for drone in row['drones']:
                if drone['target']:drone['target']={k:v for k,v in drone['target'].items() if k!='history'}
            with path.open('a') as f:f.write(json.dumps(row)+'\n')
    def tick_drone(self,d,stop,dt):
        gz=self.runtime.gz;fleet=self.runtime.fleet;did=d['id'];now=self.now();state=d['state'];p=self.pose(did);tray=self.tray_pose(d)
        if not p or not tray or not fleet:return
        health=fleet.status(did);d['battery']=health['battery'];pos=health['position'] or p['position'];age=now-d['entered']
        if health['battery'] is not None and health['battery']<self.config.battery_return and state in ('SEARCHING','OBSERVING','HOVERING','LOITERING','TARGET_SEARCHING','TARGET_TRACKING','TARGET_LOITERING'):
            if d.get('tracking') and self.follow:self.follow.finish(self,'Battery reserve','reserve')
            else:self.transition(d,'RETURNING','Battery reserve')
            state='RETURNING'
        if d['deployed'] and not health['fresh']:
            fleet.stop_control(did);self.transition(d,'FAULT','PX4 telemetry stale; native failsafe owns aircraft');self.state='FAULT';return
        if age>120 and state not in ('SEARCHING','OBSERVING','LOITERING','HOVERING','RETURNING','TARGET_SEARCHING','TARGET_TRACKING','TARGET_LOITERING'):
            self.transition(d,'FAULT',f'{state.lower()} timed out');self.state='FAULT';return
        alt=self.config.altitude+(int(did[-2:])-1)*.9
        if d.get('tracking'):alt=self.config.tracking_altitude
        elif self.state=='TRACKING':alt=max(alt,self.config.tracking_altitude+3+(int(did[-2:])-1)*.9)
        if state in ('TARGET_SEARCHING','TARGET_TRACKING','TARGET_LOITERING'):
            self.follow.tick(self,d,pos,alt);return
        if state=='PREPARING':
            # A recovered vehicle can remain in PX4 Offboard mode after disarm.
            # Restore a stationary stream while latched; retain all arming checks.
            if health['fresh'] and health['position'] is not None:self.set_goal(d,list(pos))
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
                if not d.get('tracking') and self.state!='TRACKING':self.check_detection(d,stop)
            if d['state']=='TAKEOFF' and abs(pos[2]-alt)<.5:
                d['search_start']=now;self.transition(d,'TARGET_SEARCHING' if d.get('tracking') else 'RETURNING' if self.state=='TRACKING' else 'SEARCHING')
        elif state in ('SEARCHING','HOVERING','LOITERING'):
            if state=='SEARCHING':
                radius=stop.search_radius if self.config.living_city else min(stop.search_radius,6+int(did[-2:])*.6)
                theta=((int(did[-2:])-1)%8)*math.pi/4+(now-d['search_start'])*self.config.flight_speed/radius
                if self.config.living_city:
                    from .city import survey_goal
                    xy=survey_goal(self.config,stop,now-d['search_start'],int(did[-2:])-1,self.city.layout['networks'])
                    self.set_goal(d,[*xy,alt])
                else:self.set_goal(d,[stop.x+radius*math.cos(theta),stop.y+radius*math.sin(theta),alt])
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
            if self.config.living_city:alt=max(alt,self.config.tracking_altitude+(int(did[-2:])-1)*.9)
            if self.config.living_city and d.get('target',{}).get('id'):
                row=self.vision.registry.get(d['target']['id'],now)
                if row and row['age']<1 and not row['ambiguous']:d['target']=row
            target=d['target'];x,y,_=target['position'];angle=math.atan2(pos[1]-y,pos[0]-x)
            separation=min(self.config.standoff,alt*.25) if self.config.living_city else self.config.standoff
            self.set_goal(d,[x+separation*math.cos(angle),y+separation*math.sin(angle),alt])
            if age>=self.config.observation_seconds:self.transition(d,'RETURNING','Observation complete')
        elif state=='RETURNING':
            # Reserve a distinct holding point while awaiting the single final approach corridor.
            ugv=self.pose('carrier')['position'];idx=int(did[-2:])-1;a=idx*math.pi/4;holding=[ugv[0]+8*math.cos(a),ugv[1]+8*math.sin(a),alt]
            self.set_goal(d,holding)
            waiting_to_launch=not self.abort and self.state!='TRACKING' and any(self.drones[x]['state'] in ('STORED','PREPARING','ARMING','RELEASING','TAKEOFF') for x in stop.drones)
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
            offset=tag['relative_position'];anchor=pos
            if hasattr(fleet,'perception_pose') and tag.get('camera_position') is not None:
                # Resolve the tag into the estimator frame at image capture.
                # Adding an old image offset to today's estimate moves the goal
                # while the aircraft is already correcting that same offset.
                frame_pose,frame_sync=fleet.perception_pose(did,obs['time'])
                d['landing_pose_check']={'image_time':obs['time'],'sync_error':frame_sync,
                                         'position_time':frame_pose.get('time') if frame_pose else None,
                                         'attitude_time':frame_pose.get('attitude_time') if frame_pose else None,
                                         'accepted':frame_pose is not None and frame_sync<=.25}
                if frame_pose is None or frame_sync>.25:
                    self.set_goal(d,list(pos));return
                from .vision import camera_relative
                offset=camera_relative(tag['camera_position'],frame_pose);anchor=frame_pose['position']
            ex,ey=offset[:2];height=-offset[2];error=math.hypot(ex,ey);d['tag_error']=error
            plane_z=anchor[2]+offset[2]
            # Capture-aligned image displacement is applied in the PX4 control frame.
            # Never subtract an EKF position from a Gazebo-world tag position.
            if state=='TAG_ACQUIRE' and height>3.5:
                self.set_goal(d,[anchor[0]+ex,anchor[1]+ey,plane_z+3]);return
            # Altitude follows the vision-derived tag plane; coarse tray telemetry never substitutes for a missing tag.
            if error<.07:
                d['descent_z']=max(plane_z+.49,max(pos[2]-.35,d.get('descent_z',pos[2])-.28*dt))
            else:d['descent_z']=pos[2]
            desired_z=d['descent_z']
            self.set_goal(d,[anchor[0]+ex,anchor[1]+ey,desired_z])
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
        if self.config.living_city:
            # Registry confirmation already requires distinct high-score images.
            wanted=search_classes(self.config,stop)
            rows=[r for r in self.vision.registry.snapshot(self.now()) if r['drone']==d['id'] and r['age']<1. and not r['ambiguous'] and r['confidence']>=self.config.confidence and matches_class(r['class'],wanted)]
            if not rows:
                # Centre a tentative image sighting long enough for independent
                # detector images to confirm it. It is not yet a catalogue target.
                obs=getattr(self.vision,'object_latest',{}).get(d['id'],{})
                fresh=self.now()-obs.get('time',-100)<1. and obs.get('sync_error',999)<.25
                candidates=[r for r in obs.get('detections',[]) if r.get('position') is not None and r['confidence']>=self.config.confidence and matches_class(r['class'],wanted)] if fresh else []
                if candidates and d['state'] in ('SEARCHING','HOVERING','LOITERING'):
                    candidate=max(candidates,key=lambda r:r['confidence'])
                    alt=self.config.altitude+(int(d['id'][-2:])-1)*.9
                    self.set_goal(d,[*candidate['position'][:2],alt])
                return
            index=stop.drones.index(d['id']) if d['id'] in stop.drones else 0
            preferred=wanted[index%len(wanted)]
            row=max(rows,key=lambda r:(matches_class(r['class'],[preferred]),r['last_seen']));target={**row,'track_id':row['id'],'time':row['last_seen']}
            d['detection_latency']=round(row['last_seen']-d.get('camera_started',d['entered']),2);self.tracks.append(target);d['target']=target
            self.transition(d,'OBSERVING',f"{row['class']} confirmed from repeated camera observations");return
        obs=getattr(self.vision,'object_latest',self.vision.latest).get(d['id'],{})
        if self.now()-obs.get('time',-100)>1 or obs.get('sync_error',999)>.25:return
        candidates=[x for x in obs.get('detections',[]) if matches_class(x['class'],search_classes(self.config,stop)) and x['position'] is not None and x['confidence']>=self.config.confidence]
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
            target={**candidate,'id':candidate.get('track_id',f'track-{len(self.tracks)+1:03d}'),'drone':d['id'],'time':obs['time']};self.tracks.append(target);d['target']=target;self.transition(d,'OBSERVING',f'{candidate["class"]} confirmed from camera')
    def snapshot(self):
        gz=self.runtime.gz;fleet=self.runtime.fleet;now=self.now();rows=[]
        for did,d in self.drones.items():
            p=self.pose(did);health=fleet.status(did) if fleet and did in fleet.ids else {}
            fallback=spawn_pose(self.config,(d['x'],d['y'],d['z']+.26))
            rows.append({'id':did,'bay':d['bay'],'level':d['level'],'tag_id':d['tag_id'],'state':d['state'],'position':p['position'] if p else fallback['position'],'quaternion':p['quaternion'] if p else fallback['quaternion'],'measured':p is not None,'battery':health.get('battery'),'ready':health.get('ready',False),'armed':health.get('armed',False),'mode':health.get('mode'),'telemetry_age':health.get('age'),'target':d['target'],'reason':d['reason'],'extension':abs(self.carousel.measured(gz,d['level'])['y']),'tray_position':self.tray_pose(d),'estimated_position':health.get('position'),'detection_latency':d.get('detection_latency'),'camera_active':did in getattr(gz,'enabled_cameras',set()) if gz else False,'latched':gz.latches.get(did)=='attached' if gz else True,'tag_error':d.get('tag_error'),'landing_pose_check':d.get('landing_pose_check'),'phase_seconds':round(max(0,now-d['entered']),1),'vision':self.vision.latest.get(did)})
        carrier=self.pose('carrier') or spawn_pose(self.config)
        registry=getattr(self.vision,'registry',None)
        catalogue=registry.snapshot(now) if registry else []
        tracking=self.follow.snapshot(registry,now) if self.follow and registry else {'state':'SELECTED' if registry and registry.selected else 'IDLE','target_id':registry.selected if registry else None,'drone_id':None,'timeline':[],'candidates':[]}
        return {'run_id':self.run_id,'state':self.state,'hold':self.hold,'sim_time':round(now,2),'stop_index':self.stop_index,'runtime':self.runtime.health(),'physics':{'real_time_factor':round(gz.rtf,2) if gz else 0,'paused':gz.paused if gz else False,'age':round(time.monotonic()-gz.received,2) if gz and gz.received else None},'carrier':{**carrier,'speed':round((gz.odom or {}).get('speed',0),2) if gz else 0},'carousel':self.carousel.snapshot(gz),'wheel_angles':{k:v for k,v in (gz.joints if gz else {}).items() if k.startswith('wheel_')},'drones':rows,'tracks':self.tracks,'city':self.city.snapshot() if self.city else None,'catalogue':catalogue,'tracking':tracking,'tracking_events':registry.events[-60:] if registry else [],'events':self.events[-60:],'perception':{'detector_ready':self.vision.detector_ready,'tag_ready':self.vision.tag_ready,'error':self.vision.error,'aerial_ready':getattr(self.vision,'aerial_ready',False),'aerial_error':getattr(self.vision,'aerial_error',None),'visual_tracking':getattr(self.vision,'optical_debug',{}),'performance':getattr(self.vision,'performance',{})}}
