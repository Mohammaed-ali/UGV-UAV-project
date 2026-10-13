"""Pinned Open Robotics Prius visual conversion; keep controlled body occupancy.

Coordinates are converted once to X-forward metres. OBJ faces, UVs and materials
are preserved in Collada for both Gazebo and Three.js. No imported controllers.
"""
from pathlib import Path
import urllib.request,json,hashlib,shutil,xml.etree.ElementTree as E,numpy as np
ROOT=Path(__file__).resolve().parents[1];PIN='38a4686dd573739dcd237187030efba3ce4913b0'
NS='http://www.collada.org/2005/11/COLLADASchema';E.register_namespace('',NS)
def el(p,tag,text=None,**attrs):
 e=E.SubElement(p,'{'+NS+'}'+tag,attrs)
 if text is not None:e.text=str(text)
 return e

def read_obj(path):
 vertices=[];uv=[];normals=[];faces={};material='Hybrid'
 for line in path.read_text().splitlines():
  fields=line.split()
  if not fields:continue
  if fields[0]=='v':vertices.append(list(map(float,fields[1:4])))
  elif fields[0]=='vt':uv.append(list(map(float,fields[1:3])))
  elif fields[0]=='vn':normals.append(list(map(float,fields[1:4])))
  elif fields[0]=='usemtl':material=fields[1]
  elif fields[0]=='f':
   indices=[[int(n)-1 for n in item.split('/')] for item in fields[1:]]
   for i in range(1,len(indices)-1):faces.setdefault(material,[]).append([indices[0],indices[i],indices[i+1]])
 return np.array(vertices),np.array(uv),np.array(normals),faces

def write_dae(path,vertices,uv,normals,faces):
 doc=E.Element('{'+NS+'}COLLADA',version='1.4.1');asset=el(doc,'asset');el(asset,'unit',meter='1',name='meter');el(asset,'up_axis','Z_UP')
 images=el(doc,'library_images');effects=el(doc,'library_effects');materials=el(doc,'library_materials')
 for name in faces:
  effect=el(effects,'effect',id=name+'-effect');common=el(effect,'profile_COMMON')
  if name!='Windows':
   image=el(images,'image',id=name+'-image');el(image,'init_from',name+'.png');param=el(common,'newparam',sid=name+'-surface');surface=el(param,'surface',type='2D');el(surface,'init_from',name+'-image');param=el(common,'newparam',sid=name+'-sampler');sampler=el(param,'sampler2D');el(sampler,'source',name+'-surface')
  technique=el(common,'technique',sid='common');phong=el(technique,'phong');diffuse=el(phong,'diffuse')
  if name=='Windows':el(diffuse,'color','.10 .14 .17 1')
  else:el(diffuse,'texture',texture=name+'-sampler',texcoord='UVMap')
  el(el(phong,'specular'),'color','.15 .15 .15 1');el(el(phong,'shininess'),'float',20)
  material=el(materials,'material',id=name+'-material',name=name);el(material,'instance_effect',url='#'+name+'-effect')
 geometries=el(doc,'library_geometries');geom=el(geometries,'geometry',id='car-geometry');mesh=el(geom,'mesh')
 for name,data,size,params in [('positions',vertices,3,['X','Y','Z']),('normals',normals,3,['X','Y','Z']),('uv',uv,2,['S','T'])]:
  source=el(mesh,'source',id=name);el(source,'float_array',' '.join(f'{x:.8g}' for x in data.ravel()),id=name+'-array',count=str(data.size));accessor=el(el(source,'technique_common'),'accessor',source='#'+name+'-array',count=str(len(data)),stride=str(size))
  for param in params:el(accessor,'param',name=param,type='float')
 vert=el(mesh,'vertices',id='vertices');el(vert,'input',semantic='POSITION',source='#positions')
 for name,triangles in faces.items():
  tri=el(mesh,'triangles',count=str(len(triangles)),material=name);el(tri,'input',semantic='VERTEX',source='#vertices',offset='0');el(tri,'input',semantic='TEXCOORD',source='#uv',offset='1',set='0');el(tri,'input',semantic='NORMAL',source='#normals',offset='2');el(tri,'p',' '.join(str(x) for t in triangles for v in t for x in v))
 scene=el(el(doc,'library_visual_scenes'),'visual_scene',id='car-scene');node=el(scene,'node',id='car');instance=el(node,'instance_geometry',url='#car-geometry');binding=el(el(instance,'bind_material'),'technique_common')
 for name in faces:
  im=el(binding,'instance_material',symbol=name,target='#'+name+'-material');el(im,'bind_vertex_input',semantic='UVMap',input_semantic='TEXCOORD',input_set='0')
 el(el(doc,'scene'),'instance_visual_scene',url='#car-scene');E.ElementTree(doc).write(path,encoding='utf-8',xml_declaration=True)

