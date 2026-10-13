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
    with pytest.raises(ValidationError):Mission(stops=[Stop(id='a',label='A',x=4,y=6)])
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
        sim_time=10.;received=0.;paused=False;rtf=1.;odom={'speed':0};joints={f'carousel_{level}_{axis}_joint':0. for level in ('upper','lower') for axis in ('y','z')};contacts={};latches={'uav01':'attached'}
        poses={'carrier':{'position':[0,0,.66],'yaw':0,'quaternion':[0,0,0,1]},'uav01':{'position':[-1.5,1.65,2.42],'yaw':0,'quaternion':[0,0,0,1]}}
        def latch(self,did,attach):self.requested_latch=(did,attach)
        def tray(self,*args):pass
        def carousel(self,*args):pass
        def camera(self,*args):pass
    class Fleet:
        ids=['uav01']
        def status(self,did):return self.health
        def goal(self,*args):pass
        def launch(self,*args):pass
        def command(self,did,command):self.last_command=command
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
    e.vision.latest['uav01']={'time':10,'sync_error':0,'tags':[{'id':2,'position':[-1.5,1.65,2.1875],'relative_position':[0,0,-.2325]}]}
    e.tick_drone(d,e.config.stops[0],.05);assert d['state']=='TAG_ACQUIRE'
    e.vision.latest['uav01']['tags'][0]['id']=1;e.vision.latest['uav01']['time']=8
    e.tick_drone(d,e.config.stops[0],.05);assert d['state']=='TAG_ACQUIRE'

def test_brief_stale_tag_holds_descent_without_consuming_retry(tmp_path):
    e=fixture_engine(tmp_path);d=e.drones['uav01'];d['state']='DESCENDING'
    e.runtime.fleet.health={**e.runtime.fleet.health,'position':[-1.5,1.65,5.]}
    e.vision.latest['uav01']={'time':9.,'sync_error':0,'tags':[{'id':1,'position':[-1.5,1.65,2.18],'relative_position':[0,0,-2.82]}]}
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

def test_camera_preview_and_mission_release_their_own_sensor_demand():
    from threading import RLock
    from backend.transport import GazeboBridge
    gz=GazeboBridge.__new__(GazeboBridge)
    subscribed=[];unsubscribed=[]
    gz.node=SimpleNamespace(subscribe=lambda cls,topic,cb:subscribed.append(topic),unsubscribe=unsubscribed.append)
    gz.lock=RLock();gz.camera_packets={};gz.callbacks=[];gz.Image=object
    gz.enabled_cameras=set();gz.camera_consumers={};gz.preview_id=None
    gz.camera('uav01');gz.preview('uav01')
    assert len(subscribed)==1 and gz.camera_consumers['uav01']=={'mission','preview'}
    gz.camera('uav01',False)
    assert gz.enabled_cameras=={'uav01'} and not unsubscribed
    gz.preview('uav02')
    assert gz.enabled_cameras=={'uav02'} and unsubscribed==['/fieldlab/uav01/camera']
    gz.camera('uav02');gz.preview(None)
    assert gz.enabled_cameras=={'uav02'}
    gz.camera_packets['uav02']={'time':2};gz.camera('uav02',False)
    assert not gz.enabled_cameras and not gz.camera_packets

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


def test_stacked_square_has_four_distinct_pads_on_each_common_tray():
    slots=[slot(i) for i in range(8)]
    for level in ('upper','lower'):
        tray=[d for d in slots if d['level']==level]
        assert len({(d['x'],d['y']) for d in tray})==4
        assert len({d['z'] for d in tray})==1
    for i in range(0,8,2):assert (slots[i]['x'],slots[i]['y'])==(slots[i+1]['x'],slots[i+1]['y'])

def test_carousel_waits_for_measured_joint_motion():
    from backend.rack import Carousel,destinations
    c=Carousel();commands={}
    gz=SimpleNamespace(joints={},carousel=lambda level,axis,value:commands.update({f'carousel_{level}_{axis}_joint':value}))
    assert not c.ready(gz,'upper')
    assert not c.request('lower',False)
    assert c.request('lower',True)
    for _ in range(100):c.tick(gz,.05)
    assert c.moving and not c.ready(gz,'lower') and c.angle<.2
    for _ in range(600):
        gz.joints.update(commands);c.tick(gz,.05)
    assert c.ready(gz,'lower') and c.active=='lower'
    for angle in [i*math.pi/100 for i in range(101)]:
        p=destinations(angle)
        horizontal=abs(p['upper']['y']-p['lower']['y'])
        # Loaded trays have at least a 0.6 m vertical gap or a full width laterally.
        vertical=abs(2.25+p['upper']['z']-(.78+p['lower']['z']))
        assert horizontal>2.65 or vertical>.6

