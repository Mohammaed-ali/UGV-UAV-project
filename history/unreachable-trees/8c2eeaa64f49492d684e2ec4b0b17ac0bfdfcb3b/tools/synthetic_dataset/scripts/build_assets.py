"""Build original, locally pinned low-detail assets. Does not download anything."""
import csv
import io
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import cv2
import numpy as np
import yaml
from common import TOOL, atomic_write, file_hash, write_json
from geometry import quaternion, rotation


def part(name, size, position, color, kind='box', rpy=(0,0,0)):
    return dict(name=name, kind=kind, size=list(size), position=list(position),
                rpy=list(rpy), color=list(color))


def surface_points(parts):
    points=[]
    for p in parts:
        if p['kind']=='box':
            from itertools import product
            pts=np.array(list(product(*[[-s/2,s/2] for s in p['size']])))
        else:
            radius,length=p['size']
            pts=np.array([[radius*math.cos(t),radius*math.sin(t),z] for t in
                          np.linspace(0,2*math.pi,64,endpoint=False) for z in (-length/2,length/2)])
        pts=pts@rotation(quaternion(*p['rpy'])).T+p['position']
        points.extend(pts.tolist())
    return points


def target_parts(cls,index):
    colors=[[.65,.13,.09],[.12,.32,.68],[.85,.77,.47],[.12,.53,.38]]
    color=colors[index]; dark=[.06,.07,.08]; glass=[.16,.25,.3]
    if cls=='person':
        height=[1.68,1.75,1.82,1.88][index]; scale=height/1.8
        p=[part('torso',[.27,.44,.62],[0,0,1.17],color),
           part('head',[.13,.23],[0,0,1.685],[.62,.39,.25],'cylinder'),
           part('leg_l',[.14,.15,.78],[0,.13,.39],dark),
           part('leg_r',[.14,.15,.78],[.08 if index==1 else 0,-.13,.39],dark),
           part('arm_l',[.13,.13,.63],[0,.31,1.13],color,rpy=(.15*index,0,0)),
           part('arm_r',[.13,.13,.63],[0,-.31,1.13],color,rpy=(-.12*index,0,0))]
        if index==3: p.append(part('backpack',[.22,.35,.4],[-.2,0,1.15],[.35,.22,.12]))
        for a in p:
            a['position']=[s*scale for s in a['position']];a['size']=[s*scale for s in a['size']]
        return p
    if cls=='car':
        length,width,height=[(4.2,1.75,1.42),(4.65,1.85,1.55),(4.9,1.9,1.65),(4.7,2.,1.85)][index]
        p=[part('body',[length,width,.65],[0,0,.62],color),
           part('cabin',[length*[.48,.55,.72,.67][index],width*.88,height-.85],[-.22,0,(height+.85)/2],color),
           part('windshield',[.04,width*.8,(height-.85)*.72],[length*.24-.2,0,(height+.85)/2],glass)]
    elif cls=='truck':
        length,width,height=[(6.2,2.25,2.5),(7.6,2.45,3.4),(8.6,2.5,3.0),(9.0,2.55,3.5)][index]
        p=[part('chassis',[length,width,.45],[0,0,.68],dark),
           part('cab',[1.8,width,height*.65],[length/2-.9,0,.9+height*.325],color),
           part('windshield',[.05,width*.86,.65],[length/2+.03,0,1.85],glass)]
        if index==0:
            p += [part('bed',[length-2,width,.25],[-1,0,1.],color),part('rail',[length-2,.1,.55],[-1,width/2,1.3],color)]
        elif index==2:
            p.append(part('tank',[width*.48,length-2.2],[-1,0,2.],[.65,.67,.69],'cylinder',rpy=(0,math.pi/2,0)))
        else:
            p.append(part('cargo_box',[length-2,width,height-1.],[-1,0,(height+1.)/2],color))
    else:
        length,width,height=[(10.5,2.5,3.0),(12.,2.55,3.3),(12.8,2.55,3.8)][index]
        p=[part('body',[length,width,height-.55],[0,0,(height+.55)/2],color)]
        for j in range(8):
            for sign in (-1,1):
                p.append(part(f'window_{j}_{sign}',[length/10,.02,.75],[-length*.4+j*length*.1,sign*(width/2+.01),height*.73],glass))
        p.append(part('front_glass',[.02,width*.88,1.0],[length/2+.01,0,height*.7],glass))
        if index==2:
            p += [part('roof_ac',[2.3,1.4,.25],[1.5,0,height+.125],dark),part('roof_hatch',[.8,.8,.1],[-2,0,height+.05],dark)]
    radius=.32 if cls=='car' else .46
    for x in (-length*.32,length*.32):
        for y in (-width*.48,width*.48):
            p.append(part(f'wheel_{x}_{y}',[radius,.18],[x,y,radius],dark,'cylinder',rpy=(math.pi/2,0,0)))
    return p


def model_sdf(asset):
    model=ET.Element('model',name=asset['asset_id']);ET.SubElement(model,'static').text='true'
    link=ET.SubElement(model,'link',name='body')
    for p in asset['parts']:
        visual=ET.SubElement(link,'visual',name=p['name'])
        ET.SubElement(visual,'pose').text=' '.join(map(str,p['position']+p['rpy']))
        geom=ET.SubElement(visual,'geometry')
        if p['kind']=='box':
            ET.SubElement(ET.SubElement(geom,'box'),'size').text=' '.join(map(str,p['size']))
        else:
            shape=ET.SubElement(geom,'cylinder');ET.SubElement(shape,'radius').text=str(p['size'][0]);ET.SubElement(shape,'length').text=str(p['size'][1])
        mat=ET.SubElement(visual,'material')
        for name in ('ambient','diffuse'): ET.SubElement(mat,name).text=' '.join(map(str,p['color']+[1]))
        ET.SubElement(mat,'specular').text='0 0 0 1'
        ET.SubElement(visual,'cast_shadows').text='true'
    return model


