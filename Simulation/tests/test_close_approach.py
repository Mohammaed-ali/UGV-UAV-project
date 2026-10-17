import math
from types import SimpleNamespace
import numpy as np
import pytest
from backend.config import Mission
from backend.service import CloseApproach,depth_observation,decode_depth,AIRCRAFT_RADIUS


def target(now=1.):
    return {'id':'Vehicle-001','last_seen':now,'age':0.,'ambiguous':False,
            'identity_confidence':.95,'drone':'uav01','position':[0.,0.,0.],
            'velocity':[0.,0.],'box':[230.,150.,180.,180.]}


def packet(now=1.,height=4.,surface=2.):
    return {'time':now,'image':np.full((120,160),height-.08-surface,np.float32)}


def test_metric_depth_measures_surface_to_aircraft_envelope_not_target_centre():
    pose={'position':[0.,0.,4.],'quaternion':[0.,0.,0.,1.]}
    obs=depth_observation(packet(),pose,pose['position'],target(),1.)
    assert obs['clearance_m']==pytest.approx(4.-2.-AIRCRAFT_RADIUS,abs=1e-6)
    assert obs['surface_point'][2]==pytest.approx(2.,abs=1e-6)
    assert obs['alignment_m']<.06
    assert math.dist(pose['position'],obs['nearest_point'])-AIRCRAFT_RADIUS==pytest.approx(obs['clearance_m'])


@pytest.mark.parametrize('bad', ['old','future','unpaired','empty','ground'])
def test_range_rejects_stale_unpaired_invalid_and_ground_only_images(bad):
    p=packet();t=target();pose={'position':[0.,0.,4.],'quaternion':[0.,0.,0.,1.]}
    if bad=='old':p['time']=0.
    if bad=='future':p['time']=2.
    if bad=='unpaired':t['last_seen']=0.
    if bad=='empty':p['image'][:]=np.nan
    if bad=='ground':p=packet(surface=0.)
    assert depth_observation(p,pose,pose['position'],t,1.) is None


def test_float_depth_decoder_respects_stride_and_rejects_rgb():
    rows=np.array([[1.,2.,99.],[3.,4.,99.]],dtype='<f4')
    formats=SimpleNamespace(values_by_number={1:SimpleNamespace(name='R_FLOAT32'),2:SimpleNamespace(name='RGB_INT8')})
    descriptor=SimpleNamespace(fields_by_name={'pixel_format_type':SimpleNamespace(enum_type=formats)})
    msg=SimpleNamespace(width=2,height=2,step=12,data=rows.tobytes(),pixel_format_type=1,DESCRIPTOR=descriptor)
    assert decode_depth(msg).tolist()==[[1.,2.],[3.,4.]]
    msg.pixel_format_type=2
    assert decode_depth(msg) is None


class Harness:
    def __init__(self):
        self.time=1.;self.goals=[];self.sensor=[]
        self.runtime=SimpleNamespace(gz=SimpleNamespace(proximity=lambda *a:self.sensor.append(a)),
                                     fleet=SimpleNamespace(status=lambda did:{'velocity':[0.,0.,0.]}))
    def now(self):return self.time
    def set_goal(self,d,p):self.goals.append(list(p))


def controller(height=4.):
    e=Harness();c=CloseApproach(Mission());d={'id':'uav01'};pos=[0.,0.,height]
    c.start(1.,pos,.5)
    c.sample=lambda *args:{'surface_point':[0.,0.,2.],'nearest_point':[0.,0.,2.],
                          'clearance_m':height-2.-AIRCRAFT_RADIUS,'alignment_m':0.,
                          'time':e.time,'tilt':0.}
    return e,c,d,pos


def test_approach_descends_at_configured_rate_only_with_fresh_centred_depth():
    e,c,d,pos=controller()
    e.time=1.25;c.tick(e,d,pos,12.,target(e.time))
    assert e.goals[-1][2]==pytest.approx(3.9)
    assert e.goals[-1][:2]==[0.,0.]
    c.sample=lambda *a:None;e.time=1.5
    c.tick(e,d,pos,12.,target(e.time))
    assert e.goals[-1]==pos and c.state=='APPROACHING'


