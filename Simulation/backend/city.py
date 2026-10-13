"""Lane geometry and background motion. Never imported by image tracking.

Traffic and pedestrians occupy three compact districts separated by a protected service
cross. Velocity commands are integrated by Gazebo, not by this controller.
"""
from __future__ import annotations
import math, random
from .placement import segment_distance

SERVICE_Y=-22.; SERVICE_X=30.; SERVICE_HALF=3.6
# Full-size roads and bodies; closer blocks, with the southeast district removed.
DISTRICTS=[(-47.,15.,-103.,-37.),(-47.,15.,-7.,59.),(45.,107.,-7.,59.)]
SCENARIO_DISTRICT=2
DIMENSIONS={'person':(.95,.65,1.72),'car':(4.45,1.85,1.65),
            'truck':(7.7,2.55,3.4),'bus':(8.35,2.95,3.2)}

def search_classes(m,stop=None):
    return [stop.target_class] if stop and stop.target_class else (m.target_classes or [m.target_class])

def matches_class(kind,classes):
    return kind in classes or 'vehicle' in classes and kind in ('car','truck','bus')

def placement_plan(obj,x,y,yaw,objects,paths,stops,carrier=None):
    """Validate an operator edit using scene geometry; never supply perception."""
    body=DIMENSIONS[obj['kind']];radius=math.hypot(*body[:2])/2
    if not all(math.isfinite(v) for v in (x,y,yaw)) or max(abs(x),abs(y))>108:raise ValueError('Place the actor within X/Y ±108 m.')
    if min(abs(x-SERVICE_X),abs(y-SERVICE_Y))<3.34+radius+.5:raise ValueError('Placement overlaps the protected UGV lane. Choose another position.')
    if any(math.dist([x,y],[stop.x,stop.y])<4.7+radius for stop in stops):raise ValueError('Placement overlaps a deployment bay.')
    if carrier and math.dist([x,y],carrier[:2])<3.34+radius+1.:raise ValueError('Placement is too close to the carrier.')
    for other in objects:
        if other['id']==obj['id']:continue
        if other['kind']=='building':
            if abs(x-other['x'])<other['sx']/2+radius+.5 and abs(y-other['y'])<other['sy']/2+radius+.5:raise ValueError('Placement overlaps a building.')
        elif math.dist([x,y],[other['x'],other['y']])<radius+math.hypot(*DIMENSIONS[other['kind']][:2])/2+.5:raise ValueError(f'Placement overlaps {other["id"]}.')
    kind='sidewalk' if obj['kind']=='person' else 'vehicle'
    route=min((p for p in paths if p['kind']==kind),key=lambda p:project(p['points'],[x,y])[0])
    error,s,_=project(route['points'],[x,y]);parked=error>.45
    if not parked:_,yaw=point_at(route['points'],s)
    return dict(x=x,y=y,yaw=yaw,path_id=route['id'],district=route['district'],parked=parked,manual_placement=True)

def apply_placements(m,objects,paths):
    by_id={o['id']:o for o in objects}
    for placement in m.actor_placements:
        obj=by_id.get(placement.id)
        if obj is None:raise ValueError(f'{placement.id} is absent. Increase its population count or clear the saved placement.')
        obj.update(x=placement.x,y=placement.y,yaw=placement.yaw)
    for placement in m.actor_placements:
        obj=by_id[placement.id]
        obj.update(placement_plan(obj,placement.x,placement.y,placement.yaw,objects,paths,m.stops))

def snap_service(x,y,tolerance=4.):
    options=[(x,SERVICE_Y),(SERVICE_X,y)]
    p=min(options,key=lambda a:math.hypot(a[0]-x,a[1]-y))
    if max(abs(p[0]),abs(p[1]))>108 or math.hypot(p[0]-x,p[1]-y)>tolerance:
        raise ValueError('Living-city stops must be on the protected service lane: Y = -22 m or X = 30 m (within 4 m to snap).')
    return p

def service_route(a,b):
    a=snap_service(a.x,a.y);b=snap_service(b.x,b.y)
    corner=(SERVICE_X,SERVICE_Y)
    return [a,b] if a[0]==b[0] or a[1]==b[1] else [a,corner,b]

