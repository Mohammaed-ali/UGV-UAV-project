from __future__ import annotations

import math
from typing import Literal
from pydantic import BaseModel, Field, model_validator, ConfigDict
from .rack import UPPER_Z,LOWER_Z,PITCH,PAD_Z,RADIUS,CENTER_Z,HALF_HEIGHT,BASE_Z,CHASSIS_SIZE,DECK_SIZE,WHEEL_X,WHEEL_Y
from .placement import placement_clear,TRAVEL_CLEARANCE,STOP_CLEARANCE

MAP_SIZE=240
ROUTE_LIMIT=108

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Point(StrictModel):
    x: float = Field(ge=-ROUTE_LIMIT, le=ROUTE_LIMIT)
    y: float = Field(ge=-ROUTE_LIMIT, le=ROUTE_LIMIT)

class Stop(Point):
    id: str = Field(min_length=1, max_length=40, pattern=r'^[a-zA-Z0-9_-]+$')
    label: str = Field(min_length=1, max_length=48)
    drones: list[str] = Field(default_factory=list, max_length=8)
    search_radius: float = Field(default=12, ge=3, le=25)
    target_class: Literal['person','vehicle','car','truck','bus'] | None = None
    search_timeout: float | None = Field(default=None, ge=5, le=1800)
    loiter_seconds: float | None = Field(default=None, ge=0, le=1800)

class ActorPlacement(Point):
    id: str = Field(pattern=r'^(person|vehicle)_[0-9]+$',max_length=32)
    yaw: float = Field(default=0.,ge=-math.pi,le=math.pi)