@pytest.mark.parametrize('change', ['stale','ambiguous','other-camera','weak-identity','too-fast','boundary'])
def test_loss_uncertainty_speed_and_boundary_force_vertical_backoff(change):
    e,c,d,pos=controller();t=target()
    if change=='stale':t['age']=1.
    if change=='ambiguous':t['ambiguous']=True
    if change=='other-camera':t['drone']='uav02'
    if change=='weak-identity':t['identity_confidence']=.6
    if change=='too-fast':t['velocity']=[10.,0.]
    if change=='boundary':t['position']=[116.,0.,0.]
    c.tick(e,d,pos,12.,t)
    assert c.state=='RETREATING' and e.goals[-1]==[0.,0.,12.]
    assert c.target_point is None


def test_depth_minimum_buffer_prevents_further_descent():
    e,c,d,pos=controller(height=3.1)
    c.tick(e,d,pos,12.,target())
    assert c.state=='RETREATING' and e.goals[-1][2]==12.


def test_close_hold_requires_stability_then_continues_until_operator_backoff():
    e,c,d,pos=controller(height=3.25)
    for stamp in [1.,1.25,1.5,1.75,2.]:
        e.time=stamp;c.tick(e,d,pos,12.,target(stamp))
    assert c.state=='HOLDING' and e.goals[-1][2]==pytest.approx(3.25)
    assert not any('spray' in k or 'deliver' in k or 'payload' in k for k in c.snapshot(2.))
    c.retreat(2.,'Operator backoff');c.tick(e,d,pos,12.,target(2.))
    assert c.state=='RETREATING' and e.goals[-1]==[0.,0.,12.]
    c.tick(e,d,[0.,0.,12.],12.,target(2.))
    assert c.state=='CANCELLED' and e.sensor[-1]==('uav01',False)


def test_range_display_expires_and_missing_depth_never_claims_close_hold():
    e,c,d,pos=controller();c.tick(e,d,pos,12.,target())
    assert c.snapshot(1.)['measured_clearance_m'] is not None
    assert c.snapshot(2.)['measured_clearance_m'] is None
    c.sample=lambda *a:None;e.time=5.
    c.tick(e,d,pos,12.,target(5.))
    assert c.state=='APPROACHING' and e.goals[-1]==pos
    e.time=5.5;c.tick(e,d,pos,12.,target(5.5))
    assert c.state=='RETREATING' and 'unavailable' in c.reason


def test_config_rejects_nonfinite_or_below_minimum_clearance():
    assert Mission().approach_clearance==.5
    for value in [.49,float('nan'),float('inf'),11.]:
        with pytest.raises(ValueError):Mission(approach_clearance=value)


def test_engine_only_accepts_close_approach_during_fresh_active_tracking(tmp_path):
    from test_follow import instant_engine
    e,key,goals=instant_engine(tmp_path)
    e.runtime.gz.paused=False;e.runtime.gz.proximity=lambda *a:None
    with pytest.raises(ValueError,match='Start tracking'):e.start_approach()
    e.start_tracking(key);e.start_approach(.75)
    assert e.follow.close.clearance==.75 and e.follow.close.state=='APPROACHING'
    e.stop_approach();assert e.follow.close.state=='RETREATING'
    e.follow.close.state='IDLE';e.hold=True
    with pytest.raises(ValueError,match='Resume'):e.start_approach()


def test_finish_and_recall_disable_close_sensor_without_restarting_landing(tmp_path):
    from test_follow import instant_engine
    e,key,goals=instant_engine(tmp_path)
    calls=[];e.runtime.gz.paused=False;e.runtime.gz.proximity=lambda *a:calls.append(a)
    e.start_tracking(key);e.start_approach()
    e.follow.finish(e,'Operator recall','stopped')
    assert e.follow.close.state=='CANCELLED' and calls[-1]==(e.follow.drone_id,False)
    assert e.drones[e.follow.drone_id]['state']=='RETURNING'



def test_close_patch_stays_inside_the_selected_object_and_plane_projection_uses_depth_height():
    from backend.optical import interior_patch
    from backend.vision import ground_point
    assert interior_patch([100.,100.,200.,100.],.35,80.)==[165.,132.5,70.,35.]
    pose={'position':[0.,0.,4.],'quaternion':[0.,0.,0.,1.]}
    p=ground_point(320.,240.,pose,plane_height=2.)
    assert p==[0.,0.,2.]



