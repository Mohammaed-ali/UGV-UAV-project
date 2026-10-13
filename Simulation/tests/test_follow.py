from types import SimpleNamespace
import numpy as np
from backend.config import Mission
from backend.follow import Follow
from backend.tracking import Registry

class Harness:
 def __init__(self,registry,now=1.):
  self.vision=SimpleNamespace(registry=registry);self.time=now;self.drones={'uav01':{'state':'TARGET_TRACKING','deployed':True}};self.goals=[]
 def now(self):return self.time
 def set_goal(self,d,goal):self.goals.append(goal)
 def transition(self,d,state,reason):d['state']=state

def confirmed():
 r=Registry();frame=np.full((480,640,3),100,np.uint8)
 for i in range(3):r.update('uav01',i*.2,[dict(class_='person',**{'class':'person'},confidence=.8,position=[36.,40.,0.],box=[250,190,35,65])],frame,'City')
 key=r.snapshot(.4)[0]['id'];r.select(key,.4);return r,key

def test_prediction_stops_after_bounded_horizon_and_uncertainty_grows():
 r,key=confirmed();r.tracks[key]['velocity']=[1.,0.]
 assert r.get(key,20)['predicted_position']==r.get(key,60)['predicted_position']
 assert r.get(key,20)['uncertainty_m']>r.get(key,1)['uncertainty_m']

def test_visual_update_does_not_claim_a_new_detector_classification():
 r,key=confirmed();frame=np.full((480,640,3),100,np.uint8)
 r.refresh_visual(key,'uav01',.5,[251,191,35,65],[36.1,40.,0.],frame,.9,'City','CSRT')
 row=r.get(key,.5);assert row['source']=='CSRT' and row['last_detection']==.4 and row['last_seen']==.5

def test_missing_camera_observation_times_out_to_return_without_identity_switch():
 r,key=confirmed();e=Harness(r);f=Follow(key,'uav01',1,Mission(reacquire_seconds=5,no_target_policy='return'));f.tracking_started=1
 e.time=10;f.tick(e,e.drones['uav01'],[30,34,12],12)
 assert f.outcome=='lost' and f.state=='RETURNING' and f.target_id==key
 assert any(x['state']=='LOST' for x in f.timeline)

def test_lost_target_uses_configured_wait_then_returns():
 r,key=confirmed();e=Harness(r);f=Follow(key,'uav01',1,Mission(reacquire_seconds=5,no_target_policy='hover',loiter_seconds=3))
 e.time=10;f.tick(e,e.drones['uav01'],[30,34,12],12);assert f.state=='LOITERING'
 e.time=14;f.tick(e,e.drones['uav01'],[30,34,12],12);assert f.outcome=='lost' and f.state=='RETURNING'

def test_active_follow_keeps_goal_bounded_by_static_flight_planner():
 from backend.navigation import FlightPlanner
 planner=FlightPlanner([],boundary=116.)
 assert planner.goal('uav01',[30,34,12],[200,-200,12])==[116.,-116.,12]


def test_public_search_follows_map_turn_without_refreshing_sighting():
 from backend.navigation import public_search_candidate
 paths=[{'kind':'sidewalk','points':[[0,0],[0,20],[20,20],[20,0],[0,0]]}, {'kind':'vehicle','points':[[100,100],[110,100],[100,100]]}]
 goal=public_search_candidate(paths,[0,10,0],[0,1],15,0,'sidewalk')
 assert goal==[5.,20.]
 assert public_search_candidate(paths,[50,50,0],[0,1],15,0,'sidewalk') is None
 r,key=confirmed();before=r.get(key,.4)['last_seen']
 e=Harness(r,10);f=Follow(key,'uav01',.4,Mission(reacquire_seconds=60),paths)
 f.tick(e,e.drones['uav01'],[30,34,12],12)
 assert r.get(key,10)['last_seen']==before and f.state=='REACQUIRING'


def test_large_vehicle_follow_reserves_camera_coverage_and_stable_heading():
 r,key=confirmed();r.tracks[key].update(**{'class':'car','velocity':[0.,1.2]})
 e=Harness(r,.5);f=Follow(key,'uav01',.5,Mission(tracking_distance=3.))
 f.tick(e,e.drones['uav01'],[30,34,12],12)
 assert f.state=='TRACKING'
 # The car centre stays near the camera centre, leaving room for its whole body.
 assert 39.<e.goals[-1][1]<40.5
 assert 'follow_yaw' not in e.drones['uav01']


def test_follow_goal_correction_cannot_jump_faster_than_aircraft_limit():
 import math
 r,key=confirmed();e=Harness(r,.5);f=Follow(key,'uav01',.5,Mission(flight_speed=3.))
 f.tick(e,e.drones['uav01'],[30,34,12],12);before=e.goals[-1]
 r.tracks[key]['position']=[39.,40.,0.];r.tracks[key]['last_seen']=.55;e.time=.55
 f.tick(e,e.drones['uav01'],[30,34,12],12)
 assert math.dist(before[:2],e.goals[-1][:2])<=.151
 assert f.state=='TRACKING'


