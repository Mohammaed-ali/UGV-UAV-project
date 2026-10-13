import math
import pytest
from backend.city import layout,project,lengths,point_at,service_route,DIMENSIONS
from backend.config import Mission,Stop

def test_city_route_snaps_and_uses_service_junction():
    m=Mission(living_city=True,stops=[Stop(id='a',label='A',x=29.5,y=34.5)])
    assert m.stops[0].x==30
    assert service_route(m.start,m.stops[0])==[(-28,-22),(30,-22),(30,34.5)]
    with pytest.raises(ValueError):Mission(living_city=True,stops=[Stop(id='a',label='A',x=0,y=0)])

@pytest.mark.parametrize('seed',[1,42,101])
def test_city_networks_preserve_full_carrier_and_actor_clearance(seed):
    m=Mission(living_city=True,seed=seed);city=layout(m)
    assert city==layout(m)
    actors=[o for o in city['objects'] if o['kind']!='building']
    assert len(actors)==28
    for path in city['networks']:
        if path['kind']=='service':continue
        for s in range(0,int(lengths(path['points'])[-1]),2):
            p,yaw=point_at(path['points'],s)
            # Conservative full UGV turning circle, and deployed carousel bay envelope.
            body_half=1.5 if path['kind']=='vehicle' else .4
            assert min(abs(p[1]+22),abs(p[0]-30))>3.34+body_half
            assert all(math.dist(p,(stop.x,stop.y))>4.7+body_half for stop in m.stops)

def test_path_projection_and_sampling_close_loop():
    points=layout(Mission(living_city=True))['networks'][0]['points']
    for s in [0.,20.,60.,150.]:
        p,_=point_at(points,s);error,found,_=project(points,p)
        assert error<1e-8 and found==pytest.approx(s)


def test_initial_physical_occupancy_is_separated_across_crossing_route_ids():
    for count in (18,40):
        actors=[o for o in layout(Mission(living_city=True,population=count,traffic=20))['objects'] if o['kind']!='building']
        for i,a in enumerate(actors):
            for b in actors[i+1:]:
                ra=1.1 if a['kind']=='person' else math.hypot(*DIMENSIONS[a['kind']][:2])/2+1.
                rb=1.1 if b['kind']=='person' else math.hypot(*DIMENSIONS[b['kind']][:2])/2+1.
                assert math.dist([a['x'],a['y']],[b['x'],b['y']])>=ra+rb


def test_loaded_carrier_brakes_before_bay_and_damps_turn_momentum():
 from backend.driving import city_drive
 cruise,_=city_drive(10,0,1.5,0,1.5)
 approach,_=city_drive(1,0,1.5,0,1.5)
 creep,_=city_drive(.46,0,0,0,1.5)
 linear,angular=city_drive(3,.1,0,.5,1.5)
 assert cruise==1.5 and 0<approach<.3 and creep>0
 assert angular<0  # Brake the measured rotation before a small heading error.
 assert city_drive(4,1.,1.5,0,1.5)[0]==0


def test_contact_topic_is_configured_for_native_contact_system():
 from backend.world import city_contact
 import xml.etree.ElementTree as E
 link=E.Element('link');city_contact(link,'occupancy')
 assert link.find('sensor/contact/topic').text=='/fieldlab/city/contacts'
 assert link.find('sensor/contact/collision').text=='occupancy'


def test_sweep_catches_rotation_between_valid_endpoint_footprints():
 from scripts.evaluate_fleet_evidence import sweep,corners
 body=(4.,1.);first={'position':[0,0,0],'yaw':0};last={'position':[0,0,0],'yaw':math.pi}
 assert max(abs(p[1]) for pose in (first,last) for p in corners(pose,body))<.51
 assert max(abs(p[1]) for pose in sweep(first,last,body) for p in corners(pose,body))>2.


def test_public_survey_checks_nearby_path_and_both_sides_inside_radius():
 from backend.city import survey_goal
 m=Mission(living_city=True,flight_speed=3.,stops=[Stop(id='a',label='A',x=30,y=34.5,search_radius=12)])
 public=[{'kind':'sidewalk','points':[[36,0],[36,90],[90,90],[90,0],[36,0]]}]
 stop=m.stops[0];goals=[survey_goal(m,stop,t,0,public) for t in range(48)]
 assert goals[0]==[36.,34.5]
 assert min(p[1] for p in goals)<stop.y-8 and max(p[1] for p in goals)>stop.y+8
 assert all(math.dist(p,[stop.x,stop.y])<=stop.search_radius+1e-8 for p in goals)
 assert survey_goal(m,stop,0,2,public)!=goals[0]


def test_compact_city_keeps_full_size_blocks_and_three_districts():
 from backend.city import DISTRICTS
 assert len(DISTRICTS)==3
 assert all(x1-x0==62. and y1-y0==66. for x0,x1,y0,y1 in DISTRICTS)
 assert min(x0 for x0,x1,y0,y1 in DISTRICTS)==-47.
 assert max(y1 for x0,x1,y0,y1 in DISTRICTS)==59.
 city=layout(Mission(living_city=True))
 assert len([o for o in city['objects'] if o['kind']=='building'])==12

@pytest.mark.parametrize('scenario',['custom','walking-person','moving-vehicle','similar-people','stopping-vehicle','building-occlusion','leaving-area'])
def test_compact_city_scenario_paths_reference_existing_districts(scenario):
 city=layout(Mission(living_city=True,city_scenario=scenario,traffic=0 if scenario=='building-occlusion' else 10))
 path_ids={p['id'] for p in city['networks']}
 assert all(o['path_id'] in path_ids and o['district']<3 for o in city['objects'] if o['kind']!='building')
