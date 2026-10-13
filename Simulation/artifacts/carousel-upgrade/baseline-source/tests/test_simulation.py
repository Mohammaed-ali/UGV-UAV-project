import math
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from backend.config import Mission,Stop,enu_to_ned,ned_to_enu,slot
from backend.vision import camera_to_world,ground_point
from backend.mission import Engine

def test_allocation_rejects_duplicates_and_unknown_aircraft():
    with pytest.raises(ValidationError):Mission(stops=[Stop(id='a',label='A',x=0,y=-22,drones=['uav01','uav01'])])
    with pytest.raises(ValidationError):Mission(stops=[Stop(id='a',label='A',x=0,y=-22,drones=['uav09'])])
    for counts in [(8,),(4,4),(3,5),(3,2,3),(0,8)]:
        next_id=1;stops=[]
        for i,n in enumerate(counts):
            stops.append(Stop(id=str(i),label=str(i),x=-12+i*15,y=-22,drones=[f'uav{k:02d}' for k in range(next_id,next_id+n)]));next_id+=n
        assert sum(len(s.drones) for s in Mission(stops=stops).stops)==8

def test_route_blocked_and_nonfinite_inputs_are_rejected():
    with pytest.raises(ValidationError):Mission(stops=[Stop(id='a',label='A',x=-13,y=20)])
    with pytest.raises(ValidationError):Mission(ugv_speed=float('nan'))

def test_coordinate_conversion_and_camera_rays():
    assert enu_to_ned([7,3,4])==[3,7,-4]
    assert ned_to_enu(enu_to_ned([7,3,4]))==[7,3,4]
    pose={'position':[7,3,10.08],'quaternion':[0,0,0,1]}
    assert camera_to_world([1,2,10],pose)==pytest.approx([5,2,0])
    assert ground_point(320,240,pose)==pytest.approx([7,3,0])
    assert ground_point(320,100,pose)[0]>7
    # A +90 degree ENU body yaw maps the same optical ray into +north.
    pose['quaternion']=[0,0,math.sin(math.pi/4),math.cos(math.pi/4)]
    assert camera_to_world([1,2,10],pose)==pytest.approx([8,1,0])

def fixture_engine(tmp_path):
    class GZ:
        sim_time=10.;received=0.;paused=False;rtf=1.;odom={'speed':0};joints={'tray_uav01_joint':1.65};contacts={};latches={'uav01':'attached'}
        poses={'carrier':{'position':[0,0,.66],'yaw':0,'quaternion':[0,0,0,1]},'uav01':{'position':[-1.5,1.65,2.42],'yaw':0,'quaternion':[0,0,0,1]}}
        def latch(self,did,attach):self.requested_latch=(did,attach)
        def tray(self,*args):pass
        def camera(self,*args):pass
    class Fleet:
        ids=['uav01']
        def status(self,did):return self.health
        def goal(self,*args):pass
        def launch(self,*args):pass
        def stop_control(self,*args):pass
        def disarm(self,did):self.disarm_requested=True
        health={'ready':True,'fresh':True,'armed':True,'offboard':True,'landed':True,'position':[-1.5,1.65,2.42],'velocity':[0,0,0],'battery':100}
    runtime=SimpleNamespace(state='running',gz=GZ(),fleet=Fleet(),health=lambda:{})
    vision=SimpleNamespace(confidence=.4,latest={},landing=set(),detector_ready=True,tag_ready=True,error=None)
    return Engine(tmp_path,runtime,vision)

def test_takeoff_requires_measured_latch_release(tmp_path):
    e=fixture_engine(tmp_path);d=e.drones['uav01'];d['state']='ARMING'
    e.tick_drone(d,e.config.stops[0],.05)
    assert d['state']=='RELEASING' and not d['deployed']
    e.tick_drone(d,e.config.stops[0],.05)
    assert d['state']=='RELEASING'
    e.runtime.gz.latches['uav01']='detached';e.tick_drone(d,e.config.stops[0],.05)
    assert d['state']=='TAKEOFF' and d['deployed']

def test_stale_or_repeated_images_do_not_confirm_target(tmp_path):
    e=fixture_engine(tmp_path);d=e.drones['uav01'];d['state']='SEARCHING'
    detection={'class':'person','confidence':.9,'position':[5,5,0],'box':[1,2,3,4]}
    e.vision.latest['uav01']={'time':1,'sync_error':0,'detections':[detection]};e.check_detection(d,e.config.stops[0]);assert not d['target']
    e.vision.latest['uav01']['time']=9.5
    for _ in range(10):e.check_detection(d,e.config.stops[0])
    assert d['confirmations']==1 and not d['target']
    for stamp in [9.6,9.7]:e.vision.latest['uav01']['time']=stamp;e.check_detection(d,e.config.stops[0])
    assert d['state']=='OBSERVING'

def test_docking_requires_contact_and_confirmed_disarm(tmp_path):
    e=fixture_engine(tmp_path);d=e.drones['uav01'];d.update(state='LANDING',deployed=True)
    e.tick_drone(d,e.config.stops[0],.05);assert d['state']=='LANDING'
    e.runtime.gz.contacts['uav01']=(True,10);e.tick_drone(d,e.config.stops[0],.05)
    e.runtime.gz.sim_time=11;e.runtime.gz.contacts['uav01']=(True,11)
    e.tick_drone(d,e.config.stops[0],.05);assert d['state']=='LANDING' and e.runtime.fleet.disarm_requested
    e.runtime.fleet.health={**e.runtime.fleet.health,'armed':False};e.tick_drone(d,e.config.stops[0],.05)
    assert d['state']=='LATCHING'

