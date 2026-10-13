"""Articulate the standalone copied meshes; original assets stay intact.

Split triangle meshes into rigid limbs / wheel parts, preserving material colors.
The background body retains one conservative physical collision envelope.
"""
from pathlib import Path
import copy,json,xml.etree.ElementTree as E
import numpy as np

ROOT=Path(__file__).resolve().parents[1];NS='http://www.collada.org/2005/11/COLLADASchema';N={'c':NS}
E.register_namespace('',NS)
def tag(name):return '{'+NS+'}'+name

def split_file(source,out,name,kind,color):
    tree=E.parse(source);root=tree.getroot();mesh=root.find('.//c:mesh',N)
    if mesh is None:return []
    positions=next(s for s in mesh.findall('c:source',N) if 'position' in s.attrib['id'].lower())
    values=np.array(list(map(float,positions.find('c:float_array',N).text.split()))).reshape(-1,3)
    triangles=mesh.find('c:triangles',N)
    if triangles is None:raise ValueError('Expected triangulated licensed mesh: '+str(source))
    stride=max(int(i.attrib['offset']) for i in triangles.findall('c:input',N))+1
    vertex_offset=int(next(i.attrib['offset'] for i in triangles.findall('c:input',N) if i.attrib['semantic']=='VERTEX'))
    raw=np.array(list(map(int,triangles.find('c:p',N).text.split()))).reshape(-1,3,stride)
    centers=values[raw[:,:,vertex_offset]].mean(1);labels=[]
    for p in centers:
        if kind=='person':
            if p[2]<.86:label='leg_left' if p[1]>=0 else 'leg_right'
            elif abs(p[1])>.215 and p[2]<1.43:label='arm_left' if p[1]>=0 else 'arm_right'
            else:label='body'
        else:
            # Existing licensed rubber meshes consist of the four tire surfaces;
            # keep each whole tire instead of cutting it at an arbitrary height.
            wheel=('rubber' in name)
            label=('wheel_'+('front' if p[0]>=0 else 'rear')+'_'+('left' if p[1]>=0 else 'right')) if wheel else 'body'
        labels.append(label)
    parts=[]
    for label in sorted(set(labels)):
        mask=np.array([x==label for x in labels]);selected=raw[mask]
        verts=values[np.unique(selected[:,:,vertex_offset])]
        if label.startswith('leg'):pivot=[0,.105 if label.endswith('left') else -.105,.87]
        elif label.startswith('arm'):pivot=[0,.23 if label.endswith('left') else -.23,1.38]
        elif label.startswith('wheel'):pivot=((verts.min(0)+verts.max(0))/2).tolist()
        else:pivot=[0,0,0]
        clone=copy.deepcopy(root);cmesh=clone.find('.//c:mesh',N)
        psource=next(s for s in cmesh.findall('c:source',N) if 'position' in s.attrib['id'].lower())
        psource.find('c:float_array',N).text=' '.join(f'{v:.8g}' for v in (values-np.array(pivot)).ravel())
        tris=cmesh.find('c:triangles',N);tris.attrib['count']=str(len(selected));tris.find('c:p',N).text=' '.join(map(str,selected.ravel()))
        file=name+'_'+label+'.dae';E.ElementTree(clone).write(out/file,encoding='utf-8',xml_declaration=True)
        parts.append({'file':f'/assets-sim/city/{source.parent.name}/{file}','color':color,'pivot':pivot,
                      'kind':'wheel' if label.startswith('wheel') else label,'name':name+'_'+label,'radius':float((verts[:,2].max()-verts[:,2].min())/2) if label.startswith('wheel') else 0,'steering':label.startswith('wheel_front')})
    return parts

def main():
    manifest=json.loads((ROOT/'assets/manifest.json').read_text());result={}
    textured=ROOT/'assets/textured-car-manifest.json'
    for model,parts in manifest.items():
        if model.startswith('car_mesh_') and textured.is_file():
            result[model]=json.loads(textured.read_text());continue
        out=ROOT/'assets/city'/model;out.mkdir(parents=True,exist_ok=True);result[model]=[]
        kind='person' if model.startswith('human') else model.split('_')[0]
        for part in parts:
            source=ROOT/'assets'/part['file'].removeprefix('/assets-sim/')
            # Sedan glass receives a realistic dark tint on these standalone
            # articulated copies; original licensed meshes/materials stay intact.
            color=[.04,.08,.10] if model=='car_mesh_0' and source.stem=='paint_7' else part['color']
            result[model].extend(split_file(source,out,source.stem,kind,color))
    for parts in result.values():
        front=[p['pivot'][0] for p in parts if p.get('steering')];rear=[p['pivot'][0] for p in parts if p['kind']=='wheel' and not p.get('steering')]
        wheelbase=(sum(front)/len(front)-sum(rear)/len(rear)) if front and rear else 3.2
        for part in parts:
            part['wheelbase']=wheelbase
            if part['kind']=='wheel':part['radius']=max(p['radius'] for p in parts if p['kind']=='wheel' and p['name'].split('wheel_',1)[1]==part['name'].split('wheel_',1)[1])
    textured=ROOT/'assets/textured-car-manifest.json'
    if textured.is_file():
        for variant in ('car_mesh_0','car_mesh_1'):result[variant]=json.loads(textured.read_text())
    (ROOT/'assets/city-manifest.json').write_text(json.dumps(result))
    print('Prepared articulated standalone city meshes:',sum(map(len,result.values())),'parts')
if __name__=='__main__':main()