def test_recovery_reserves_lower_tray_before_upper(tmp_path):
    e=fixture_engine(tmp_path);stop=Stop(id='a',label='A',x=0,y=-22,drones=['uav01','uav02'])
    e.drones['uav01'].update(state='RETURNING',deployed=True)
    e.drones['uav02'].update(state='SEARCHING',deployed=True)
    assert e.recovery_level(stop)=='lower'
    e.drones['uav02']['state']='DOCKED'
    assert e.recovery_level(stop)=='upper'

def test_image_relative_alignment_corrects_estimator_frame_bias(tmp_path):
    e=fixture_engine(tmp_path);d=e.drones['uav01'];d['state']='DESCENDING'
    e.runtime.fleet.health={**e.runtime.fleet.health,'position':[16.,-20.,4.]}
    e.vision.latest['uav01']={'time':10.,'sync_error':0,'tags':[{'id':1,'position':[16.,-20.,3.2],'relative_position':[-.14,.02,-.8]}]}
    e.tick_drone(d,e.config.stops[0],.05)
    assert d['tag_error']==pytest.approx(math.hypot(.14,.02))
    assert d['goal']==pytest.approx([15.86,-19.98,4.])
    assert d['state']=='DESCENDING'

def test_native_land_uses_relative_height_even_with_world_frame_bias(tmp_path):
    e=fixture_engine(tmp_path);d=e.drones['uav01'];d['state']='DESCENDING'
    e.runtime.fleet.health={**e.runtime.fleet.health,'position':[16.,-20.,4.]}
    e.vision.latest['uav01']={'time':10.,'sync_error':0,'tags':[{'id':1,'position':[100.,100.,100.],'relative_position':[.01,.01,-.52]}]}
    e.tick_drone(d,e.config.stops[0],.05)
    assert d['state']=='LANDING' and e.runtime.fleet.last_command==21

def test_another_observer_does_not_block_target_confirmation(tmp_path):
    e=fixture_engine(tmp_path);d=e.drones['uav01'];d['state']='SEARCHING';e.drones['uav02']['state']='OBSERVING'
    detection={'class':'person','confidence':.85,'position':[5,5,0],'box':[1,2,3,4]}
    for t in [9.7,9.8]:
        e.vision.latest['uav01']={'time':t,'sync_error':0,'detections':[detection]};e.check_detection(d,e.config.stops[0])
    assert d['state']=='OBSERVING' and d['confirmations']==2

def test_archive_quota_preserves_reports_and_unrecognized_directories(tmp_path):
    from backend.storage import prune_run_archives
    runs=tmp_path/'artifacts/runs';old=runs/'fieldlab-sitl-old';old.mkdir(parents=True)
    (old/'flight.ulg').write_bytes(b'old native log')
    protected=runs/'fieldlab-sitl-with-report';protected.mkdir();(protected/'evidence.json').write_text('{}')
    (runs/'mission.jsonl').write_text('{}')
    report=prune_run_archives(tmp_path,budget_mb=0)
    assert report['removed']==['fieldlab-sitl-old'] and not old.exists()
    assert (runs/'fieldlab-sitl-old.summary.json').is_file()
    assert (runs/'mission.jsonl').is_file() and protected.is_dir()

def test_confirmation_follows_same_person_when_confidence_ranking_changes(tmp_path):
    e=fixture_engine(tmp_path);d=e.drones['uav01'];d['state']='SEARCHING'
    near={'class':'person','confidence':.8,'position':[5,5,0],'box':[1,2,3,4]}
    far={'class':'person','confidence':.7,'position':[-5,-5,0],'box':[10,20,3,4]}
    e.vision.latest['uav01']={'time':9.7,'sync_error':0,'detections':[near,far]};e.check_detection(d,e.config.stops[0])
    far['confidence']=.95
    e.vision.latest['uav01']['time']=9.8;e.check_detection(d,e.config.stops[0])
    assert d['state']=='OBSERVING' and d['target']['position']==[5,5,0]

@pytest.mark.parametrize('wheels',[4,6])
@pytest.mark.parametrize('seed',[1,42,101])
def test_edited_northbound_route_has_clear_physical_footprints(wheels,seed):
    from backend.config import scene
    from backend.placement import route_clear,ACTOR_RADIUS
    mission=Mission(wheels=wheels,seed=seed,population=18,traffic=10,stops=[
        Stop(id='a',label='A',x=-12,y=-22),Stop(id='b',label='B',x=28,y=-24),
        Stop(id='c',label='C',x=29.5,y=34.5)])
    # The old fixed car coordinate lies directly across this edited B-to-C leg.
    assert not route_clear(28,-15.2,ACTOR_RADIUS['car'],mission)
    layout=scene(mission)
    actors=[o for o in layout['objects'] if o['kind']!='building']
    assert sum(o['kind']=='person' for o in actors)==18
    assert sum(o['kind']!='person' for o in actors)==10
    assert scene(mission)==layout
    for obj in actors:
        assert route_clear(obj['x'],obj['y'],ACTOR_RADIUS[obj['kind']],mission)
        if obj['kind']=='person':
            assert not any(abs(obj['x']-r['x'])<r['sx']/2+.8 and abs(obj['y']-r['y'])<r['sy']/2+.8 for r in layout['roads'])