def test_tag_identity_and_age_gate_descent(tmp_path):
    e=fixture_engine(tmp_path);d=e.drones['uav01'];d['state']='TAG_ACQUIRE'
    e.vision.latest['uav01']={'time':10,'sync_error':0,'tags':[{'id':2,'position':[-1.5,1.65,2.1875]}]}
    e.tick_drone(d,e.config.stops[0],.05);assert d['state']=='TAG_ACQUIRE'
    e.vision.latest['uav01']['tags'][0]['id']=1;e.vision.latest['uav01']['time']=8
    e.tick_drone(d,e.config.stops[0],.05);assert d['state']=='TAG_ACQUIRE'

def test_brief_stale_tag_holds_descent_without_consuming_retry(tmp_path):
    e=fixture_engine(tmp_path);d=e.drones['uav01'];d['state']='DESCENDING'
    e.runtime.fleet.health={**e.runtime.fleet.health,'position':[-1.5,1.65,5.]}
    e.vision.latest['uav01']={'time':9.,'sync_error':0,'tags':[{'id':1,'position':[-1.5,1.65,2.18]}]}
    e.tick_drone(d,e.config.stops[0],.05)
    assert d['state']=='DESCENDING' and d['retry']==0
    assert d['goal']==[-1.5,1.65,5.]
    e.runtime.gz.sim_time=10.3;e.tick_drone(d,e.config.stops[0],.05)
    assert d['state']=='DESCENDING' and d['retry']==0
    e.vision.latest['uav01']['time']=10.3;e.tick_drone(d,e.config.stops[0],.05)
    assert d['tag_lost_since'] is None and d['goal'][2]<5.

def test_sustained_tag_loss_consumes_one_reacquisition_attempt(tmp_path):
    e=fixture_engine(tmp_path);d=e.drones['uav01'];d['state']='ALIGNING'
    e.tick_drone(d,e.config.stops[0],.05)
    e.runtime.gz.sim_time=12.1;e.tick_drone(d,e.config.stops[0],.05)
    assert d['state']=='TAG_ACQUIRE' and d['retry']==1
    e.runtime.gz.sim_time=12.2;e.tick_drone(d,e.config.stops[0],.05)
    assert d['retry']==1

def test_fresh_tags_do_not_make_old_target_detections_fresh(tmp_path):
    e=fixture_engine(tmp_path);d=e.drones['uav01'];d['state']='SEARCHING'
    detection={'class':'person','confidence':.9,'position':[5,5,0],'box':[1,2,3,4]}
    e.vision.latest['uav01']={'time':10,'sync_error':0,'detections':[detection]}
    e.vision.object_latest={'uav01':{'time':1,'sync_error':0,'detections':[detection]}}
    e.check_detection(d,e.config.stops[0]);assert not d['target'] and not d.get('confirmations')

def test_rack_unique_assignment():
    slots=[slot(i) for i in range(8)]
    assert len({s['tag_id'] for s in slots})==8
    assert [(s['bay'],s['level']) for s in slots]==[(b,l) for b in range(1,5) for l in ('upper','lower')]

def test_contact_requires_the_correct_aircraft_model():
    from threading import RLock
    from backend.transport import GazeboBridge
    gz=GazeboBridge.__new__(GazeboBridge);gz.lock=RLock();gz.contacts={}
    stamp=SimpleNamespace(stamp=SimpleNamespace(sec=12,nsec=0))
    wrong=SimpleNamespace(collision1=SimpleNamespace(name='carrier::tray_uav01::pad_collision'),collision2=SimpleNamespace(name='uav02::base_link::gear'))
    gz.contact_cb('uav01',SimpleNamespace(header=stamp,contact=[wrong]));assert gz.contacts['uav01']==(False,12)
    right=SimpleNamespace(collision1=wrong.collision1,collision2=SimpleNamespace(name='uav01::base_link::gear'))
    gz.contact_cb('uav01',SimpleNamespace(header=stamp,contact=[right]));assert gz.contacts['uav01']==(True,12)

def test_reset_after_fault_allows_launch_when_simulation_clock_restarts(tmp_path):
    import time
    e=fixture_engine(tmp_path);old_run=e.run_id
    e.state='FAULT';e.dock_owner='uav04';e.launch_owner='uav05'
    e.last_launch=450.;e.last_time=550.;e.last_log=550.;e.hold=True;e.abort=True
    e.seen_commands[(old_run,'old-request')]={'accepted':True}
    e.runtime.state='offline';e.configure(e.config)
    assert e.run_id!=old_run and not e.hold and not e.abort
    assert not e.seen_commands
    assert e.dock_owner is None and e.launch_owner is None
    assert e.last_time==0 and e.last_log==0
    # A subsequent run can deploy at time 10, despite the previous run's
    # corridor ownership and launch timestamp at time 450.
    e.runtime.state='running';e.runtime.gz.received=time.monotonic();e.state='DEPLOYING'
    e.runtime.gz.drive=lambda *_:None
    e.tick()
    assert e.drones['uav01']['state'] in ('PREPARING','ARMING')
    assert e.launch_owner=='uav01'
    assert (tmp_path/'artifacts/runs'/f'{e.run_id}.jsonl').exists()

def test_stop_disables_mission_ticks_before_telemetry_is_closed(tmp_path):
    from backend.runtime import Runtime
    runtime=Runtime(tmp_path);runtime.state='running';closed=[]
    def close_transport():
        assert runtime.state=='stopping'
        closed.append(True)
    runtime.gz=SimpleNamespace(close=close_transport)
    runtime.fleet=SimpleNamespace(close=close_transport)
    runtime.stop()
    assert len(closed)==2 and runtime.state=='offline'
