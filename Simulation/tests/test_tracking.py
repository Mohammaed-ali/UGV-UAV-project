import numpy as np
import pytest
from backend.tracking import Registry
from backend.navigation import FlightPlanner
from backend.transport import matrix_quaternion,quaternion_matrix

def frame(color=(30,80,160)):
    image=np.full((480,640,3),color,dtype=np.uint8);return image
def detection(x,confidence=.85,box=None):
    return {'class':'person','confidence':confidence,'position':[x,5.,0.],'box':box or [100.,100.,30.,80.]}

def test_registry_requires_distinct_images_and_low_scores_cannot_create_tracks():
    r=Registry();image=frame()
    for _ in range(10):r.update('uav01',1.,[detection(1)],image,'Alpha')
    assert not r.snapshot(1)
    r.update('uav01',1.1,[detection(1)],image,'Alpha');r.update('uav01',1.2,[detection(1)],image,'Alpha')
    key=r.snapshot(1.2)[0]['id'];r.update('uav01',1.3,[detection(1.1,.2)],image,'Alpha')
    assert r.snapshot(1.3)[0]['id']==key and r.snapshot(1.3)[0]['last_seen']==1.3
    r.update('uav02',1.4,[detection(20,.2)],image,'Bravo')
    assert len(r.snapshot(1.4))==1

def test_world_projection_association_survives_large_camera_pixel_motion():
    r=Registry();image=frame()
    for i in range(5):r.update('uav01',i*.2,[detection(10+i*.12,box=[100+i*60,100,30,80])],image,'Alpha')
    rows=r.snapshot(.8);assert len(rows)==1 and rows[0]['speed']>0
    assert rows[0]['history'][-1]['position'][0]==pytest.approx(10.48)

def test_long_gap_creates_fresh_candidate_instead_of_silent_identity_switch():
    r=Registry();image=frame()
    for i in range(3):r.update('uav01',i*.2,[detection(2)],image,'Alpha')
    old=r.snapshot(.4)[0]['id'];r.select(old,.4)
    for i in range(3):r.update('uav01',30+i*.2,[detection(2)],image,'Charlie')
    rows=r.snapshot(30.4);assert len(rows)==2
    assert next(t for t in rows if t['id']==old)['last_seen']==.4
    assert next(t for t in rows if t['id']==old)['ambiguous']

def test_same_class_lookalikes_are_marked_uncertain_at_crossing():
    r=Registry();image=frame()
    for i in range(3):r.update('uav01',i*.1,[detection(0),detection(3)],image,'Alpha')
    assert len(r.snapshot(.2))==2
    r.update('uav01',.3,[detection(1.5)],image,'Alpha')
    assert any(t['ambiguous'] for t in r.snapshot(.3))
    assert len(r.tracks)==2

def test_metadata_and_thumbnail_storage_are_bounded():
    r=Registry();image=frame()
    for i in range(300):r.update('uav01',float(i),[detection(i*30)],image,'Alpha')
    assert len(r.tracks)<=250 and len(r.crops)<=128

def test_navigation_routes_around_building_and_above_low_roof():
    planner=FlightPlanner([dict(kind='building',x=0,y=0,sx=8,sy=8,sz=10)])
    current=[-12.,0.,8.];target=[12.,0.,8.]
    next_goal=planner.goal('uav01',current,target)
    assert next_goal!=target and planner.clear(current,next_goal,planner.boxes(8))
    assert planner.goal('uav01',[-12,0,15],[12,0,15])==[12,0,15]

def test_px4_camera_frame_rotation_conversion():
    rotation=np.array([[0.,-1,0],[1,0,0],[0,0,1]])
    assert quaternion_matrix(matrix_quaternion(rotation))==pytest.approx(rotation)


def test_auxiliary_image_channel_preserves_real_uav_and_provisional_class():
 r=Registry();frame=np.full((480,640,3),120,np.uint8)
 det={'class':'bus','confidence':.88,'box':[200,150,100,200],'position':[36.,40.,0.],'source':'Aerial vehicle detector','class_provisional':True}
 for stamp in (1.,1.2,1.4):
  r.update('uav01',stamp,[],frame,'City')
  r.update('uav01',stamp,[det],frame,'City',frame_key='uav01-aerial')
 row=r.snapshot(1.4)[0]
 assert row['drone']=='uav01' and row['class_provisional'] and row['source']=='Aerial vehicle detector'


def test_visual_tracker_accepts_detector_latency_but_bounds_later_gaps():
 from backend.optical import Optical
 class Correlation:
  def update(self,image):return True,(100,100,30,80)
 image=frame();tracker=Optical(image,[100,100,30,80],1.)
 tracker.correlation=Correlation()
 assert tracker.update(image,2.3) is not None
 assert tracker.update(image,2.5) is not None
 assert tracker.update(image,3.8) is None


def test_camera_seed_compensation_removes_aircraft_translation():
 from backend.optical import compensated_seed
 image=frame();old={'position':[0.,0.,12.],'quaternion':[0.,0.,0.,1.]}
 new={'position':[1.,0.,12.],'quaternion':[0.,0.,0.,1.]}
 warped,box=compensated_seed(image,[300.,220.,40.,40.],old,new)
 # Aircraft +X movement shifts a stationary ground object down in the image.
 assert warped.shape==image.shape and box[1]>250 and box[0]==pytest.approx(300,abs=.01)
 assert box[2:]==pytest.approx([40,40],abs=.01)