def rounded_loop(bounds,offset=0.,reverse=False):
    x0,x1,y0,y1=bounds;x0-=offset;x1+=offset;y0-=offset;y1+=offset
    radius=max(3.,12.+offset);points=[]
    for cx,cy,start in [(x1-radius,y0+radius,-90),(x1-radius,y1-radius,0),
                        (x0+radius,y1-radius,90),(x0+radius,y0+radius,180)]:
        for k in range(13):
            a=math.radians(start+k*90/12);points.append([cx+radius*math.cos(a),cy+radius*math.sin(a)])
    if reverse:points.reverse()
    points.append(points[0].copy())
    return points

def circuit_from(path,anchor):
    _,s,i=project(path,anchor);p,_=point_at(path,s)
    return [p,*path[i+1:-1],*path[:i+1],p]

def lengths(path):
    values=[0.]
    for a,b in zip(path,path[1:]):values.append(values[-1]+math.dist(a,b))
    return values

def point_at(path,s):
    cumulative=lengths(path);s%=cumulative[-1]
    for i,(a,b) in enumerate(zip(path,path[1:])):
        if cumulative[i+1]>=s:
            f=(s-cumulative[i])/max(1e-6,cumulative[i+1]-cumulative[i])
            return [a[0]+f*(b[0]-a[0]),a[1]+f*(b[1]-a[1])],math.atan2(b[1]-a[1],b[0]-a[0])
    return path[0],0.

def project(path,p,previous_s=None):
    cumulative=lengths(path);best=(float('inf'),0.,0)
    for i,(a,b) in enumerate(zip(path,path[1:])):
        dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
        t=max(0.,min(1.,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/max(1e-9,den)))
        dist=math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
        progress=cumulative[i]+t*math.sqrt(den)
        if previous_s is not None and abs((progress-previous_s+cumulative[-1]/2)%cumulative[-1]-cumulative[-1]/2)>12:continue
        if dist<best[0]:best=(dist,progress,i)
    return best

def survey_goal(m,stop,age,index,public_networks=None):
    """Scan public paths using map geometry, without looking at actor placement."""
    classes=search_classes(m,stop);wanted=classes[index%len(classes)]
    kind='sidewalk' if wanted=='person' else 'vehicle'
    networks=[p for p in (public_networks if public_networks is not None else layout(m)['networks']) if p['kind']==kind]
    nearest=min(networks,key=lambda p:project(p['points'],[stop.x,stop.y])[0])
    _,s,_=project(nearest['points'],[stop.x,stop.y])
    # Check the nearest path first, then sweep both directions with centre
    # revisits. Stagger aircraft using only their mission index, not actor truth.
    phase=(age+index*6.)%48.;amplitude=min(stop.search_radius*.75,m.flight_speed*3.)
    offset=0.
    if 6.<phase<18.:offset=amplitude*(1-abs(phase-12.)/6.)
    elif 24.<phase<36.:offset=-amplitude*(1-abs(phase-30.)/6.)
    p,_=point_at(nearest['points'],s+offset)
    dx,dy=p[0]-stop.x,p[1]-stop.y;scale=min(1.,stop.search_radius/max(.1,math.hypot(dx,dy)))
    return [stop.x+dx*scale,stop.y+dy*scale]

