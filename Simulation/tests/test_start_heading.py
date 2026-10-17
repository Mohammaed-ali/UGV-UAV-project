import math
import xml.etree.ElementTree as E
from types import SimpleNamespace

import pytest
from backend.config import Mission, Stop, slot, spawn_pose
from backend.mission import Engine
from backend.world import aircraft, carrier


@pytest.mark.parametrize('start,goal,yaw',[
    ((-28,-22),(-44.5,-22),math.pi),
    ((-28,-22),(16,-22),0.),
    ((30,0),(30,20),math.pi/2),
    ((30,0),(30,-40),-math.pi/2),
    # Face the service-lane junction, rather than pointing diagonally at the bay.
    ((-28,-22),(30,34.5),0.),
    ((30,0),(-44.5,-22),-math.pi/2),
])
def test_start_faces_first_protected_route_segment(start,goal,yaw):
    m=Mission(living_city=True,start=dict(zip(('x','y'),start)),
              stops=[Stop(id='a',label='A',x=goal[0],y=goal[1])])
    assert spawn_pose(m)['yaw']==pytest.approx(yaw)


def test_field_start_faces_diagonal_first_leg():
    m=Mission(terrain='field',population=0,traffic=0,start={'x':0,'y':0},
              stops=[Stop(id='a',label='A',x=-10,y=10)])
    assert spawn_pose(m)['yaw']==pytest.approx(3*math.pi/4)


@pytest.mark.parametrize('wheels',[4,6])
@pytest.mark.parametrize('goal',[(30,20),(-44.5,-22)])
def test_physical_aircraft_and_preview_share_rotated_rack(tmp_path,monkeypatch,wheels,goal):
    # Minimal pinned-model stand-ins keep this geometry regression self-contained.
    models=tmp_path/'PX4-Autopilot/Tools/simulation/gz/models'
    for name,text in [('x500_base','<link name="base_link"/>'),('x500','<plugin name="motors"/>')]:
        folder=models/name;folder.mkdir(parents=True)
        (folder/'model.sdf').write_text(f'<sdf><model name="{name}">{text}</model></sdf>')
    monkeypatch.setenv('FIELDLAB_DEPS',str(tmp_path))
    m=Mission(living_city=True,wheels=wheels,start={'x':30,'y':-22},
              stops=[Stop(id='a',label='A',x=goal[0],y=goal[1])])
    world=E.Element('world');carrier(world,m)
    for i in range(8):aircraft(world,m,i)
    c=[float(v) for v in world.find("model[@name='carrier']/pose").text.split()]
    yaw=c[-1];assert abs(yaw)>.1
    vision=SimpleNamespace(latest={},detector_ready=True,tag_ready=True,error=None)
    runtime=SimpleNamespace(gz=None,fleet=None,health=lambda:{'state':'offline'})
    engine=Engine(tmp_path,runtime,vision);engine.config=m;preview=engine.snapshot()
    assert preview['carrier']['yaw']==pytest.approx(yaw)
    assert preview['carrier']['quaternion']==pytest.approx([0,0,math.sin(yaw/2),math.cos(yaw/2)])
    for i in range(8):
        s=slot(i);p=[float(v) for v in world.find(f"model[@name='{s['id']}']/pose").text.split()]
        # Inverse transform must recover the original bay on the physical rack.
        dx,dy=p[0]-c[0],p[1]-c[1]
        assert [math.cos(yaw)*dx+math.sin(yaw)*dy,-math.sin(yaw)*dx+math.cos(yaw)*dy]==pytest.approx([s['x'],s['y']])
        assert p[-1]==pytest.approx(yaw)
        assert preview['drones'][i]['position']==pytest.approx(p[:3])
        assert preview['drones'][i]['quaternion']==pytest.approx(preview['carrier']['quaternion'])