def test_visual_identity_survives_camera_yaw_without_blessing_a_new_appearance():
 from backend.optical import Optical,compensated_seed
 import math
 image=np.full((480,640,3),100,np.uint8)
 image[45:155,395:465]=[235,235,235]
 image[58:86,402:458]=[50,80,100];image[113:145,402:458]=[50,80,100]
 old={'position':[0.,0.,12.],'quaternion':[0.,0.,0.,1.]}
 yaw=math.radians(32);new={'position':[.3,0.,12.],'quaternion':[0.,0.,math.sin(yaw/2),math.cos(yaw/2)]}
 current,expected=compensated_seed(image,[395.,45.,70.,110.],old,new,.8)
 tracker=Optical(image,[395.,45.,70.,110.],1.,pose=old,plane_height=.8)
 signature=tracker.signature.copy();result=tracker.update(current,1.1,new)
 assert result is not None
 assert result[0]==pytest.approx(expected,abs=7)
 assert tracker.signature==pytest.approx(signature)
 # A missing foreground object cannot become an observation through reprojection.
 assert tracker.update(np.full_like(current,100),1.2,new) is None


def test_unconfirmed_lookalike_blocks_selected_visual_identity_until_confirmation():
 r=Registry();image=frame()
 for stamp in (1.,1.1,1.2):r.update('uav01',stamp,[detection(0)],image,'A')
 key=r.snapshot(1.2)[0]['id'];r.select(key,1.2)
 a=detection(.1);b=detection(1.,.3,box=[180.,100.,30.,80.])
 r.update('uav01',1.3,[a,b],image,'A')
 assert r.get(key,1.3)['ambiguous']
 assert r.get(key,1.3)['last_seen']==1.2
 assert r.refresh_visual(key,'uav01',1.4,a['box'],a['position'],image,.95,'A') is None
 # Separate, unique observations become a candidate, never clear the disputed ID.
 for stamp in (1.4,1.5,1.6):r.update('uav01',stamp,[a],image,'A')
 assert r.get(key,1.6)['ambiguous'] and r.get(key,1.6)['last_seen']==1.2
 candidate=next(t for t in r.snapshot(1.6) if t['id']!=key)
 r.confirm(candidate['id'],1.6)
 assert r.selected==candidate['id'] and not r.get(candidate['id'],1.6)['ambiguous']


def test_similar_clothing_region_challenges_pixel_lock_without_classifying_target():
 from backend.optical import Optical
 image=np.full((480,640,3),100,np.uint8);image[220:245,300:320]=[150,80,30]
 pose={'position':[0.,0.,12.],'quaternion':[0.,0.,0.,1.]}
 tracker=Optical(image,[295,210,35,45],1.,pose=pose,person_guard=True)
 assert not tracker.similar_regions(image,[295,210,35,45],pose)
 other=image.copy();other[225:250,360:380]=[150,80,30]
 assert tracker.similar_regions(other,[295,210,35,45],pose)
 other[225:250,360:380]=[30,80,150]
 assert not tracker.similar_regions(other,[295,210,35,45],pose)


def test_disputed_old_identity_cannot_challenge_confirmed_replacement():
 r=Registry();image=frame()
 for stamp in (1.,1.1,1.2):r.update('uav01',stamp,[detection(0)],image,'A')
 old=r.snapshot(1.2)[0]['id'];r.select(old,1.2)
 # Long absence freezes the old hypothesis and establishes a fresh candidate.
 for stamp in (31.,31.1,31.2):r.update('uav01',stamp,[detection(.1)],image,'A')
 new=next(t['id'] for t in r.snapshot(31.2) if t['id']!=old)
 r.confirm(new,31.2)
 for stamp in (31.3,31.4,31.5):r.update('uav01',stamp,[detection(.2)],image,'A')
 assert not r.get(new,31.5)['ambiguous']
 assert r.get(new,31.5)['last_seen']==31.5
 assert r.get(old,31.5)['last_seen']==1.2

def test_displaced_optical_box_is_lost_lock_not_second_person():
 from backend.optical import Optical
 image=np.full((480,640,3),100,np.uint8);image[220:245,300:320]=[150,80,30]
 pose={'position':[0.,0.,12.],'quaternion':[0.,0.,0.,1.]}
 tracker=Optical(image,[295,210,35,45],1.,pose=pose,person_guard=True)
 assert not tracker.similar_regions(image,[350,210,35,45],pose)
 assert not tracker.clothing_present


def test_person_identity_uses_clothing_not_shared_pavement_and_shadow():
 from backend.tracking import appearance,similarity
 image=np.full((480,640,3),[170,185,190],np.uint8)
 image[110:130,110:120]=[150,80,30]
 image[110:130,180:190]=[80,80,80]
 person=appearance(image,[100,100,30,80],True)
 shadow=appearance(image,[170,100,30,80],True)
 assert person is not None and shadow is None
 assert similarity(person,shadow)<.85
 image[110:130,180:190]=[150,80,30]
 assert similarity(person,appearance(image,[170,100,30,80],True))>.99


def test_tentative_duplicate_does_not_challenge_continuing_confirmed_identity():
 r=Registry();image=frame()
 for stamp in (1.,1.1,1.2):r.update('uav01',stamp,[detection(0)],image,'A')
 key=r.snapshot(1.2)[0]['id'];r.select(key,1.2)
 # Seed one uncertain observation outside the immediate association gate.
 r.update('uav01',1.3,[detection(4)],image,'A')
 r.update('uav01',1.4,[detection(1.7)],image,'A')
 assert not r.get(key,1.4)['ambiguous']
 assert r.get(key,1.4)['last_seen']==1.4