def test_carrier_stall_uses_measured_pose_despite_spinning_wheel_odometry(tmp_path):
    import time
    e=fixture_engine(tmp_path);gz=e.runtime.gz;gz.received=time.monotonic()
    gz.poses['carrier']={'position':[-28,-22,.74],'yaw':0,'quaternion':[0,0,0,1]}
    gz.odom={'speed':1.5};commands=[];gz.drive=lambda *args:commands.append(args)
    e.state='DRIVING';e.tick();assert not e.hold
    gz.sim_time=18.1;e.tick()
    assert e.hold and commands[-1]==(0,0)
    assert 'no measured forward progress' in e.events[-1]['message']
    e.command('resume');e.tick();assert not e.hold

def test_measured_carrier_progress_refreshes_stall_watch(tmp_path):
    import time
    e=fixture_engine(tmp_path);gz=e.runtime.gz;gz.received=time.monotonic()
    gz.poses['carrier']={'position':[-28,-22,.74],'yaw':0,'quaternion':[0,0,0,1]}
    gz.drive=lambda *args:None;e.state='DRIVING';e.tick()
    gz.sim_time=17.;gz.poses['carrier']['position'][0]=-27.5;e.tick()
    gz.sim_time=24.;gz.poses['carrier']['position'][0]=-27.;e.tick()
    assert not e.hold


def test_landing_goal_uses_image_capture_estimate_not_current_translation(tmp_path):
    e=fixture_engine(tmp_path);d=e.drones['uav01'];d['state']='ALIGNING'
    e.runtime.fleet.health={**e.runtime.fleet.health,'position':[2.,3.,6.]}
    capture={'position':[1.,2.,6.],'quaternion':[0.,0.,0.,1.]}
    e.runtime.fleet.perception_pose=lambda did,stamp:(capture,0.)
    e.vision.latest['uav01']={'time':10.,'sync_error':0.,'tags':[{'id':1,'relative_position':[.2,.1,-3.], 'camera_position':[-.1,-.2,2.92]}]}
    e.tick_drone(d,e.config.stops[0],.05)
    assert d['goal'][:2]==pytest.approx([1.2,2.1])
    e.runtime.fleet.health={**e.runtime.fleet.health,'position':[2.4,3.3,6.]}
    e.tick_drone(d,e.config.stops[0],.05)
    assert d['goal'][:2]==pytest.approx([1.2,2.1])
    e.runtime.fleet.perception_pose=lambda did,stamp:(capture,.5)
    e.tick_drone(d,e.config.stops[0],.05)
    assert d['goal']==[2.4,3.3,6.]


def test_service_junction_is_waypoint_not_final_arrival(tmp_path):
    import time
    e=fixture_engine(tmp_path)
    e.config=Mission(living_city=True,start={'x':28,'y':-22},stops=[Stop(id='c',label='C',x=30,y=34.5)])
    e.city=SimpleNamespace(tick=lambda:None,violations={});e.record_snapshot=lambda:None
    e.state='DRIVING';e.runtime.gz.received=time.monotonic()
    e.runtime.gz.poses['carrier']['position']=[29.55,-22,.74]
    e.runtime.gz.drive=lambda v,w:setattr(e.runtime.gz,'last_drive',(v,w))
    e.tick()
    assert e.state=='DRIVING' and e.drive_waypoint==2
    assert e.runtime.gz.last_drive[0]==0 and e.runtime.gz.last_drive[1]>0
    e.runtime.gz.poses['carrier']['position']=[30,34.1,.74]
    e.runtime.gz.poses['carrier']['yaw']=math.pi/2
    e.tick()
    assert e.state=='DEPLOYING'