def texture(family,index):
    rng=np.random.default_rng(20261005+index+100*['grass','dirt','road','mixed'].index(family))
    base=np.array({'grass':[65,105,58],'dirt':[145,111,76],'road':[64,66,70],'mixed':[75,105,60]}[family],float)
    a=np.clip(base+rng.normal(0,7+index*2,(256,256,1)),0,255).astype(np.uint8)
    for _ in range(700):
        x,y=rng.integers(0,256,2);radius=int(rng.integers(1,3));cv2.circle(a,(int(x),int(y)),radius,tuple(int(v) for v in np.clip(base+rng.normal(0,18,3),0,255)),-1)
    if family=='road':
        for y in range(0,256,48): cv2.rectangle(a,(125,y),(129,y+23),(220,210,165),-1)
        cv2.line(a,(30,0),(30,255),(190,190,177),2);cv2.line(a,(224,0),(224,255),(190,190,177),2)
    elif family=='mixed':
        boundary=110+index*12;a[:,:boundary]=np.clip(np.array([140,105,74])+rng.normal(0,9,(256,boundary,1)),0,255)
        center=80+index*25;cv2.rectangle(a,(center-14,0),(center+14,255),(65,67,69),-1)
        for y in range(0,256,44): cv2.line(a,(center,y),(center,y+20),(225,211,170),2)
    return cv2.cvtColor(a,cv2.COLOR_RGB2BGR)


def main():
    manifest=[]
    for cls,n in [('person',4),('car',4),('truck',4),('bus',3)]:
        for i in range(n):
            aid=f'{cls}_{i}';parts=target_parts(cls,i);points=np.array(surface_points(parts))
            # Normalize exact lowest geometry point onto the ground plane.
            low=points[:,2].min()
            for p in parts: p['position'][2]-=float(low)
            points=np.array(surface_points(parts));dims=(points.max(0)-points.min(0)).tolist()
            asset={'asset_id':aid,'category':cls,'model_name':aid,'parts':parts,'geometry_points':points.tolist(),
                   'bounds':{'min':points.min(0).tolist(),'max':points.max(0).tolist()},'physical_dimensions_m':dims,
                   'held_out':cls!='person' and i==n-1,'eligibility':['test'] if cls!='person' and i==n-1 else ['train','val','test'],
                   'notes':'Original procedural geometry; simplified appearance. Person variants share one human template; no person model holdout claim.' if cls=='person' else 'Distinct dimensions and body/cargo geometry, not a recolored identical mesh.'}
            folder=TOOL/'models'/aid;folder.mkdir(parents=True,exist_ok=True)
            sdf=ET.Element('sdf',version='1.9');sdf.append(model_sdf(asset));ET.indent(sdf)
            atomic_write(folder/'model.sdf',ET.tostring(sdf,encoding='utf-8',xml_declaration=True))
            asset.update(local_path=f'models/{aid}/model.sdf',checksum=file_hash(folder/'model.sdf'))
            manifest.append(asset)
    for family in ['grass','dirt','road','mixed']:
        for i in range(4):
            p=TOOL/'assets'/'textures'/f'{family}_{i}.png';p.parent.mkdir(parents=True,exist_ok=True)
            success,data=cv2.imencode('.png',texture(family,i));assert success;atomic_write(p,data.tobytes())
            manifest.append({'asset_id':f'{family}_{i}','category':'background','family':family,
                             'model_name':f'{family}_procedural_{i}','local_path':str(p.relative_to(TOOL)),
                             'checksum':file_hash(p),'physical_dimensions_m':[240,240,0],
                             'held_out':i==3,'eligibility':['test'] if i==3 else ['train','val','test'],
                             'notes':'Original seeded procedural texture; heldout pattern is a distinct seed, not a real terrain asset.'})
    from world import clutter_assets
    for asset in clutter_assets():
        aid=asset['asset_id'];points=np.array(surface_points(asset['parts']))
        folder=TOOL/'models'/aid;folder.mkdir(parents=True,exist_ok=True)
        sdf=ET.Element('sdf',version='1.9');sdf.append(model_sdf(asset));ET.indent(sdf)
        atomic_write(folder/'model.sdf',ET.tostring(sdf,encoding='utf-8',xml_declaration=True))
        asset.update(category='distractor',model_name=aid,geometry_points=points.tolist(),
                     bounds={'min':points.min(0).tolist(),'max':points.max(0).tolist()},
                     physical_dimensions_m=(points.max(0)-points.min(0)).tolist(),local_path=f'models/{aid}/model.sdf',
                     checksum=file_hash(folder/'model.sdf'),held_out=False,eligibility=['train','val','test'],
                     notes='Original static non-target structure. No target class label.')
        manifest.append(asset)
    for a in manifest:
        a.update(source_uri='repo:tools/synthetic_dataset/scripts/build_assets.py#'+a['asset_id'],provider_author='Wildlife project procedural generator',
                 upstream_version='procedural-v1',license='CC0-1.0',download_date=None,creation_date='2026-10-05')
    write_json(TOOL/'assets/manifests/assets.json',manifest)
    fields=['asset_id','category','model_name','source_uri','provider_author','upstream_version','license','download_date','creation_date','checksum','local_path','physical_dimensions_m','eligibility','notes']
    stream=io.StringIO();w=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(manifest);atomic_write(TOOL/'assets/manifests/assets.csv',stream.getvalue())
    print(f'Pinned {len(manifest)} original assets; no external download')


if __name__=='__main__': main()
