"""Generate the Gazebo world from the same SI scene manifest used by the browser."""
from pathlib import Path
import math
import xml.etree.ElementTree as E
from .config import Mission, scene, slot

def el(parent,tag,text=None,**attrs):
    e=E.SubElement(parent,tag,{k:str(v) for k,v in attrs.items()})
    if text is not None: e.text=str(text)
    return e

def pose(p,values): return el(p,'pose',' '.join(str(v) for v in values))

def plugin(p,filename,name,values=None):
    a=el(p,'plugin',filename=filename,name='gz::sim::systems::'+name)
    for k,v in (values or {}).items():
        for item in v if isinstance(v,list) else [v]: el(a,k,item)
    return a

def inertial(link,mass,size):
    a,b,c=size; i=el(link,'inertial');el(i,'mass',mass);j=el(i,'inertia')
    for k,v in {'ixx':mass*(b*b+c*c)/12,'iyy':mass*(a*a+c*c)/12,'izz':mass*(a*a+b*b)/12,'ixy':0,'ixz':0,'iyz':0}.items():el(j,k,v)

def geometry(p,kind,size):
    g=el(p,'geometry');s=el(g,kind)
    if kind=='box': el(s,'size',' '.join(map(str,size)))
    elif kind=='cylinder':el(s,'radius',size[0]);el(s,'length',size[1])
    elif kind=='sphere':el(s,'radius',size[0])
    return g

def shape(link,name,kind,size,xyz=(0,0,0),color='.2 .25 .25 1',collision=True,rpy=(0,0,0)):
    v=el(link,'visual',name=name+'_visual');pose(v,(*xyz,*rpy));geometry(v,kind,size)
    mat=el(v,'material');el(mat,'ambient',color);el(mat,'diffuse',color)
    if collision:
        c=el(link,'collision',name=name+'_collision');pose(c,(*xyz,*rpy));geometry(c,kind,size)
        surface=el(c,'surface');o=el(el(surface,'friction'),'ode');el(o,'mu',.7);el(o,'mu2',.7)
    return v

def carrier(world,m):
    a=el(world,'model',name='carrier');pose(a,(m.start.x,m.start.y,.66,0,0,0))
    base=el(a,'link',name='base_link');inertial(base,180,(4.6,1.65,.5));shape(base,'chassis','box',(4.6,1.65,.5),color='.16 .24 .23 1')
    shape(base,'deck','box',(4.8,1.85,.12),(0,0,.31),'.25 .31 .29 1')
    for x in (-2.1,2.1):
        for y in (-.48,.48):shape(base,f'post_{x}_{y}','box',(.06,.06,1.45),(x,y,1.02),'.24 .28 .26 1')
    wheels=[]
    for x in ([-1.65,1.65] if m.wheels==4 else [-1.65,0,1.65]):
        for side,y in [('left',.94),('right',-.94)]:
            n=f'wheel_{side}_{str(x).replace(".","_").replace("-","m")}';w=el(a,'link',name=n);pose(w,(x,y,-.32,math.pi/2,0,0));inertial(w,6,(.68,.68,.24));shape(w,n,'cylinder',(.34,.24),color='.065 .075 .07 1')
            j=el(a,'joint',name=n+'_joint',type='revolute');el(j,'parent','base_link');el(j,'child',n);axis=el(j,'axis');el(axis,'xyz','0 0 -1');l=el(axis,'limit');el(l,'effort',240);el(l,'velocity',12)
            wheels.append((side,n+'_joint'))
    plugin(a,'gz-sim-diff-drive-system','DiffDrive',{'left_joint':[n for s,n in wheels if s=='left'],'right_joint':[n for s,n in wheels if s=='right'],'wheel_separation':1.88,'wheel_radius':.34,'topic':'/fieldlab/carrier/cmd_vel','odom_topic':'/fieldlab/carrier/odom','odom_publish_frequency':30,'max_linear_velocity':3,'max_angular_velocity':.7,'max_linear_acceleration':.5,'max_angular_acceleration':.5})
    for idx in range(8):
        s=slot(idx);did=s['id'];name='tray_'+did
        t=el(a,'link',name=name);pose(t,(s['x'],0,s['z'],0,0,0));inertial(t,3,(.88,.88,.055))
        shape(t,'pad','box',(.88,.88,.055),color='.77 .8 .75 1')
        tag=shape(t,'tag','box',(.38,.38,.001),(0,0,.029),'1 1 1 1',collision=False)
        metal=el(el(tag.find('material'),'pbr'),'metal');el(metal,'albedo_map',f'model://tags/tag_{idx+1}.png');el(metal,'metalness',0);el(metal,'roughness',1)
        sensor=el(t,'sensor',name='contact_'+did,type='contact');el(sensor,'always_on','true');el(sensor,'update_rate',30);el(sensor,'topic',f'/fieldlab/trays/{did}/contact')
        contact=el(sensor,'contact');el(contact,'collision','pad_collision');el(contact,'topic',f'/fieldlab/trays/{did}/contact')
        j=el(a,'joint',name=name+'_joint',type='prismatic');el(j,'parent','base_link');el(j,'child',name)
        axis=el(j,'axis');el(axis,'xyz',f'0 {s["side"]} 0');limit=el(axis,'limit');el(limit,'lower',0);el(limit,'upper',1.65);el(limit,'effort',500);el(limit,'velocity',.3);el(el(axis,'dynamics'),'damping',25)
        plugin(a,'gz-sim-joint-position-controller-system','JointPositionController',{'joint_name':name+'_joint','topic':f'/fieldlab/trays/{did}/position','p_gain':250,'i_gain':0,'d_gain':35,'cmd_max':200,'cmd_min':-200})
        plugin(a,'gz-sim-detachable-joint-system','DetachableJoint',{'parent_link':name,'child_model':did,'child_link':'base_link','attach_topic':f'/fieldlab/trays/{did}/attach','detach_topic':f'/fieldlab/trays/{did}/detach','output_topic':f'/fieldlab/trays/{did}/latch','suppress_child_warning':'true'})
    plugin(a,'gz-sim-joint-state-publisher-system','JointStatePublisher',{'topic':'/fieldlab/carrier/joints'})
    plugin(a,'gz-sim-pose-publisher-system','PosePublisher',{'publish_link_pose':'true','publish_model_pose':'true','use_pose_vector_msg':'true','update_frequency':30,'topic':'/fieldlab/carrier/poses'})