def layout(m):
    rng=random.Random(m.seed);roads=[];paths=[];objects=[];crossings=[]
    for di,b in enumerate(DISTRICTS):
        x0,x1,y0,y1=b;cx=(x0+x1)/2;cy=(y0+y1)/2
        # Rounded asphalt strips are generated from these center lines.
        for lane in (-1,1):
            paths.append({'id':f'lane-{di}-{lane}','kind':'vehicle','district':di,
                          'points':rounded_loop(b,lane*2.5,lane==1),'width':5.})
        for side in (-1,1):
            paths.append({'id':f'walk-{di}-{side}','kind':'sidewalk','district':di,
                          'points':rounded_loop(b,side*9.,side==1),'width':2.2})
        inside=circuit_from(rounded_loop(b,-9.),[cx,y1-9.]);outside=circuit_from(rounded_loop(b,9.,True),[cx,y1+9.])
        paths.append({'id':f'walk-cross-{di}','kind':'sidewalk','district':di,
                      'points':[*inside,outside[0],*outside[1:],inside[0]],'width':2.2,'crossing':di})
        crossings.append({'id':f'crossing-{di}','district':di,'x':cx,'y':y1,'width':3.,'length':20.})
        roads.append({'id':f'district-{di}','points':rounded_loop(b),'width':10.})
        for ix,dx in enumerate((-10.,10.)):
            for iy,dy in enumerate((-12.,12.) if y1-y0<80 else (-26.,0.,26.)):
                objects.append(dict(id=f'building_{di}_{ix}_{iy}',kind='building',x=cx+dx,y=cy+dy,z=0,
                                    sx=10.,sy=12.,sz=6.+(di+ix+iy)%4*2.5,yaw=0,variant=(di+ix+iy)%4))
    # Scenario branches are public map geometry, used only by the city controller.
    # The perception registry and follow controller never receive actor routes.
    if m.city_scenario=='building-occlusion':
        route=next(p for p in paths if p['id']==f'walk-{SCENARIO_DISTRICT}-1')
        x0,x1,y0,y1=DISTRICTS[SCENARIO_DISTRICT];cx=(x0+x1)/2;cy=(y0+y1)/2
        base=circuit_from(route['points'],[x0-9.,cy+1.])
        route['points']=[base[0],[cx-18.5,cy+1.],[cx-1.5,cy+1.],[cx-1.5,cy+23.],[cx-18.5,cy+23.],[cx-18.5,cy+1.],*base]
        next(o for o in objects if o['id']==f'building_{SCENARIO_DISTRICT}_0_1')['sz']=18.
    if m.city_scenario=='leaving-area':
        paths.append({'id':'walk-exit','kind':'sidewalk','district':SCENARIO_DISTRICT,'points':[[36.,-12.],[36.,119.],[38.,119.],[38.,-12.],[36.,-12.]],'width':2.2})
    if m.city_scenario=='similar-people':
        paths.append({'id':'walk-lookalike','kind':'sidewalk','district':SCENARIO_DISTRICT,'points':rounded_loop(DISTRICTS[SCENARIO_DISTRICT],8.,False),'width':2.2})
    actors=[];usage={} 
    for kind,count in [('person',m.population),('vehicle',m.traffic)]:
        available=[p for p in paths if p['kind']==('sidewalk' if kind=='person' else 'vehicle')]
        for i in range(count):
            cls='person' if kind=='person' else ('car','truck','bus')[i%3]
            if not m.target_present and matches_class(cls,search_classes(m)):continue
            site=m.stops[i%len(m.stops)]
            route=available[i%len(available)] if i%6==5 else min(available,key=lambda p:project(p['points'],[site.x,site.y])[0])
            if cls=='person' and i%4==3:
                route=next(p for p in available if p.get('crossing')==route['district'])
            if cls=='person' and m.city_scenario=='similar-people':route=next(p for p in available if p['id']==(f'walk-{SCENARIO_DISTRICT}-1' if i%2==0 else 'walk-lookalike'))
            if cls=='person' and m.city_scenario=='leaving-area':route=next(p for p in available if p['id']=='walk-exit')
            if cls=='person' and m.city_scenario=='building-occlusion':route=next(p for p in available if p['id']==f'walk-{SCENARIO_DISTRICT}-1')
            ordinal=usage.get(route['id'],0);usage[route['id']]=ordinal+1
            _,near_s,_=project(route['points'],[site.x,site.y])
            spacing=4. if cls=='person' else 16.
            # Public, deterministic scenario placement: approach the survey site
            # during its initial carrier turn and aircraft preparation. This
            # never changes actor speed/pose in response to target selection.
            approach_seconds=40. if m.city_scenario in ('walking-person','similar-people','building-occlusion','leaving-area') else 15.
            s=(near_s-(approach_seconds*m.walking_speed if cls=='person' else 32.*m.traffic_speed)+ordinal*spacing+rng.uniform(-1,1))%lengths(route['points'])[-1]
            xy,yaw=point_at(route['points'],s)
            obj=dict(id=f'{"person" if kind=="person" else "vehicle"}_{i}',kind=cls,x=xy[0],y=xy[1],z=0,
                     yaw=yaw,variant=i%4 if cls=='person' else i%2,path_id=route['id'],district=route['district'],
                     desired_speed=m.walking_speed*rng.uniform(.85,1.) if cls=='person' else m.traffic_speed*rng.uniform(.75,1.),
                     parked=cls=='car' and i%7==6,start_delay=4.+i%5*2. if i%6==5 else 0.,phase_offset=i*.8)
            if obj['parked']:
                parking=rounded_loop(DISTRICTS[route['district']],6.5)
                xy,yaw=point_at(parking,near_s);obj.update(x=xy[0],y=xy[1],yaw=yaw)
            # Routes can share sidewalk geometry. Reserve initial physical spacing
            # across route IDs, including the compound crossing branch.
            spawn_path=parking if obj['parked'] else route['points']
            radius=1.1 if cls=='person' else math.hypot(*DIMENSIONS[cls][:2])/2+1.
            for attempt in range(80):
                overlaps=any(math.dist([obj['x'],obj['y']],[a['x'],a['y']])<radius+(1.1 if a['kind']=='person' else math.hypot(*DIMENSIONS[a['kind']][:2])/2+1.) for a in actors)
                if not overlaps:break
                s-=4. if cls=='person' else 12.;xy,yaw=point_at(spawn_path,s);obj.update(x=xy[0],y=xy[1],yaw=yaw)
            else:raise ValueError('Population exceeds safe initial occupancy on these public paths.')
            if cls=='person' and m.city_scenario=='similar-people':obj['variant']=0
            objects.append(obj);actors.append(obj)
    apply_placements(m,objects,paths)
    service=[{'id':'service-east-west','kind':'service','points':[[-108.,SERVICE_Y],[108.,SERVICE_Y]],'width':SERVICE_HALF*2},
             {'id':'service-north-south','kind':'service','points':[[SERVICE_X,-108.],[SERVICE_X,108.]],'width':SERVICE_HALF*2}]
    route=[]
    for a,b in zip([m.start,*m.stops],[*m.stops]):
        leg=service_route(a,b);route.extend(leg if not route else leg[1:])
    return {'objects':objects,'roads':[], 'city_roads':roads,'networks':paths+service,'ugv_route':route,'crossings':crossings,
            'deployment_bays':[{'id':s.id,'x':s.x,'y':s.y,'radius':4.7} for s in m.stops],
            'motion_model':'Gazebo velocity-controlled background bodies; physical PX4 aircraft and wheel-driven carrier'}

