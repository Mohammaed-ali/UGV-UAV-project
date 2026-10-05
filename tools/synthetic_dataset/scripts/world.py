"""Create a static preloaded world; active poses and light are changed via transport."""
from copy import deepcopy
import xml.etree.ElementTree as ET
from common import TOOL, atomic_write
from build_assets import model_sdf, part


def camera_sensors(link,cam,spike=False,anti_aliasing=1):
    options=[('rgb','camera',''),('visible','boundingbox_camera','visible_2d')]
    if spike: options += [('full','boundingbox_camera','full_2d'),('three','boundingbox_camera','3d'),('semantic','segmentation','semantic'),('instance','segmentation','instance')]
    for name,kind,option in options:
        sensor=ET.SubElement(link,'sensor',name=name,type=kind)
        ET.SubElement(sensor,'pose').text='0 0 0 0 0 0';ET.SubElement(sensor,'topic').text='/dataset/'+name
        ET.SubElement(sensor,'gz_frame_id').text='dataset_camera'
        camera=ET.SubElement(sensor,'camera')
        if option: ET.SubElement(camera,'segmentation_type' if kind=='segmentation' else 'box_type').text=option
        ET.SubElement(camera,'horizontal_fov').text=str(cam['horizontal_fov'])
        image=ET.SubElement(camera,'image')
        for key in ('width','height'): ET.SubElement(image,key).text=str(cam[key])
        ET.SubElement(image,'anti_aliasing').text=str(anti_aliasing if kind=='camera' else 1)
        clip=ET.SubElement(camera,'clip')
        for key in ('near','far'): ET.SubElement(clip,key).text=str(cam[key])
        ET.SubElement(camera,'camera_info_topic').text='/dataset/'+name+'/camera_info'
        ET.SubElement(sensor,'always_on').text='true';ET.SubElement(sensor,'update_rate').text=str(cam['update_rate_hz'])
    return link


def clutter_assets():
    assets=[]
    for i in range(6):
        parts=[part('crate',[1.4,1.4,1.3],[0,0,.65],[.43,.31,.19])] if i%3==0 else (
              [part('trunk',[.18,3.2],[0,0,1.6],[.3,.19,.1],'cylinder'),part('crown',[1.2,2.4],[0,0,3.9],[.15,.32,.1],'cylinder')] if i%3==1 else
              [part('barrier',[3,.4,1.3],[0,0,.65],[.55,.55,.5])])
        assets.append({'asset_id':f'clutter_{i}','parts':parts})
    for name,length in [('canopy_mild',2),('canopy_moderate',4)]:
        assets.append({'asset_id':name,'parts':[part('roof',[length,3,.2],[0,0,5.1],[.45,.43,.37])]+[
            part(f'leg_{x}_{y}',[.15,.15,5],[x,y,2.5],[.45,.43,.37]) for x in (-length/2,length/2) for y in (-1.5,1.5)]})
    assets.append({'asset_id':'shadow_wall','parts':[part('wall',[6,.25,8],[0,0,4],[.6,.6,.55])]})
    return assets


def pinned_model(asset, name=None):
    """Load the checksummed model and resolve only its known local resource URIs."""
    if not asset.get('dependencies'):
        a=deepcopy(asset);a['asset_id']=name or asset['asset_id'];return model_sdf(a)
    path=TOOL/asset['local_path'];model=deepcopy(ET.parse(path).find('model'))
    model.set('name',name or asset['asset_id'])
    for uri in model.findall('.//uri'):
        p=(path.parent/uri.text).resolve()
        if not p.is_relative_to(TOOL.resolve()):raise ValueError('Asset resource escapes tool directory')
        uri.text=str(p)
    return model


