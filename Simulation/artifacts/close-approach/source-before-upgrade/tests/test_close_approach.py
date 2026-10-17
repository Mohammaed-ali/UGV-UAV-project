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
