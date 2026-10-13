"""Generate the Gazebo world from the same SI scene manifest used by the browser."""
from pathlib import Path
import math
import xml.etree.ElementTree as E
from .config import Mission, scene, slot
from .rack import BASE_Z,UPPER_Z,LOWER_Z,CENTER_Z,HALF_HEIGHT,RADIUS,PAD_Z,CHASSIS_SIZE,DECK_SIZE,WHEEL_X,WHEEL_Y

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
    a=el(world,'model',name='carrier');pose(a,(m.start.x,m.start.y,BASE_Z,0,0,0))
    base=el(a,'link',name='base_link');inertial(base,240,(CHASSIS_SIZE,CHASSIS_SIZE,.5));shape(base,'chassis','box',(CHASSIS_SIZE,CHASSIS_SIZE,.5),color='.16 .24 .23 1')
    shape(base,'deck','box',(DECK_SIZE,DECK_SIZE,.12),(0,0,.31),'.25 .31 .29 1')
    # The two level-preserving gondolas follow these vertical guide loops.
    # Coupled orthogonal actuators drive physical prismatic joints, never poses.
    for x in (-1.48,1.48):
        for y in (-1.35,1.35):shape(base,f'post_{x}_{y}','box',(.075,.075,1.94),(x,y,1.29),'.24 .28 .26 1')
        for k in range(48):
            a0=k*2*math.pi/48;a1=(k+1)*2*math.pi/48
            y0,z0=RADIUS*math.sin(a0),CENTER_Z+HALF_HEIGHT*math.cos(a0)
            y1,z1=RADIUS*math.sin(a1),CENTER_Z+HALF_HEIGHT*math.cos(a1)
            shape(base,f'guide_{x}_{k}','box',(.055,math.hypot(y1-y0,z1-z0)+.018,.055),(x,(y0+y1)/2,(z0+z1)/2),'.34 .4 .36 1',collision=False,rpy=(math.atan2(z1-z0,y1-y0),0,0))
    wheels=[]
    for x in ([-WHEEL_X,WHEEL_X] if m.wheels==4 else [-WHEEL_X,0,WHEEL_X]):
        for side,y in [('left',WHEEL_Y),('right',-WHEEL_Y)]:
            n=f'wheel_{side}_{str(x).replace(".","_").replace("-","m")}';w=el(a,'link',name=n);pose(w,(x,y,-.36,math.pi/2,0,0));inertial(w,7,(.76,.76,.3));shape(w,n,'cylinder',(.38,.3),color='.065 .075 .07 1')
            j=el(a,'joint',name=n+'_joint',type='revolute');el(j,'parent','base_link');el(j,'child',n);axis=el(j,'axis');el(axis,'xyz','0 0 -1');l=el(axis,'limit');el(l,'effort',240);el(l,'velocity',12)
            wheels.append((side,n+'_joint'))
    plugin(a,'gz-sim-diff-drive-system','DiffDrive',{'left_joint':[n for s,n in wheels if s=='left'],'right_joint':[n for s,n in wheels if s=='right'],'wheel_separation':3.32,'wheel_radius':.38,'topic':'/fieldlab/carrier/cmd_vel','odom_topic':'/fieldlab/carrier/odom','odom_publish_frequency':30,'max_linear_velocity':3,'max_angular_velocity':.5,'max_linear_acceleration':.5,'max_angular_acceleration':.3})
    for level,height in [('upper',UPPER_Z),('lower',LOWER_Z)]:
        guide=el(a,'link',name=f'carousel_{level}_guide');inertial(guide,1,(.1,.1,.1))
        shelf=el(a,'link',name=f'carousel_{level}_shelf');pose(shelf,(0,0,height,0,0,0));inertial(shelf,12,(2.65,2.65,.08))
        shape(shelf,'shelf','box',(2.65,2.65,.08),color='.38 .49 .44 1')
        for axis,parent,child,xyz,bounds in [
            ('y','base_link',f'carousel_{level}_guide','0 1 0',(-RADIUS-.1,RADIUS+.1)),
            ('z',f'carousel_{level}_guide',f'carousel_{level}_shelf','0 0 1',(-1.57,.1) if level=='upper' else (-.1,1.57))]:
            name=f'carousel_{level}_{axis}_joint';j=el(a,'joint',name=name,type='prismatic');el(j,'parent',parent);el(j,'child',child)
            ax=el(j,'axis');el(ax,'xyz',xyz);limits=el(ax,'limit');el(limits,'lower',bounds[0]);el(limits,'upper',bounds[1]);el(limits,'effort',4000);el(limits,'velocity',.5)
            el(el(ax,'dynamics'),'damping',40)
            plugin(a,'gz-sim-joint-position-controller-system','JointPositionController',{'joint_name':name,'topic':f'/fieldlab/carousel/{level}/{axis}','p_gain':12000,'i_gain':600,'d_gain':650,'i_max':800,'i_min':-800,'cmd_max':4000,'cmd_min':-4000})
    for idx in range(8):
        s=slot(idx);did=s['id'];name='tray_'+did
        t=el(a,'link',name=name);pose(t,(s['x'],s['y'],s['z'],0,0,0));inertial(t,.5,(1.04,1.04,.055))
        shape(t,'pad','box',(1.04,1.04,.055),color='.77 .8 .75 1')
        tag=shape(t,'tag','box',(.38,.38,.001),(0,0,.029),'1 1 1 1',collision=False)
        metal=el(el(tag.find('material'),'pbr'),'metal');el(metal,'albedo_map',f'model://tags/tag_{idx+1}.png');el(metal,'metalness',0);el(metal,'roughness',1)
        sensor=el(t,'sensor',name='contact_'+did,type='contact');el(sensor,'always_on','true');el(sensor,'update_rate',30);el(sensor,'topic',f'/fieldlab/trays/{did}/contact')
        contact=el(sensor,'contact');el(contact,'collision','pad_collision');el(contact,'topic',f'/fieldlab/trays/{did}/contact')
        j=el(a,'joint',name=name+'_fixed',type='fixed');el(j,'parent',f'carousel_{s["level"]}_shelf');el(j,'child',name)
        plugin(a,'gz-sim-detachable-joint-system','DetachableJoint',{'parent_link':name,'child_model':did,'child_link':'base_link','attach_topic':f'/fieldlab/trays/{did}/attach','detach_topic':f'/fieldlab/trays/{did}/detach','output_topic':f'/fieldlab/trays/{did}/latch','suppress_child_warning':'true'})
    plugin(a,'gz-sim-joint-state-publisher-system','JointStatePublisher',{'topic':'/fieldlab/carrier/joints'})
    plugin(a,'gz-sim-pose-publisher-system','PosePublisher',{'publish_link_pose':'true','publish_model_pose':'true','use_pose_vector_msg':'true','update_frequency':30,'topic':'/fieldlab/carrier/poses'})