def write_world(cfg,path):
    sdf=ET.Element('sdf',version='1.9');world=ET.SubElement(sdf,'world',name=cfg['world']['name'])
    for system in ('Physics','UserCommands','SceneBroadcaster','Sensors'):
        plugin=ET.SubElement(world,'plugin',filename='gz-sim-'+{'SceneBroadcaster':'scene-broadcaster','UserCommands':'user-commands'}.get(system,system.lower())+'-system',name='gz::sim::systems::'+system)
        if system=='Sensors': ET.SubElement(plugin,'render_engine').text=cfg['world']['rendering_engine']
    physics=ET.SubElement(world,'physics',name='dataset',type='ignored')
    ET.SubElement(physics,'max_step_size').text=str(cfg['world']['step_s']);ET.SubElement(physics,'real_time_factor').text=str(cfg['world']['real_time_factor'])
    scene=ET.SubElement(world,'scene');ET.SubElement(scene,'ambient').text=' '.join(map(str,cfg['world']['ambient']))
    ET.SubElement(scene,'background').text='.5 .6 .7 1';ET.SubElement(scene,'shadows').text='true'
    sun=ET.SubElement(world,'light',name='sun',type='directional');ET.SubElement(sun,'cast_shadows').text='true'
    ET.SubElement(sun,'direction').text='-.3 .2 -1';ET.SubElement(sun,'diffuse').text='.8 .8 .8 1';ET.SubElement(sun,'specular').text='.15 .15 .15 1'
    backgrounds=[a for a in cfg['assets'] if a['category']=='background']
    for i,a in enumerate(backgrounds):
        model=ET.SubElement(world,'model',name=a['asset_id']);ET.SubElement(model,'static').text='true'
        ET.SubElement(model,'pose').text=f"{i*cfg['world']['zone_spacing_m']} 0 {cfg['world']['ground_z']} 0 0 0"
        link=ET.SubElement(model,'link',name='ground');visual=ET.SubElement(link,'visual',name='surface')
        geom=ET.SubElement(visual,'geometry')
        if a.get('surface_mesh'):
            mesh=ET.SubElement(geom,'mesh');ET.SubElement(mesh,'uri').text=str(TOOL/a['surface_mesh'])
        else:
            plane=ET.SubElement(geom,'plane');ET.SubElement(plane,'normal').text='0 0 1';ET.SubElement(plane,'size').text=f"{cfg['world']['background_size_m']} {cfg['world']['background_size_m']}"
        mat=ET.SubElement(visual,'material');ET.SubElement(mat,'ambient').text='1 1 1 1';ET.SubElement(mat,'diffuse').text='1 1 1 1';ET.SubElement(mat,'specular').text='0 0 0 1'
        metal=ET.SubElement(ET.SubElement(mat,'pbr'),'metal');ET.SubElement(metal,'albedo_map').text=str(TOOL/a['local_path']);ET.SubElement(metal,'metalness').text='0';ET.SubElement(metal,'roughness').text='1'
        for key in ('normal','roughness'):
            if key in a.get('maps',{}):ET.SubElement(metal,key+'_map').text=str(TOOL/a['maps'][key])
    for asset in cfg['assets']:
        if asset['category'] not in [c['name'] for c in cfg['classes']]: continue
        label=next(c['gazebo_label'] for c in cfg['classes'] if c['name']==asset['category'])
        for slot in range(cfg['world']['pool_copies_per_variant']):
            model=pinned_model(asset,f"pool_{asset['asset_id']}_{slot}");ET.SubElement(model,'pose').text=f"{cfg['world']['staging_x_m']} 0 -50 0 0 0"
            plugin=ET.SubElement(model,'plugin',filename='gz-sim-label-system',name='gz::sim::systems::Label');ET.SubElement(plugin,'label').text=str(label);world.append(model)
    for asset in cfg['assets']:
        if asset['category']!='distractor':continue
        model=pinned_model(asset);ET.SubElement(model,'pose').text=f"{cfg['world']['staging_x_m']} 0 -50 0 0 0";world.append(model)
    rig=ET.SubElement(world,'model',name='dataset_rig');ET.SubElement(rig,'static').text='true'
    ET.SubElement(rig,'pose').text='0 0 20 0 1.5707963267948966 0';camera_sensors(ET.SubElement(rig,'link',name='camera_link'),cfg['camera'],anti_aliasing=cfg['world'].get('anti_aliasing',1))
    ET.indent(sdf);atomic_write(path,ET.tostring(sdf,encoding='utf-8',xml_declaration=True))