def aircraft(world,m,idx):
    import os,copy
    s=slot(idx);did=s['id'];a=el(world,'model',name=did);pose(a,(m.start.x+s['x'],m.start.y,.66+s['z']+.26,0,0,0))
    models=Path(os.environ['FIELDLAB_DEPS'])/'PX4-Autopilot/Tools/simulation/gz/models'
    base=E.parse(models/'x500_base/model.sdf').getroot().find('model')
    for child in base:
        if child.tag in ('link','joint','self_collide'):a.append(copy.deepcopy(child))
    if m.wind:
        el(a,'enable_wind','true')
        el(a.find("link[@name='base_link']"),'enable_wind','true')
    motors=E.parse(models/'x500/model.sdf').getroot().find('model')
    for p in motors.findall('plugin'):a.append(copy.deepcopy(p))
    link=el(a,'link',name='camera_link');pose(link,(0,0,-.08,0,math.pi/2,0));inertial(link,.01,(.02,.02,.02))
    sensor=el(link,'sensor',name='down_camera',type='camera');el(sensor,'always_on','false');el(sensor,'update_rate',10);el(sensor,'topic',f'/fieldlab/{did}/camera')
    cam=el(sensor,'camera');el(cam,'horizontal_fov',1.22);im=el(cam,'image');el(im,'width',640);el(im,'height',480);el(im,'format','R8G8B8');cl=el(cam,'clip');el(cl,'near',.03);el(cl,'far',100)
    j=el(a,'joint',name='camera_joint',type='fixed');el(j,'parent','base_link');el(j,'child','camera_link')

def make_world(root:Path,m:Mission)->Path:
    sdf=E.Element('sdf',version='1.9');w=el(sdf,'world',name='fieldlab')
    physics=el(w,'physics',name='fixed_step',type='ignored');el(physics,'max_step_size',.004);el(physics,'real_time_factor',1)
    for file,name in [('physics','Physics'),('user-commands','UserCommands'),('scene-broadcaster','SceneBroadcaster'),('imu','Imu'),('magnetometer','Magnetometer'),('navsat','NavSat'),('air-pressure','AirPressure'),('contact','Contact')]:plugin(w,f'gz-sim-{file}-system',name)
    plugin(w,'gz-sim-sensors-system','Sensors',{'render_engine':'ogre2'})
    el(w,'gravity','0 0 -9.80665');el(w,'magnetic_field','0.0000055645 0.0000228758 -0.0000423884')
    if m.wind:
        el(el(w,'wind'),'linear_velocity',f'{m.wind} 0 0')
        plugin(w,'gz-sim-wind-effects-system','WindEffects',{'force_approximation_scaling_factor':.15})
    sc=el(w,'scene');el(sc,'ambient','.65 .65 .65 1');el(sc,'background','.75 .82 .8 1');el(sc,'shadows','true')
    light=el(w,'light',name='sun',type='directional');pose(light,(0,0,50,0,0,0));el(light,'diffuse','.95 .92 .85 1');el(light,'specular','.2 .2 .2 1');el(light,'direction','-.4 .3 -1');el(light,'cast_shadows','true')
    coords=el(w,'spherical_coordinates');el(coords,'surface_model','EARTH_WGS84');el(coords,'world_frame_orientation','ENU');el(coords,'latitude_deg',47.397742);el(coords,'longitude_deg',8.545594);el(coords,'elevation',488);el(coords,'heading_deg',0)
    floor=el(w,'model',name='ground');el(floor,'static','true');fl=el(floor,'link',name='ground_link');shape(fl,'ground','box',(160,160,.2),(0,0,-.1),'.55 .6 .46 1')
    for name,x,y,sx,sy in [('road',0,-22,140,8),('crossroad',30,10,8,80)]:
        a=el(w,'model',name=name);el(a,'static','true');pose(a,(x,y,0,0,0,0));l=el(a,'link',name='visual');shape(l,name,'box',(sx,sy,.008),(0,0,.006),'.23 .27 .26 1',collision=False)
    for obj in scene(m)['objects']:
        if obj['kind']=='building':
            a=el(w,'model',name=obj['id']);el(a,'static','true');pose(a,(obj['x'],obj['y'],0,0,0,0));l=el(a,'link',name='building');shape(l,'block','box',(obj['sx'],obj['sy'],obj['sz']),(0,0,obj['sz']/2),'.66 .65 .57 1')
        else:
            model=('human_mesh_'+str(obj['variant'])) if obj['kind']=='person' else obj['kind']+'_mesh_0'
            inc=el(w,'include');el(inc,'uri','model://'+model);el(inc,'name',obj['id']);pose(inc,(obj['x'],obj['y'],0,0,0,obj['yaw']))
    for idx in range(8):aircraft(w,m,idx)
    carrier(w,m)
    path=root/'.runtime/world.sdf';path.parent.mkdir(parents=True,exist_ok=True);E.indent(sdf);path.write_bytes(E.tostring(sdf,encoding='utf-8',xml_declaration=True));return path