def test_brief_camera_gap_holds_without_descending_then_stale_identity_backs_off():
    e,c,d,pos=controller();t=target();t['age']=.65
    c.tick(e,d,pos,12.,t)
    assert c.state=='APPROACHING' and e.goals[-1]==pos
    t['age']=1.
    c.tick(e,d,pos,12.,t)
    assert c.state=='RETREATING'



def test_close_entry_keeps_live_optical_identity_without_requiring_a_new_detector_seed(monkeypatch):
    from backend.vision import Vision
    from test_follow import confirmed
    import threading
    r,key=confirmed();v=Vision.__new__(Vision);frame=np.full((480,640,3),100,np.uint8)
    pose={'position':[36.,40.,12.],'quaternion':[0.,0.,0.,1.]}
    p={'time':.5,'image':frame}
    v.running=True;v.registry=r;v.observer_keys={};v.searching={'uav01'};v.landing=set()
    v.runtime=SimpleNamespace(gz=SimpleNamespace(lock=threading.RLock(),camera_packets={'uav01':p}),
                              fleet=SimpleNamespace(perception_pose=lambda *a:(pose,0.)))
    v.generation=0;v.anchors={};v.confidence=.4;v.optical_debug={};v.sites={}
    v.close_observations={'uav01':{'target_id':key,'time':.5,'surface_point':[36.,40.,2.]}}
    calls=[]
    tracker=SimpleNamespace(close_mode=False,plane_height=.8,method='CSRT',rivals=[])
    tracker.update=lambda *a:(calls.append('current-image') or ([300.,220.,40.,40.],.9))
    v.optical_states={'uav01':(key,tracker)};v.lock=threading.RLock();v.performance={'visual_frames':0}
    v.object_latest={};v.latest={};v.raw={};v.annotated={}
    monkeypatch.setattr('backend.vision.time.sleep',lambda *a:setattr(v,'running',False))
    v.run_optical()
    assert calls==['current-image'] and tracker.close_mode
    assert r.get(key,.5)['last_seen']==.5 and tracker.plane_height==2.


def test_higher_nearby_visible_surface_sets_the_descent_floor():
    e,c,d,pos=controller()
    c.alt_goal=0.
    c.sample=lambda *a:{'surface_point':[0.,0.,1.],'nearest_point':[0.,0.,2.],
                        'clearance_m':1.5,'alignment_m':0.,'time':1.,'tilt':0.}
    c.tick(e,d,pos,12.,target())
    assert e.goals[-1][2]==pytest.approx(3.25)

def depth_scene(stamp=1.,regions=None,color=(40,50,220)):
    regions=regions or [(65,45,30,30)]
    frame=np.full((480,640,3),100,np.uint8)
    image=np.full((120,160),3.92,np.float32)
    for x,y,w,h in regions:
        image[y:y+h,x:x+w]=1.92
        frame[y*4:(y+h)*4,x*4:(x+w)*4]=color
    return frame,{'time':stamp,'image':image},{'position':[0.,0.,4.],'quaternion':[0.,0.,0.,1.]}


def test_depth_rgb_continuity_follows_a_selected_image_component_without_actor_metadata():
    from backend.depth_visual import DepthVisual
    frame,p,pose=depth_scene()
    row={'age':0.,'ambiguous':False,'box':[250.,170.,150.,150.],'class':'car'}
    current=[p]
    tracker=DepthVisual.seed(row,frame,p,pose,1.,lambda stamp:current[0])
    assert tracker is not None
    frame,p,pose=depth_scene(1.1,[(66,45,30,30)])
    current[0]=p
    box,quality=tracker.update(frame,1.1,pose)
    assert box[0]==264. and quality>=.8
    assert tracker.last_position[2]==0. and tracker.plane_height==pytest.approx(2.,abs=1e-6)


def test_depth_rgb_continuity_does_not_identify_an_unselected_or_stale_region():
    from backend.depth_visual import DepthVisual
    frame,p,pose=depth_scene()
    row={'age':0.,'ambiguous':False,'box':[10.,10.,20.,20.],'class':'car'}
    assert DepthVisual.seed(row,frame,p,pose,1.,lambda stamp:p) is None
    row.update(box=[250.,170.,150.,150.],age=1.)
    assert DepthVisual.seed(row,frame,p,pose,1.,lambda stamp:p) is None