class Mission(StrictModel):
    version: Literal[1] = 1
    name: str = Field(default='Perimeter survey', max_length=80)
    wheels: Literal[4,6] = 4
    seed: int = Field(default=42, ge=0, le=2147483647)
    terrain: Literal['field','proving_ground'] = 'proving_ground'
    population: int = Field(default=18, ge=0, le=40)
    traffic: int = Field(default=10, ge=0, le=20)
    target_present: bool = True
    target_class: Literal['person','vehicle','car','truck','bus'] = 'person'
    target_classes: list[Literal['person','vehicle','car','truck','bus']] = Field(default_factory=list,max_length=3)
    actor_placements: list[ActorPlacement] = Field(default_factory=list,max_length=60)
    ugv_speed: float = Field(default=1.5, ge=.2, le=10)
    altitude: float = Field(default=9, ge=6, le=20)
    flight_speed: float = Field(default=2, ge=.5, le=4)
    launch_interval: float = Field(default=5, ge=2, le=60)
    search_timeout: float = Field(default=40, ge=5, le=1800)
    no_target_policy: Literal['return','hover','loiter'] = 'loiter'
    loiter_seconds: float = Field(default=20, ge=0, le=1800)
    loiter_radius: float = Field(default=5, ge=2, le=10)
    observation_seconds: float = Field(default=15, ge=5, le=1800)
    standoff: float = Field(default=8, ge=4, le=20)
    confidence: float = Field(default=.4, ge=.2, le=.95)
    landing_retries: int = Field(default=2, ge=0, le=5)
    battery_return: float = Field(default=25, ge=15, le=60)
    wind: float = Field(default=0, ge=0, le=4)
    graphics_quality: Literal['low','balanced','high'] = 'balanced'
    living_city: bool = False
    city_scenario: Literal['custom','walking-person','moving-vehicle','similar-people','stopping-vehicle','building-occlusion','leaving-area'] = 'custom'
    walking_speed: float = Field(default=1.2,ge=.3,le=5.)
    traffic_speed: float = Field(default=1.6,ge=.3,le=20.)
    flight_boundary: float = Field(default=116.,ge=108.,le=116.)
    tracking_seconds: float = Field(default=90,ge=10,le=600)
    reacquire_seconds: float = Field(default=35,ge=5,le=180)
    tracking_altitude: float = Field(default=12,ge=8,le=20)
    tracking_distance: float = Field(default=2.,ge=0,le=5.)
    reacquire_confidence: float = Field(default=.8,ge=.6,le=.95)
    early_selection: bool = True
    tracking_uav: Literal['auto','uav01','uav02','uav03','uav04','uav05','uav06','uav07','uav08'] = 'auto'
    tracking_enabled: bool = True
    approach_clearance: float = Field(default=.5,ge=.5,le=10.)
    approach_speed: float = Field(default=.4,ge=.1,le=.75)
    aerial_vehicles: bool = True
    start: Point = Field(default_factory=lambda: Point(x=-28,y=-22))
    stops: list[Stop] = Field(default_factory=lambda: [
        Stop(id='alpha',label='Alpha',x=-12,y=-22,drones=['uav01','uav02','uav03']),
        Stop(id='bravo',label='Bravo',x=16,y=-22,drones=['uav04','uav05']),
        Stop(id='charlie',label='Charlie',x=30,y=3,drones=['uav06','uav07','uav08'])
    ],min_length=1,max_length=16)

    @model_validator(mode='after')
    def valid_plan(self):
        if len(set(self.target_classes))!=len(self.target_classes):raise ValueError('Choose up to three distinct search classes.')
        if len({p.id for p in self.actor_placements})!=len(self.actor_placements):raise ValueError('Actor placement IDs must be unique.')
        if self.actor_placements and not self.living_city:raise ValueError('Actor placement is available in Living city.')
        if self.living_city:
            if self.city_scenario=='building-occlusion' and self.traffic>0:raise ValueError('The building-occlusion pedestrian-plaza scenario requires zero vehicles. Use Custom city for normal traffic.')
            from .city import snap_service
            self.start.x,self.start.y=snap_service(self.start.x,self.start.y)
            for stop in self.stops:stop.x,stop.y=snap_service(stop.x,stop.y)
        ids=[s.id for s in self.stops]
        if len(set(ids))!=len(ids): raise ValueError('Stop IDs must be unique.')
        assigned=[d for s in self.stops for d in s.drones]
        available={f'uav{i:02d}' for i in range(1,9)}
        if any(d not in available for d in assigned): raise ValueError('Unknown drone ID.')
        if len(assigned)!=len(set(assigned)): raise ValueError('Each drone can be assigned to only one stop per mission.')
        points=[self.start,*self.stops]
        for a,b in zip(points,points[1:]):
            if math.hypot(a.x-b.x,a.y-b.y)<3: raise ValueError('Consecutive stops must be at least 3 meters apart.')
        if self.living_city:
            from .city import service_route
            points=[Point(x=x,y=y) for a,b in zip(points,points[1:]) for x,y in service_route(a,b)]
        for obj in scene(self)['objects']:
            if obj['kind']!='building': continue
            for a,b in zip(points,points[1:]):
                dx,dy=b.x-a.x,b.y-a.y
                if dx*dx+dy*dy<1e-9:continue
                t=max(0,min(1,((obj['x']-a.x)*dx+(obj['y']-a.y)*dy)/(dx*dx+dy*dy)))
                px,py=a.x+t*dx,a.y+t*dy
                if abs(px-obj['x'])<obj['sx']/2+5 and abs(py-obj['y'])<obj['sy']/2+5:
                    raise ValueError('A route segment intersects a building clearance zone.')
        return self

def slot(index: int) -> dict:
    bay=index//2;level='upper' if index%2==0 else 'lower'
    return {'id':f'uav{index+1:02d}','bay':bay+1,'level':level,'tag_id':index+1,
            'x':PITCH if bay<2 else -PITCH,'y':PITCH if bay%2==0 else -PITCH,
            'z':(UPPER_Z if level=='upper' else LOWER_Z)+PAD_Z,'side':1 if bay%2==0 else -1}