class City:
    def __init__(self,mission,gz):
        self.gz=gz;self.mission=mission;self.layout=layout(mission)
        self.paths={p['id']:p['points'] for p in self.layout['networks']}
        self.actors={o['id']:{**o,'speed':0.,'distance':0.,'last_position':None,'last_time':0.,'wait_until':o['start_delay']} for o in self.layout['objects'] if o['kind']!='building'}
        self.last_time=-1.;self.events=[];self.violations={};self.min_carrier_gap=None
        self.crossings=self.layout['crossings'];self.reservations={};self.crossing_passes=0;self.crossing_violations=[];self.crossing_owners={}
    def relocate(self,name,x,y,yaw):
        if self.gz.paused:raise ValueError('Resume physics to move a live actor, or edit its position before initialization.')
        obj=self.actors.get(name)
        if obj is None:raise ValueError('Choose a city person or vehicle.')
        objects=[o for o in self.layout['objects'] if o['kind']=='building']
        for other in self.actors.values():
            pose=self.gz.poses.get(other['id'])
            if pose:objects.append({**other,'x':pose['position'][0],'y':pose['position'][1]})
        carrier=self.gz.poses.get('carrier',{}).get('position')
        plan=placement_plan(obj,x,y,yaw,objects,self.layout['networks'],self.mission.stops,carrier)
        previous=dict(obj);obj['parked']=True;self.gz.actor_velocity(name,0.,0.)
        try:
            self.gz.actor_route(name,[])
            self.gz.place_actor(name,x,y,plan['yaw'])
        except Exception:
            obj.update(previous)
            try:self.gz.actor_route(name,self.paths[obj['path_id']])
            except Exception:pass
            raise
        obj.update(plan,speed=0.,path_s=None,last_position=None,last_time=self.gz.sim_time,start_delay=0.,wait_until=self.gz.sim_time)
        if not plan['parked']:self.gz.actor_route(name,self.paths[plan['path_id']])
        self.crossing_owners={d:owner for d,owner in self.crossing_owners.items() if owner!=name}
        self.violations.pop(name,None)
        return {'id':name,'x':x,'y':y,'yaw':plan['yaw'],'motion':'stationary off lane' if plan['parked'] else 'following assigned path','persistent':False}

    def tick(self):
        now=self.gz.sim_time;dt=now-self.last_time
        if self.gz.paused or dt<=0 or dt<.075:return
        dt=min(.2,dt);self.last_time=now;poses=self.gz.poses;carrier=poses.get('carrier')
        measured={name:poses[name] for name in self.actors if name in poses}
        self.reservations={}
        for cross in self.crossings:
            owner=self.crossing_owners.get(cross['district']);op=measured.get(owner)
            if op and (abs(op['position'][0]-cross['x'])>2. or abs(op['position'][1]-cross['y'])>9.2):self.crossing_owners.pop(cross['district'],None);owner=None
            occupied=[name for name,p in measured.items() if self.actors[name]['district']==cross['district'] and abs(p['position'][0]-cross['x'])<2.+DIMENSIONS[self.actors[name]['kind']][0]/2 and abs(p['position'][1]-cross['y'])<(8.7 if self.actors[name]['kind']=='person' else 5.)]
            pedestrians=[name for name in occupied if self.actors[name]['kind']=='person'];vehicles=[name for name in occupied if self.actors[name]['kind']!='person']
            walk_window=22./max(.2,self.mission.walking_speed*.8);cycle=36.+walk_window;phase=now%cycle
            entry_open=33.<=phase<35. and not vehicles and owner is None
            vehicle_green=phase<30. and not pedestrians and owner is None
            self.reservations[cross['district']]={'id':cross['id'],'x':cross['x'],'y':cross['y'],'pedestrian_entry':entry_open,'vehicle_green':vehicle_green,'owner':owner,'occupants':occupied,'state':'vehicles' if vehicle_green else 'pedestrians' if pedestrians or owner or entry_open else 'clearing'}
        for name,actor in self.actors.items():
            p=measured.get(name)
            if not p:continue
            xy=p['position'][:2];path=self.paths[actor['path_id']];err,s,index=project(path,xy,actor.get('path_s'));actor['path_s']=s
            if actor['parked']:
                self.gz.actor_velocity(name,0.,0.);actor['lane_error']=0.;actor['measured_speed']=0.;continue
            stamp=p['time'];previous_stamp=actor.get('last_pose_time')
            if actor['last_position'] is not None and previous_stamp is not None and stamp>previous_stamp:
                travelled=math.dist(xy,actor['last_position']);actor['distance']+=travelled
                actor['measured_speed']=travelled/(stamp-previous_stamp)
                actor['yaw_rate']=((p['yaw']-actor.get('last_yaw',p['yaw'])+math.pi)%(2*math.pi)-math.pi)/(stamp-previous_stamp)
            if previous_stamp is None or stamp>previous_stamp:
                actor['last_position']=xy;actor['last_pose_time']=stamp;actor['last_yaw']=p['yaw']
            actor['last_time']=now
            actor['lane_error']=err
            limit=.85 if actor['kind']=='person' else 1.0
            if err>limit:self.violations[name]=round(err,3)
            desired=actor['desired_speed']
            # Seeded, repeatable stop windows. Background actors do not know UAV targets.
            phase=(now+actor['phase_offset'])%58.
            if actor['parked'] or now<actor['wait_until'] or 38.<phase<41.:desired=0.
            ahead,_=point_at(path,s+(1.2 if actor['kind']=='person' else 2.))
            heading=math.atan2(ahead[1]-xy[1],ahead[0]-xy[0]);turn=(heading-p['yaw']+math.pi)%(2*math.pi)-math.pi
            cross=self.crossings[actor['district']];reservation=self.reservations[actor['district']]
            if actor['kind']=='person' and actor['path_id'].startswith('walk-cross'):
                on_bridge=abs(xy[0]-cross['x'])<1.2 and abs(xy[1]-cross['y'])<8.7
                approaching=abs(ahead[0]-cross['x'])<.7 and abs(ahead[1]-cross['y'])<8.95
                owner=self.crossing_owners.get(actor['district'])
                if approaching and not on_bridge and owner!=name:
                    if reservation['pedestrian_entry'] and owner is None:
                        self.crossing_owners[actor['district']]=name;reservation['pedestrian_entry']=False;reservation['vehicle_green']=False
                    else:desired=0.
                if on_bridge and not actor.get('crossing_active'):
                    actor['crossing_active']=True;self.crossing_passes+=1
                elif not on_bridge:actor['crossing_active']=False
                if on_bridge and reservation['vehicle_green']:self.crossing_violations.append({'time':now,'actor':name,'crossing':cross['id']})
            elif actor['kind']!='person' and not reservation['vehicle_green']:
                _,signal_s,_=project(path,[cross['x'],cross['y']]);gap=(signal_s-s)%lengths(path)[-1]
                half=DIMENSIONS[actor['kind']][0]/2;stop_distance=half+3.
                braking=actor['speed']**2/2.6+actor['speed']*.6
                if gap<stop_distance+braking+5.:desired=min(desired,max(0.,gap-stop_distance)*.5)
            # Cross-branch pedestrian spacing uses measured bodies and relative heading.
            if actor['kind']=='person':
                for other,q in measured.items():
                    if other==name or self.actors[other]['kind']!='person':continue
                    dx,dy=q['position'][0]-xy[0],q['position'][1]-xy[1]
                    forward=dx*math.cos(p['yaw'])+dy*math.sin(p['yaw'])
                    lateral=abs(-dx*math.sin(p['yaw'])+dy*math.cos(p['yaw']))
                    if 0<forward<3.5 and lateral<1.0:desired=min(desired,max(0.,forward-2.2)*.6)
            # Following-distance brake on the same directed lane, including queued actors.
            for other,q in measured.items():
                if other==name or self.actors[other]['parked'] or self.actors[other]['path_id']!=actor['path_id']:continue
                _,other_s,_=project(path,q['position'][:2],self.actors[other].get('path_s'));gap=(other_s-s)%lengths(path)[-1]
                half=(DIMENSIONS[actor['kind']][0]+DIMENSIONS[self.actors[other]['kind']][0])/2
                buffer=1.2 if actor['kind']=='person' else 3.
                desired=min(desired,max(0.,gap-half-buffer)*.5)
            if carrier:
                gap=math.dist(xy,carrier['position'][:2])-math.hypot(*DIMENSIONS[actor['kind']][:2])/2-2.7
                self.min_carrier_gap=gap if self.min_carrier_gap is None else min(gap,self.min_carrier_gap)
                if gap<1.5:desired=0.;self.violations[name+'-carrier']=round(gap,3)
            accel=.7 if actor['kind']=='person' else .65
            actor['speed']+=max(-1.3*dt,min(accel*dt,desired-actor['speed']))
            speed=actor['speed']  # Native path guidance uses the current physical heading.
            if err>1.4:speed=0.
            actor['turn']=max(-.8,min(.8,turn*2.5));self.gz.actor_velocity(name,speed,actor['turn'])
            actor['walk_phase']=actor['distance']*2*math.pi/1.25
            actor['wheel_angle']=actor['distance']/(.35 if actor['kind']=='car' else .5)
    def snapshot(self):
        result=[]
        for name,actor in self.actors.items():
            p=self.gz.poses.get(name)
            if not p:continue
            result.append({'id':name,'kind':actor['kind'],'position':p['position'],'quaternion':p['quaternion'],
                           'yaw':p['yaw'],'time':p['time'],'speed':round(actor.get('measured_speed',0.),3),
                           'walk_phase':actor.get('walk_phase',0.),'wheel_angle':actor.get('wheel_angle',0.),'yaw_rate':actor.get('yaw_rate',0.),'distance':actor['distance'],'steering':max(-.45,min(.45,math.atan(3.2*actor.get('turn',0.)/max(.05,actor['speed'])))) if actor['speed']>.05 else 0.,
                           'lane_error':round(actor.get('lane_error',0.),3),'commanded_speed':round(actor['speed'],3),'path_s':actor.get('path_s'),'parked':actor['parked']})
        return {'actors':result,'violations':self.violations,'minimum_carrier_gap':self.min_carrier_gap,
                'contact_events':getattr(self.gz,'city_contacts',[]),'actor_contacts':getattr(self.gz,'actor_contacts',[]),'crossings':list(self.reservations.values()),
                'crossing_passes':self.crossing_passes,'crossing_violations':self.crossing_violations[-50:]}