def test_depth_rgb_continuity_rejects_changed_appearance_and_ambiguous_lookalikes():
    from backend.depth_visual import DepthVisual
    frame,p,pose=depth_scene()
    row={'age':0.,'ambiguous':False,'box':[250.,170.,150.,150.],'class':'car'}
    current=[p]
    tracker=DepthVisual.seed(row,frame,p,pose,1.,lambda stamp:current[0])
    frame2,p2,pose2=depth_scene(1.1,color=(220,50,40))
    current[0]=p2
    assert tracker.update(frame2,1.1,pose2) is None
    frame2,p2,pose2=depth_scene(1.1,[(50,45,13,30),(97,45,13,30)])
    current[0]=p2
    assert tracker.update(frame2,1.1,pose2) is None and len(tracker.rivals)==2
    assert tracker.update(frame,2.,pose) is None


def test_depth_rgb_continuity_requires_a_time_paired_depth_image():
    from backend.depth_visual import surface_candidates
    frame,p,pose=depth_scene()
    assert surface_candidates(frame,p,pose,1.2)==[]



def test_tracking_enables_one_depth_sensor_before_close_in_and_finish_releases_it(tmp_path):
    from test_follow import instant_engine
    e,key,goals=instant_engine(tmp_path)
    e.vision.depth_targets={};calls=[];e.runtime.gz.proximity=lambda *a:calls.append(a)
    e.start_tracking(key)
    assert calls==[(e.follow.drone_id,True)]
    assert e.vision.depth_targets=={e.follow.drone_id:key}
    e.follow.finish(e,'Operator stop')
    assert calls[-1]==(e.follow.drone_id,False) and not e.vision.depth_targets



def test_selected_observer_processes_a_captured_pair_when_latest_rgb_is_ahead_of_depth():
    from backend.depth_visual import paired_rgb
    rgb=[{'time':1.},{'time':1.1},{'time':1.2}]
    depth=[{'time':1.},{'time':1.1}]
    assert paired_rgb(rgb[-1],rgb,depth,1.) is rgb[1]
    assert paired_rgb(rgb[-1],rgb,depth,1.1) is None
    assert paired_rgb({'time':2.},rgb,depth) is None



def test_primary_and_aerial_detector_positions_share_depth_geometry_without_duplicate_identity():
    from backend.depth_visual import surface_candidates,localize_detections
    from backend.tracking import Registry
    r=Registry()
    for i in range(8):
        stamp=1.+i*.1;frame,p,pose=depth_scene(stamp)
        det={'class':'car','confidence':.9,'box':[250.,170.,150.,150.],
             'position':[(-1. if i%2 else 1.)*2.,0.,0.]}
        corrected=localize_detections([det],surface_candidates(frame,p,pose,stamp))
        r.update('uav01',stamp,corrected,frame,'City',frame_key='aerial' if i%2 else 'main')
    rows=r.snapshot(1.7)
    assert len(rows)==1 and not rows[0]['ambiguous']
    assert math.hypot(*rows[0]['position'][:2])<.1


def test_depth_localization_does_not_assign_a_detection_spanning_two_distinct_components():
    from backend.depth_visual import localize_detections
    det={'box':[0.,0.,100.,100.],'position':[2.,3.,0.]}
    candidates=[{'box':[0.,0.,30.,100.],'position':[0.,0.,0.]},
                {'box':[70.,0.,30.,100.],'position':[1.,0.,0.]}]
    assert localize_detections([det],candidates)[0]['position']==[2.,3.,0.]



def test_resume_after_world_pause_waits_briefly_for_fresh_px4_instead_of_faulting(tmp_path):
    from test_follow import instant_engine
    import time
    e,key,goals=instant_engine(tmp_path);e.start_tracking(key)
    gz=e.runtime.gz;gz.paused=True;gz.received=time.monotonic();gz.carousel=lambda *a:None
    e.city=SimpleNamespace(tick=lambda:None);e.record_snapshot=lambda:None
    calls=[];e.tick_drone=lambda d,stop,dt:calls.append(d['id'])
    original_status=e.runtime.fleet.status
    e.tick();assert e.world_was_paused
    gz.paused=False
    e.runtime.fleet.status=lambda did:{**original_status(did),'fresh':False}
    e.tick();assert e.state=='TRACKING' and not calls
    e.runtime.fleet.status=original_status
    e.tick();assert calls and e.resume_deadline is None