def aircraft(world,m,idx):
    import os,copy
    s=slot(idx);did=s['id'];a=el(world,'model',name=did);pose(a,(m.start.x+s['x'],m.start.y+s['y'],BASE_Z+s['z']+.26,0,0,0))
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
    layout=scene(m)
    floor=el(w,'model',name='ground');el(floor,'static','true');fl=el(floor,'link',name='ground_link');shape(fl,'ground','box',(layout['size']+10,layout['size']+10,.2),(0,0,-.1),'.59 .63 .52 1')
    for road in layout['roads']:
        a=el(w,'model',name=road['id']);el(a,'static','true');pose(a,(road['x'],road['y'],0,0,0,0));l=el(a,'link',name='visual')
        shape(l,'sidewalk','box',(road['sx']+3.5,road['sy']+3.5,.008),(0,0,.004),'.65 .66 .61 1',collision=False)
        shape(l,'asphalt','box',(road['sx'],road['sy'],.008),(0,0,.009),'.23 .27 .26 1',collision=False)
        horizontal=road['sx']>road['sy']
        for k in range(-22,23):shape(l,f'lane_{k}','box',(2.4,.12,.002) if horizontal else (.12,2.4,.002),(k*5 if horizontal else 0,0 if horizontal else k*5,.015),'.8 .82 .7 1',collision=False)
    for obj in layout['objects']:
        if obj['kind']=='building':
            a=el(w,'model',name=obj['id']);el(a,'static','true');pose(a,(obj['x'],obj['y'],0,0,0,0));l=el(a,'link',name='building');shape(l,'block','box',(obj['sx'],obj['sy'],obj['sz']),(0,0,obj['sz']/2),['.68 .68 .62 1','.6 .65 .62 1','.66 .61 .54 1','.7 .71 .66 1'][obj.get('variant',0)])
            shape(l,'roof','box',(obj['sx']+.3,obj['sy']+.3,.22),(0,0,obj['sz']+.1),'.4 .46 .43 1',collision=False)
            for row in range(max(1,int(obj['sz']//3))):
                for col in range(int(obj['sx']//3)):
                    shape(l,f'window_{row}_{col}','box',(1.3,.025,1.25),(-obj['sx']/2+1.6+col*3,-obj['sy']/2-.025,2+row*3),'.24 .38 .4 1',collision=False)
        else:
            model=('human_mesh_'+str(obj['variant'])) if obj['kind']=='person' else obj['kind']+'_mesh_0'
            inc=el(w,'include');el(inc,'uri','model://'+model);el(inc,'name',obj['id']);pose(inc,(obj['x'],obj['y'],0,0,0,obj['yaw']))
    for idx in range(8):aircraft(w,m,idx)
    carrier(w,m)
    path=root/'.runtime/world.sdf';path.parent.mkdir(parents=True,exist_ok=True);E.indent(sdf);path.write_bytes(E.tostring(sdf,encoding='utf-8',xml_declaration=True));return path