def main():
 source=ROOT/'assets/models/prius_visual';out=ROOT/'assets/city/textured_car';source.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
 base='https://raw.githubusercontent.com/osrf/car_demo/'+PIN+'/prius_description/meshes/'
 package=source/'package.xml'
 if not package.exists():
  with urllib.request.urlopen('https://raw.githubusercontent.com/osrf/car_demo/'+PIN+'/prius_description/package.xml',timeout=60) as r:package.write_bytes(r.read())
 license_path=ROOT/'assets/licenses/OpenRobotics-Prius-Apache-2.0.txt'
 if not license_path.exists():
  with urllib.request.urlopen('https://www.apache.org/licenses/LICENSE-2.0.txt',timeout=60) as r:license_path.write_bytes(r.read())
 hashes={}
 for name in ('hybrid_body.obj','hybrid_body.mtl','Hybrid.png','Hybrid_Interior.png','wheel.obj','wheel.mtl','Wheels3.png'):
  p=source/name
  if not p.exists():
   with urllib.request.urlopen(base+name,timeout=60) as r:p.write_bytes(r.read())
  hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
  if name.endswith('.png'):shutil.copy2(p,out/name)
 v,uv,n,f=read_obj(source/'hybrid_body.obj');center=(v.min(0)+v.max(0))/2;xs=4.4/(v[:,1].max()-v[:,1].min());ys=1.8/(v[:,0].max()-v[:,0].min())
 body=np.stack((-(v[:,1]-center[1])*xs,(v[:,0]-center[0])*ys,v[:,2]*.01),axis=1);normals=np.stack((-n[:,1],n[:,0],n[:,2]),axis=1);write_dae(out/'body.dae',body,uv,normals,f)
 wheel,wuv,wn,wf=read_obj(source/'wheel.obj');wheel=np.stack((-wheel[:,1],wheel[:,0],wheel[:,2]),axis=1)*.01;wn=np.stack((-wn[:,1],wn[:,0],wn[:,2]),axis=1);write_dae(out/'wheel.dae',wheel,wuv,wn,wf)
 radius=(wheel[:,2].max()-wheel[:,2].min())/2;parts=[{'file':'/assets-sim/city/textured_car/body.dae','color':[1,1,1],'pivot':[0,0,0],'kind':'body','name':'textured_car_body','textured':True}]
 front=-(-141.-center[1])*xs;rear=-(145.-center[1])*xs
 for x,label,ybase in [(front,'front',76.7),(rear,'rear',79.3)]:
  for side in (-1,1):
   parts.append({'file':'/assets-sim/city/textured_car/wheel.dae','color':[1,1,1],'pivot':[x,side*ybase*ys,radius],'kind':'wheel','name':'prius_'+label+('_left' if side>0 else '_right'),'radius':radius,'steering':label=='front','wheelbase':front-rear,'textured':True})
 (ROOT/'assets/textured-car-manifest.json').write_text(json.dumps(parts));(source/'SOURCE.json').write_text(json.dumps({'source':'https://github.com/osrf/car_demo/tree/'+PIN+'/prius_description','revision':PIN,'license':'Apache-2.0 (package.xml)','source_files_sha256':hashes,'conversion':'X-forward, Z-up metres; normalized visual body footprint 4.4 x 1.8 m; conservative occupancy 4.45 x 1.85 x 1.65 m. Background control retained.'},indent=2))
 print('Prepared textured standalone Prius visuals:',len(parts),'parts')
if __name__=='__main__':main()
