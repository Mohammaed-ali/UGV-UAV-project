import math
from types import SimpleNamespace
import pytest
from backend.config import Mission,ActorPlacement,Stop
from backend.city import City,layout,search_classes,matches_class,survey_goal

@pytest.mark.parametrize('field,maximum',[('ugv_speed',10.),('traffic_speed',20.),('walking_speed',5.)])
def test_adjustable_speed_limits_accept_requested_maximum_and_reject_excess(field,maximum):
 assert getattr(Mission(living_city=True,**{field:maximum}),field)==maximum
 with pytest.raises(ValueError):Mission(**{field:maximum+.1})

def test_three_class_search_preserves_legacy_and_stop_overrides():
 m=Mission(living_city=True,target_classes=['person','car','bus'])
 assert search_classes(m)==['person','car','bus']
 assert search_classes(m,Stop(id='s',label='S',x=30,y=34.5,target_class='truck'))==['truck']
 assert matches_class('bus',search_classes(m)) and not matches_class('truck',search_classes(m))
 with pytest.raises(ValueError):Mission(target_classes=['person','car','bus','truck'])
 with pytest.raises(ValueError):Mission(target_classes=['person','person'])
 assert search_classes(Mission(target_class='truck'))==['truck']


def test_multiclass_survey_scans_sidewalk_and_vehicle_networks():
 m=Mission(living_city=True,target_classes=['person','car','bus'])
 stop=Stop(id='s',label='S',x=30,y=34.5,search_radius=20)
 public=[dict(kind='sidewalk',points=[[36,0],[36,90],[36,0]]),dict(kind='vehicle',points=[[42.5,0],[42.5,90],[42.5,0]])]
 assert survey_goal(m,stop,0,0,public)[0]==36
 assert survey_goal(m,stop,0,1,public)[0]==42.5
 assert survey_goal(m,stop,0,2,public)[0]==42.5


def test_free_actor_placement_is_stationary_and_persists_through_config_roundtrip():
 m=Mission(living_city=True,population=1,traffic=0,actor_placements=[ActorPlacement(id='person_0',x=-85,y=40)])
 restored=Mission.model_validate_json(m.model_dump_json());obj=next(o for o in layout(restored)['objects'] if o['id']=='person_0')
 assert (obj['x'],obj['y'])==(-85,40) and obj['parked']

@pytest.mark.parametrize('position',[(30,10),(0,-22),(-26,14)])
def test_actor_placement_rejects_protected_lane_or_building(position):
 with pytest.raises(ValueError):Mission(living_city=True,population=1,traffic=0,actor_placements=[ActorPlacement(id='person_0',x=position[0],y=position[1])])


def test_actor_placement_rejects_occupied_space_and_missing_actors():
 m=Mission(living_city=True,population=2,traffic=0);other=next(o for o in layout(m)['objects'] if o['id']=='person_1')
 with pytest.raises(ValueError):Mission(living_city=True,population=2,traffic=0,actor_placements=[ActorPlacement(id='person_0',x=other['x'],y=other['y'])])
 with pytest.raises(ValueError):Mission(living_city=True,population=0,traffic=0,actor_placements=[ActorPlacement(id='person_0',x=-85,y=40)])


def test_live_actor_relocation_uses_native_route_and_pose_and_resumes_the_correct_lane():
 calls=[];m=Mission(living_city=True,population=1,traffic=0)
 gz=SimpleNamespace(sim_time=1.,paused=False,poses={},actor_velocity=lambda *a:calls.append(('velocity',a)),actor_route=lambda *a:calls.append(('route',a)),place_actor=lambda *a:calls.append(('pose',a)))
 city=City(m,gz)
 result=city.relocate('person_0',-85,40,0)
 assert result['motion']=='stationary off lane' and not result['persistent']
 assert calls[0][0]=='velocity' and calls[1]==('route',('person_0',[])) and calls[2][0]=='pose'
 calls.clear();result=city.relocate('person_0',36,26,0)
 assert result['motion']=='following assigned path' and not city.actors['person_0']['parked']
 assert calls[-1][0]=='route' and len(calls[-1][1][1])>3


def test_live_relocation_does_not_change_actor_if_native_world_rejects_it():
 m=Mission(living_city=True,population=1,traffic=0)
 def reject(*args):raise ValueError('Physics rejected')
 gz=SimpleNamespace(sim_time=1.,paused=False,poses={},actor_velocity=lambda *a:None,actor_route=lambda *a:None,place_actor=reject)
 city=City(m,gz);before=dict(city.actors['person_0'])
 with pytest.raises(ValueError):city.relocate('person_0',-85,40,0)
 assert city.actors['person_0']==before


def test_three_aircraft_can_observe_three_confirmed_camera_classes_at_once(tmp_path):
 from backend.mission import Engine
 rows=[dict(id=f'track-{i}',drone=f'uav{i+1:02d}',age=0.,ambiguous=False,confidence=.9,last_seen=.5,position=[36.,26.,0.],**{'class':kind}) for i,kind in enumerate(['person','car','bus'])]
 vision=SimpleNamespace(registry=SimpleNamespace(snapshot=lambda now:rows))
 e=Engine(tmp_path,SimpleNamespace(gz=SimpleNamespace(sim_time=.5,camera=lambda *args:None)),vision);e.config=Mission(living_city=True,target_classes=['person','car','bus'])
 stop=Stop(id='s',label='S',x=30,y=34.5,drones=['uav01','uav02','uav03'])
 for did in stop.drones:e.drones[did]['state']='SEARCHING';e.check_detection(e.drones[did],stop)
 assert all(e.drones[did]['state']=='OBSERVING' for did in stop.drones)
 assert [e.drones[did]['target']['class'] for did in stop.drones]==['person','car','bus']


def test_tentative_image_can_centre_search_without_creating_a_confirmed_target(tmp_path):
 from backend.mission import Engine
 vision=SimpleNamespace(registry=SimpleNamespace(snapshot=lambda now:[]),object_latest={'uav01':dict(time=.5,sync_error=.1,detections=[dict(position=[36.,26.,0.],confidence=.6,**{'class':'person'})])})
 e=Engine(tmp_path,SimpleNamespace(gz=SimpleNamespace(sim_time=.5)),vision);e.config=Mission(living_city=True);goals=[];e.set_goal=lambda d,p:goals.append(p)
 d=e.drones['uav01'];d['state']='SEARCHING';stop=Stop(id='s',label='S',x=30,y=34.5)
 e.check_detection(d,stop)
 assert goals==[[36.,26.,9.]] and d['target'] is None and d['state']=='SEARCHING'
 vision.object_latest['uav01']['time']=-10;goals.clear();e.check_detection(d,stop)
 assert not goals


def test_high_speed_ugv_requests_braking_before_its_physical_stopping_distance():
 from backend.driving import city_drive
 assert city_drive(1000,0,0,0,10)[0]==10
 assert city_drive(100,0,10,0,10)[0]<9.5
 assert city_drive(30,0,10,0,10)[0]<5.3
