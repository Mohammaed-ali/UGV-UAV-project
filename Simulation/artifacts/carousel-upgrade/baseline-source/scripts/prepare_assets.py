"""Copy selected, licensed reference assets. The source workspace is read-only."""
from pathlib import Path
import shutil,json,xml.etree.ElementTree as E,hashlib
import cv2

root=Path(__file__).resolve().parents[1]
reference=Path('/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3/tools/synthetic_dataset')
target=root/'assets/models';target.mkdir(parents=True,exist_ok=True)
manifest={}
for name in [*(f'human_mesh_{i}' for i in range(4)),'car_mesh_0','truck_mesh_0','bus_mesh_0']:
    source=reference/'models'/name
    shutil.copytree(source,target/name,dirs_exist_ok=True)
    (target/name/'model.config').write_text(f'<?xml version="1.0"?><model><name>{name}</name><version>1.0</version><sdf version="1.9">model.sdf</sdf><description>Independent Fieldlab asset copy</description></model>')
    model=E.parse(source/'model.sdf').getroot().find('model');parts=[]
    for v in model.findall('.//visual'):
        mesh=v.find('geometry/mesh/uri')
        if mesh is not None:
            parts.append({'file':f'/assets-sim/models/{name}/{mesh.text}','color':[float(x) for x in v.findtext('material/diffuse','.5 .5 .5 1').split()[:3]]})
    manifest[name]=parts
    # Collision proxies are added only to the standalone copies.
    tree=E.parse(target/name/'model.sdf');link=tree.getroot().find('model/link');c=E.SubElement(link,'collision',name='actor_collision')
    E.SubElement(c,'pose').text='0 0 .85 0 0 0' if name.startswith('human') else '0 0 .8 0 0 0'
    E.SubElement(E.SubElement(E.SubElement(c,'geometry'),'box'),'size').text='.5 .5 1.7' if name.startswith('human') else '4 1.8 1.6'
    tree.write(target/name/'model.sdf',encoding='utf-8',xml_declaration=True)
(root/'assets/manifest.json').write_text(json.dumps(manifest))
licenses=root/'assets/licenses';licenses.mkdir(exist_ok=True)
for p in [reference/'assets/LICENSE', reference.parent.parent/'docs/dataset/ASSETS_V2.md']:
    if p.is_file():shutil.copy2(p,licenses/p.name)
tags=target/'tags';tags.mkdir(exist_ok=True)
d=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
for i in range(1,9):
    image=cv2.aruco.generateImageMarker(d,i,320) if hasattr(cv2.aruco,'generateImageMarker') else cv2.aruco.drawMarker(d,i,320)
    image=cv2.copyMakeBorder(image,40,40,40,40,cv2.BORDER_CONSTANT,value=255)
    cv2.imwrite(str(tags/f'tag_{i}.png'),image)
(root/'assets/provenance.json').write_text(json.dumps({'source':str(reference),'source_access':'read-only copy','tags':{'family':'tag36h11','ids':list(range(1,9)),'texture_meters':.38,'detection_corner_size_meters':.38*.8},'files':{str(p.relative_to(root/'assets')):hashlib.sha256(p.read_bytes()).hexdigest() for p in target.rglob('*') if p.is_file()}},indent=2))
print('Prepared independent scene assets and eight AprilTags.')