def test_repeated_finish_preserves_reserved_landing_phase():
 r,key=confirmed();e=Harness(r);f=Follow(key,'uav01',1,Mission())
 f.finish(e,'Lost target','lost');e.drones['uav01']['state']='DESCENDING';e.time=10
 f.finish(e,'Operator stopped tracking','stopped')
 assert e.drones['uav01']['state']=='DESCENDING' and f.outcome=='lost' and f.finished_at==1

def test_recall_does_not_restart_an_existing_approach():
 from backend.mission import Engine
 e=Engine.__new__(Engine);e.hold=True;e.state='DEPLOYING';e.follow=None
 e.drones={'uav01':{'id':'uav01','state':'DESCENDING','deployed':True}}
 e.event=lambda *args:None
 def unexpected_transition(*args):raise AssertionError('Recall restarted landing')
 e.transition=unexpected_transition
 e.command('recall_all')
 assert not e.hold and e.drones['uav01']['state']=='DESCENDING'


def instant_engine(tmp_path,observer='uav02'):
 from backend.mission import Engine
 r,key=confirmed();r.tracks[key]['drone']=observer
 goals=[]
 def status(did):
  return dict(fresh=True,armed=True,offboard=True,ready=False,landed=False,position=[36.,40.,12.],battery=100.)
 fleet=SimpleNamespace(ids=['uav01','uav02','uav03','uav04'],status=status,goal=lambda did,p,yaw:goals.append((did,p)),stop_control=lambda did:None)
 gz=SimpleNamespace(sim_time=.5,joints={},poses={'carrier':dict(position=[30.,34.5,.74],yaw=0.)},latches={},drive=lambda *args:None,camera=lambda *args:None)
 e=Engine(tmp_path,SimpleNamespace(state='running',fleet=fleet,gz=gz),SimpleNamespace(registry=r,sites={}))
 e.config=Mission(living_city=True,early_selection=False);e.state='DEPLOYING';e.events=[]
 for did in ['uav01','uav02']:e.drones[did].update(state='OBSERVING',deployed=True)
 return e,key,goals


def test_track_switches_latest_lower_observer_immediately_while_other_aircraft_return(tmp_path):
 e,key,goals=instant_engine(tmp_path)
 # Neither deck readiness nor the legacy early-selection option delays flight.
 e.carousel.moving=True;e.carousel.active='lower'
 e.start_tracking(key)
 assert e.state=='TRACKING' and e.follow.drone_id=='uav02'
 assert e.follow.state=='TRACKING' and e.follow.tracking_started==.5
 assert e.drones['uav02']['state']=='TARGET_TRACKING' and goals[-1][0]=='uav02'
 assert e.drones['uav01']['state']=='RETURNING'
 assert set(e.follow_stop.drones)=={'uav01','uav02'}
 assert e.recovery_level(e.follow_stop)=='lower'


def test_switch_preserves_an_existing_landing_and_cancels_only_unarmed_preparation(tmp_path):
 e,key,goals=instant_engine(tmp_path)
 e.drones['uav03'].update(state='DESCENDING',deployed=True);e.dock_owner='uav03'
 e.drones['uav04'].update(state='PREPARING',deployed=False);e.launch_owner='uav04'
 e.start_tracking(key)
 assert e.follow.state=='TRACKING' and goals
 assert e.drones['uav03']['state']=='DESCENDING' and e.dock_owner=='uav03'
 assert e.drones['uav04']['state']=='STORED' and e.launch_owner is None
 assert 'uav03' in e.follow_stop.drones


def test_track_click_accepts_target_id_without_prior_selection_and_does_not_fake_freshness(tmp_path):
 e,key,goals=instant_engine(tmp_path);e.vision.registry.selected=None;e.runtime.gz.sim_time=10.
 e.start_tracking(key)
 assert e.vision.registry.selected==key and e.follow.target_id==key
 assert e.follow.state=='REACQUIRING' and e.follow.tracking_started is None
 assert e.vision.registry.get(key,10.)['last_seen']==.4


def test_tracking_tick_services_other_recoveries_and_waits_for_all_aircraft(tmp_path):
 import time
 e,key,goals=instant_engine(tmp_path);e.start_tracking(key)
 e.runtime.gz.paused=False;e.runtime.gz.carousel=lambda *args:None;e.runtime.gz.received=time.monotonic();e.city=SimpleNamespace(tick=lambda:None)
 calls=[];e.tick_drone=lambda d,stop,dt:calls.append(d['id']);e.record_snapshot=lambda:None
 e.tick()
 assert set(calls)=={'uav01','uav02'}
 e.drones['uav02']['state']='DOCKED';calls.clear();e.tick()
 assert calls==['uav01'] and e.state=='TRACKING'
 e.drones['uav01']['state']='DOCKED';e.index_carousel=lambda level:True;e.tick()
 assert e.state=='COMPLETE' and e.follow.state=='DOCKED'


def test_track_cannot_interrupt_an_aircraft_below_launch_clearance(tmp_path):
 import pytest
 e,key,goals=instant_engine(tmp_path,'uav01');e.drones['uav01']['state']='TAKEOFF';e.drones['uav02']['state']='STORED'
 e.config.tracking_uav='uav01';e.runtime.fleet.status=lambda did:dict(fresh=True,armed=True,offboard=True,ready=False,landed=False,position=[30.,34.5,4.],battery=100.)
 with pytest.raises(ValueError,match='No healthy airborne'):e.start_tracking(key)
 assert e.state=='DEPLOYING' and not goals