def scene(m: Mission) -> dict:
    if m.living_city:
        from .city import layout
        return {**layout(m),'name':'fieldlab','size':MAP_SIZE,'route_limit':ROUTE_LIMIT,
                'slots':[slot(i) for i in range(8)],'ground_color':'#a6aa8e',
                'rack':{'radius':RADIUS,'center_z':CENTER_Z,'half_height':HALF_HEIGHT,'upper_z':UPPER_Z,'lower_z':LOWER_Z,'pad_z':PAD_Z,'base_z':BASE_Z,'chassis_size':CHASSIS_SIZE,'deck_size':DECK_SIZE,'wheel_x':WHEEL_X,'wheel_y':WHEEL_Y}}
    import random
    rng=random.Random(m.seed)
    objects=[]
    roads=[dict(id=f'road_h_{i}',x=0,y=y,sx=230,sy=10) for i,y in enumerate((-70,-22,34,86))]
    roads += [dict(id=f'road_v_{i}',x=x,y=0,sx=10,sy=230) for i,x in enumerate((-72,-22,30,80))]
    if m.terrain=='proving_ground':
        for row,y in enumerate((-96,-46,6,60,103)):
            for col,x in enumerate((-96,-48,4,56,101)):
                i=row*5+col;sx=14+(i%3)*2;sy=14+((i+1)%3)*2
                objects.append(dict(id=f'building_{i}',kind='building',x=x,y=y,z=0,sx=sx,sy=sy,sz=6+(i%5)*2.3,yaw=0,variant=i%4))
    # Reserve the complete edited route and the carousel envelope at every stop.
    # Scenario geometry remains world-builder input, never detector input.
    active_roads=roads if m.terrain=='proving_ground' else [roads[1]]
    for i in range(m.population):
        if not m.target_present and m.target_class=='person': continue
        s=m.stops[i%len(m.stops)]
        for _ in range(400):
            angle=rng.uniform(-math.pi,math.pi);radius=rng.uniform(8,14)
            x=s.x+radius*math.cos(angle);y=s.y+radius*math.sin(angle)
            if placement_clear(x,y,'person',m,objects,active_roads):
                objects.append(dict(id=f'person_{i}',kind='person',x=x,y=y,z=0,yaw=rng.uniform(-math.pi,math.pi),variant=i%4));break
        # An exhausted search omits the actor rather than spawning an obstruction.
    parking=[]
    for road in active_roads:
        horizontal=road['sx']>road['sy']
        for along in range(-104,105,13):
            for side in (-1,1):
                offset=road['sy']/2 if horizontal else road['sx']/2
                offset+=5.5
                parking.append((along if horizontal else road['x']+side*offset,road['y']+side*offset if horizontal else along,0 if horizontal else math.pi/2))
    rng.shuffle(parking)
    for i in range(m.traffic):
        kind=['car','truck','bus'][i%3]
        if not m.target_present and kind==m.target_class: continue
        for x,y,yaw in parking:
            if placement_clear(x,y,kind,m,objects,active_roads):
                objects.append(dict(id=f'vehicle_{i}',kind=kind,x=x,y=y,z=0,yaw=yaw,variant=i%2));break
    return {'name':'fieldlab','size':MAP_SIZE,'route_limit':ROUTE_LIMIT,'objects':objects,
            'roads':active_roads,'route_clearance':{'travel_m':TRAVEL_CLEARANCE,'stop_m':STOP_CLEARANCE},
            'slots':[slot(i) for i in range(8)],'ground_color':'#a6aa8e',
            'rack':{'radius':RADIUS,'center_z':CENTER_Z,'half_height':HALF_HEIGHT,'upper_z':UPPER_Z,'lower_z':LOWER_Z,'pad_z':PAD_Z,'base_z':BASE_Z,'chassis_size':CHASSIS_SIZE,'deck_size':DECK_SIZE,'wheel_x':WHEEL_X,'wheel_y':WHEEL_Y}}

def wrap(a: float) -> float:
    return (a+math.pi)%(2*math.pi)-math.pi

def enu_to_ned(p): return [p[1],p[0],-p[2]]
def ned_to_enu(p): return [p[1],p[0],-p[2]]
