from __future__ import annotations

import math
from typing import Literal
from pydantic import BaseModel, Field, model_validator, ConfigDict

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Point(StrictModel):
    x: float = Field(ge=-68, le=68)
    y: float = Field(ge=-68, le=68)

class Stop(Point):
    id: str = Field(min_length=1, max_length=40, pattern=r'^[a-zA-Z0-9_-]+$')
    label: str = Field(min_length=1, max_length=48)
    drones: list[str] = Field(default_factory=list, max_length=8)
    search_radius: float = Field(default=12, ge=3, le=25)
    target_class: Literal['person','car','truck','bus'] | None = None
    search_timeout: float | None = Field(default=None, ge=5, le=1800)
    loiter_seconds: float | None = Field(default=None, ge=0, le=1800)

class Mission(StrictModel):
    version: Literal[1] = 1
    name: str = Field(default='Perimeter survey', max_length=80)
    wheels: Literal[4,6] = 4
    seed: int = Field(default=42, ge=0, le=2147483647)
    terrain: Literal['field','proving_ground'] = 'proving_ground'
    population: int = Field(default=6, ge=0, le=16)
    traffic: int = Field(default=3, ge=0, le=8)
    target_present: bool = True
    target_class: Literal['person','car','truck','bus'] = 'person'
    ugv_speed: float = Field(default=1.5, ge=.2, le=3)
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
    start: Point = Field(default_factory=lambda: Point(x=-28,y=-22))
    stops: list[Stop] = Field(default_factory=lambda: [
        Stop(id='alpha',label='Alpha',x=-12,y=-22,drones=['uav01','uav02','uav03']),
        Stop(id='bravo',label='Bravo',x=16,y=-22,drones=['uav04','uav05']),
        Stop(id='charlie',label='Charlie',x=30,y=3,drones=['uav06','uav07','uav08'])
    ],min_length=1,max_length=16)

    @model_validator(mode='after')
    def valid_plan(self):
        ids=[s.id for s in self.stops]
        if len(set(ids))!=len(ids): raise ValueError('Stop IDs must be unique.')
        assigned=[d for s in self.stops for d in s.drones]
        available={f'uav{i:02d}' for i in range(1,9)}
        if any(d not in available for d in assigned): raise ValueError('Unknown drone ID.')
        if len(assigned)!=len(set(assigned)): raise ValueError('Each drone can be assigned to only one stop per mission.')
        points=[self.start,*self.stops]
        for a,b in zip(points,points[1:]):
            if math.hypot(a.x-b.x,a.y-b.y)<3: raise ValueError('Consecutive stops must be at least 3 meters apart.')
        for obj in scene(self)['objects']:
            if obj['kind']!='building': continue
            for a,b in zip(points,points[1:]):
                dx,dy=b.x-a.x,b.y-a.y
                t=max(0,min(1,((obj['x']-a.x)*dx+(obj['y']-a.y)*dy)/(dx*dx+dy*dy)))
                px,py=a.x+t*dx,a.y+t*dy
                if abs(px-obj['x'])<obj['sx']/2+3 and abs(py-obj['y'])<obj['sy']/2+3:
                    raise ValueError('A route segment intersects a building clearance zone.')
        return self

def slot(index: int) -> dict:
    return {'id':f'uav{index+1:02d}','bay':index//2+1,'level':'upper' if index%2==0 else 'lower',
            'tag_id':index+1,'x':-1.5+(index//2),'y':0.,'z':1.5 if index%2==0 else .7,'side':1 if index//2%2==0 else -1}

def scene(m: Mission) -> dict:
    import random
    rng=random.Random(m.seed)
    objects=[]
    if m.terrain=='proving_ground':
        for i,(x,y,sx,sy,z) in enumerate([(-35,17,12,10,7),(-13,20,10,10,9),(9,25,14,10,7),(43,25,10,14,11),(-43,-10,8,12,5)]):
            objects.append(dict(id=f'building_{i}',kind='building',x=x,y=y,z=0,sx=sx,sy=sy,sz=z,yaw=0))
    # Scenario placement belongs to the world builder. Vision never receives this list.
    for i in range(m.population):
        if not m.target_present and m.target_class=='person': continue
        s=m.stops[i%len(m.stops)]
        objects.append(dict(id=f'person_{i}',kind='person',x=s.x+rng.uniform(-8,8),y=s.y+rng.uniform(6,12),z=0,yaw=rng.uniform(-math.pi,math.pi),variant=i%4))
    for i in range(m.traffic):
        kind=['car','truck','bus'][i%3]
        if not m.target_present and kind==m.target_class: continue
        objects.append(dict(id=f'vehicle_{i}',kind=kind,x=-20+i*18,y=-7,z=0,yaw=0,variant=i%2))
    return {'name':'fieldlab','size':150,'objects':objects,'slots':[slot(i) for i in range(8)],'ground_color':'#a6aa8e'}

def wrap(a: float) -> float:
    return (a+math.pi)%(2*math.pi)-math.pi

def enu_to_ned(p): return [p[1],p[0],-p[2]]
def ned_to_enu(p): return [p[1],p[0],-p[2]]