def test_px4_image_alignment_uses_sample_clock_despite_delayed_callbacks():
    from backend.px4 import Fleet
    import threading
    from collections import deque
    fleet=Fleet.__new__(Fleet);fleet.data={'uav01':{}};fleet.commands=[]
    fleet.origins={'uav01':[0.,0.,0.]};fleet.gazebo=SimpleNamespace(sim_time=99.)
    fleet.perception_lock=threading.RLock();fleet.perception_history={'uav01':deque(maxlen=150)};fleet.attitude_history={'uav01':deque(maxlen=150)}
    fleet.receive('uav01','vehicle_attitude',SimpleNamespace(q=[1.,0.,0.,0.],timestamp_sample=10_000_000))
    fleet.receive('uav01','vehicle_local_position',SimpleNamespace(x=2.,y=1.,z=-6.,xy_valid=True,z_valid=True,timestamp_sample=10_000_000))
    pose,sync=fleet.perception_pose('uav01',10.)
    assert pose['time']==10. and sync==0.
    assert pose['position']==[1.,2.,6.]
    assert fleet.perception_pose('uav01',10.5)[1]==.5
    fleet.receive('uav01','vehicle_local_position',SimpleNamespace(x=2.,y=1.,z=-6.,xy_valid=True,z_valid=True,timestamp_sample=11_000_000))
    assert fleet.perception_pose('uav01',11.)[1]==1. # Old attitude cannot authorize fresh geometry.


def test_slow_loaded_carousel_uses_measured_progress_beyond_old_timeout():
 from backend.rack import Carousel,destinations
 c=Carousel();commands={};physical_angle=0.
 gz=SimpleNamespace(joints={f'carousel_{l}_{a}_joint':v for l,values in destinations(0).items() for a,v in values.items()},carousel=lambda level,axis,value:commands.update({f'carousel_{level}_{axis}_joint':value}))
 assert c.request('lower',True)
 for _ in range(2800):
  physical_angle=min(c.angle,physical_angle+.035*.05)
  gz.joints={f'carousel_{l}_{a}_joint':v for l,values in destinations(physical_angle).items() for a,v in values.items()}
  c.tick(gz,.05)
  if not c.moving or c.error:break
 assert c.elapsed>80 and c.ready(gz,'lower') and not c.error

def test_carousel_fails_when_measured_gondolas_stop_progressing():
 from backend.rack import Carousel,destinations
 c=Carousel();gz=SimpleNamespace(joints={f'carousel_{l}_{a}_joint':v for l,values in destinations(0).items() for a,v in values.items()},carousel=lambda *args:None)
 assert c.request('lower',True)
 for _ in range(450):c.tick(gz,.05)
 assert c.error=='Carousel physical progress stalled' and not c.ready(gz,'lower')


def test_image_pose_accepts_attitude_that_arrived_after_position_callback():
    from backend.px4 import Fleet
    from collections import deque
    import threading
    fleet=Fleet.__new__(Fleet);fleet.data={'uav01':{}};fleet.commands=[]
    fleet.origins={'uav01':[0.,0.,0.]};fleet.gazebo=SimpleNamespace(sim_time=99.)
    fleet.perception_lock=threading.RLock();fleet.perception_history={'uav01':deque(maxlen=150)};fleet.attitude_history={'uav01':deque(maxlen=150)}
    fleet.receive('uav01','vehicle_attitude',SimpleNamespace(q=[1.,0.,0.,0.],timestamp_sample=9_000_000))
    fleet.receive('uav01','vehicle_local_position',SimpleNamespace(x=2.,y=1.,z=-6.,xy_valid=True,z_valid=True,timestamp_sample=10_000_000))
    assert fleet.perception_pose('uav01',10.)[1]==1.
    fleet.receive('uav01','vehicle_attitude',SimpleNamespace(q=[1.,0.,0.,0.],timestamp_sample=10_000_000))
    pose,sync=fleet.perception_pose('uav01',10.)
    assert sync==0. and pose['position']==[1.,2.,6.]
    assert pose['attitude_time']==10.
    assert fleet.perception_pose('uav01',10.5)[1]==.5


def test_gazebo_clock_cannot_be_rewound_by_delayed_stats():
    import threading
    from backend.transport import GazeboBridge
    gz=GazeboBridge.__new__(GazeboBridge);gz.lock=threading.RLock();gz.sim_time=0.
    gz.clock_cb(SimpleNamespace(sim=SimpleNamespace(sec=25,nsec=0)))
    gz.stats_cb(SimpleNamespace(sim_time=SimpleNamespace(sec=22,nsec=0),real_time_factor=.5,paused=False))
    assert gz.sim_time==25. and gz.rtf==.5
    gz.clock_cb(SimpleNamespace(sim=SimpleNamespace(sec=24,nsec=0)))
    assert gz.sim_time==25.


def test_bounded_mission_trace_omits_repeated_history_without_mutating_live_target(tmp_path):
    import json
    e=fixture_engine(tmp_path);d=e.drones['uav01'];d['target']={'id':'Person-001','position':[0,0,0],'history':[{'time':9.}]}
    e.record_snapshot()
    row=json.loads((tmp_path/'artifacts/runs'/f'{e.run_id}.jsonl').read_text().splitlines()[0])
    assert 'history' not in row['drones'][0]['target']
    assert d['target']['history']==[{'time':9.}]
    assert row['drones'][0]['position']==e.snapshot()['drones'][0]['position']
