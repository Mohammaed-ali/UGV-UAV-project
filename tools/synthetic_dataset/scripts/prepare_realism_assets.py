#!/usr/bin/env python3
"""Offline, reproducible derivatives of pinned CC0 meshes and photo textures.

The upstream downloads and their licenses are retained. This is asset preparation,
never postprocessing of exported camera images. No MakeHuman program code is used.
"""
from collections import defaultdict
from itertools import product
import csv
import io
import json
import math
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import cv2
import numpy as np
from scipy.spatial import ConvexHull
from common import TOOL, atomic_write, file_hash, write_json

UPSTREAM = TOOL / 'assets/upstream'
DATE = '2026-10-05'


def obj(path):
    vertices, uv, normals, faces = [], [], [], []
    group = 'body'
    for line in path.read_text().splitlines():
        values = line.split()
        if not values: continue
        if values[0] == 'v': vertices.append(list(map(float, values[1:4])))
        elif values[0] == 'vt': uv.append(list(map(float, values[1:3])))
        elif values[0] == 'vn': normals.append(list(map(float, values[1:4])))
        elif values[0] == 'g': group = values[1]
        elif values[0] == 'f':
            corners = [tuple(int(x)-1 if x else -1 for x in v.split('/')) for v in values[1:]]
            for i in range(1, len(corners)-1): faces.append((group, [corners[0], corners[i], corners[i+1]]))
    return np.array(vertices), np.array(uv), np.array(normals), faces


def dae(path, vertices, triangles, smooth=True, texcoords=None):
    """One geometry/material per file; SDF supplies the physically based material."""
    vertices = np.asarray(vertices, float);triangles = np.asarray(triangles, int)
    used = np.unique(triangles);remap = np.full(len(vertices), -1, int);remap[used] = np.arange(len(used))
    vertices, triangles = vertices[used], remap[triangles]
    edges = vertices[triangles]
    face_normals = np.cross(edges[:,1]-edges[:,0], edges[:,2]-edges[:,0])
    if smooth:
        normals = np.zeros_like(vertices)
        for column in range(3): np.add.at(normals, triangles[:,column], face_normals)
        normals /= np.maximum(np.linalg.norm(normals, axis=1)[:,None], 1e-14)
        ni = triangles
    else:
        normals = face_normals / np.maximum(np.linalg.norm(face_normals, axis=1)[:,None], 1e-14)
        ni = np.repeat(np.arange(len(triangles))[:,None], 3, axis=1)
    root = ET.Element('COLLADA', xmlns='http://www.collada.org/2005/11/COLLADASchema', version='1.4.1')
    asset=ET.SubElement(root,'asset');ET.SubElement(asset,'created').text=DATE+'T00:00:00Z'
    ET.SubElement(asset,'modified').text=DATE+'T00:00:00Z';ET.SubElement(asset,'unit', name='meter', meter='1')
    ET.SubElement(asset,'up_axis').text='Z_UP'
    mesh=ET.SubElement(ET.SubElement(ET.SubElement(root,'library_geometries'),'geometry',id='surface',name='surface'),'mesh')
    def source(name, data, parameters):
        s=ET.SubElement(mesh,'source',id=name);a=ET.SubElement(s,'float_array',id=name+'-array',count=str(data.size))
        a.text=' '.join(f'{v:.9g}' for v in data.ravel())
        acc=ET.SubElement(ET.SubElement(s,'technique_common'),'accessor',source='#'+name+'-array',count=str(len(data)),stride=str(data.shape[1]))
        for p in parameters: ET.SubElement(acc,'param',name=p,type='float')
    source('positions',vertices,['X','Y','Z']);source('normals',normals,['X','Y','Z'])
    v=ET.SubElement(mesh,'vertices',id='vertices');ET.SubElement(v,'input',semantic='POSITION',source='#positions')
    t=ET.SubElement(mesh,'triangles',count=str(len(triangles)))
    ET.SubElement(t,'input',semantic='VERTEX',source='#vertices',offset='0')
    ET.SubElement(t,'input',semantic='NORMAL',source='#normals',offset='1')
    indices=np.stack([triangles,ni],axis=-1)
    if texcoords is not None:
        source('uv', np.asarray(texcoords)[used], ['S','T'])
        ET.SubElement(t,'input',semantic='TEXCOORD',source='#uv',offset='2',set='0')
        indices=np.stack([triangles,ni,triangles],axis=-1)
    ET.SubElement(t,'p').text=' '.join(map(str,indices.ravel()))
    lib=ET.SubElement(root,'library_visual_scenes');scene=ET.SubElement(lib,'visual_scene',id='Scene')
    node=ET.SubElement(scene,'node',id='mesh',name='mesh');ET.SubElement(node,'instance_geometry',url='#surface')
    ET.SubElement(ET.SubElement(root,'scene'),'instance_visual_scene',url='#Scene')
    atomic_write(path,ET.tostring(root,encoding='utf-8',xml_declaration=True))


def mesh_asset(aid, category, vertices, face_groups, colors, provenance, held_out=False, notes=''):
    folder=TOOL/'models'/('context_v2/'+aid if category=='distractor' else aid);folder.mkdir(parents=True,exist_ok=True)
    for stale in folder.glob('*.dae'):stale.unlink()  # Only this builder's derivative files.
    vertices=np.asarray(vertices, float).copy()
    referenced=np.unique([v for faces in face_groups.values() for f in faces for v in f])
    points=vertices[referenced];low=points.min(0);high=points.max(0)
    vertices[:,:2]-=(low[:2]+high[:2])/2;vertices[:,2]-=low[2]
    points=vertices[referenced]
    # Extreme vertices of the convex hull give the exact full-mesh image bounds.
    hull=points[ConvexHull(points).vertices]
    sdf=ET.Element('sdf',version='1.9');model=ET.SubElement(sdf,'model',name=aid)
    ET.SubElement(model,'static').text='true';link=ET.SubElement(model,'link',name='body')
    dependencies=[];triangle_count=0
    for name,faces in face_groups.items():
        if not faces: continue
        p=folder/(name+'.dae');dae(p,vertices,faces,smooth=category=='person')
        dependencies.append({'local_path':str(p.relative_to(TOOL)),'checksum':file_hash(p)})
        triangle_count+=len(faces)
        visual=ET.SubElement(link,'visual',name=name);mesh=ET.SubElement(ET.SubElement(visual,'geometry'),'mesh')
        ET.SubElement(mesh,'uri').text=name+'.dae';ET.SubElement(mesh,'scale').text='1 1 1'
        material=ET.SubElement(visual,'material');color=colors[name]
        for field in ('ambient','diffuse'):ET.SubElement(material,field).text=' '.join(map(str,list(color)+[1]))
        ET.SubElement(material,'specular').text='.18 .18 .18 1'
        metal=ET.SubElement(ET.SubElement(material,'pbr'),'metal')
        ET.SubElement(metal,'metalness').text='0.15' if category!='person' and name.startswith('paint') else '0'
        ET.SubElement(metal,'roughness').text='.25' if name.startswith('glass') else '.48' if category!='person' else '.85'
        ET.SubElement(visual,'cast_shadows').text='true'
    ET.indent(sdf);p=folder/'model.sdf';atomic_write(p,ET.tostring(sdf,encoding='utf-8',xml_declaration=True))
    return dict(asset_id=aid,category=category,model_name=aid,local_path=str(p.relative_to(TOOL)),checksum=file_hash(p),
                dependencies=dependencies,geometry_points=hull.tolist(),geometry_method='convex hull of all rendered mesh vertices',
                bounds={'min':points.min(0).tolist(),'max':points.max(0).tolist()},physical_dimensions_m=(points.max(0)-points.min(0)).tolist(),
                triangle_count=triangle_count,held_out=held_out,eligibility=['test'] if held_out else ['train','val','test'],
                notes=notes,license='CC0-1.0',download_date=DATE,creation_date=DATE,**provenance)


def humans():
    source=UPSTREAM/'makehuman/base.obj';vertices,_,_,faces=obj(source)
    rev=(UPSTREAM/'makehuman/revision.txt').read_text().strip()
    clothing=[(.15,.24,.36),(.47,.23,.16),(.36,.43,.28),(.55,.49,.34),(.27,.35,.43),(.43,.19,.25),(.20,.39,.37),(.65,.59,.45)]
    skins=[(.68,.45,.32),(.36,.23,.16),(.79,.58,.43),(.53,.33,.22)]
    result=[]
    for i in range(8):
        pts=vertices.copy();height=[1.68,1.74,1.80,1.86,1.72,1.82,1.77,1.89][i]
        # Smooth static arm lowering; no animation or skeleton dependency at run time.
        for sign in (-1,1):
            weight=np.clip((sign*pts[:,0]-1.15)/.55,0,1)*np.clip((pts[:,1]+1.0)/2.0,0,1)
            angle=-sign*math.radians([24,32,27,20,30,25,18,28][i])*weight
            x=pts[:,0]-sign*1.45;y=pts[:,1]-4.8
            pts[:,0]=sign*1.45+np.cos(angle)*x-np.sin(angle)*y
            pts[:,1]=4.8+np.sin(angle)*x+np.cos(angle)*y
        pts[:,0]*=[.95,1.03,1,1.06,.97,1.02,1.10,.96][i]
        # Source Y is up, Z is forward. Export X forward, Y left, Z up, meters.
        pts=np.column_stack([pts[:,2],-pts[:,0],pts[:,1]])*height/16.7168
        groups=defaultdict(list)
        for group,corners in faces:
            f=[c[0] for c in corners];center=vertices[f].mean(0)
            f=f[::-1]  # X=source Z, Y=-source X, Z=source Y reflects handedness.
            if group=='body':
                # The clothed proxy covers torso/legs. Retain head and exposed hands.
                if center[1]<5.85 and abs(center[0])<3.95:continue
                if center[1]>7.75 and center[2]<1.45:name='hair'
                else:name='skin'
            elif group=='helper-tights':
                if center[1]<-6.65:name='shoes'
                elif center[1]<.9:name='trousers'
                else:name='shirt'
            else:continue  # Helpers/joints/genital/teeth proxies are never rendered.
            groups[name].append(f)
        colors={'shirt':clothing[i],'trousers':[(.11,.13,.17),(.19,.20,.19),(.25,.22,.18)][i%3],
                'skin':skins[i%4],'hair':[(.07,.045,.025),(.22,.14,.06),(.055,.04,.03)][i%3],'shoes':(.055,.055,.055)}
        result.append(mesh_asset(f'human_mesh_{i}','person',pts,groups,colors,
                                dict(source_uri=f'https://raw.githubusercontent.com/makehumancommunity/makehuman/{rev}/makehuman/data/3dobjs/base.obj',
                                     provider_author='MakeHuman community; project clothed static derivatives',upstream_version=rev,
                                     upstream_checksum=file_hash(source),template_family='makehuman-hm08-shared',model_scale=height/16.7168,
                                     pose_variant=f'arms_lowered_{[24,32,27,20,30,25,18,28][i]}deg',appearance_variant=i),
                                notes='Shared CC0 hm08 body and clothed tights proxy; adult height/proportion, static arm pose, skin/clothing variants. No independent person-model holdout.'))
    return result


def vehicles():
    root=UPSTREAM/'kenney/Models/OBJ format'
    palette=cv2.cvtColor(cv2.imread(str(root/'Textures/colormap.png')),cv2.COLOR_BGR2RGB)
    definitions=[('sedan','car',(4.4,1.8,1.5)),('hatchback-sports','car',(4.1,1.78,1.48)),('suv','car',(4.7,1.96,1.85)),('suv-luxury','car',(4.95,2,1.85)),
                 ('truck','truck',(7.6,2.48,3.35)),('truck-flat','truck',(7,2.4,2.9)),('delivery','truck',(6.2,2.2,3)),('delivery-flat','truck',(6.1,2.2,2.8))]
    result=[]
    for name,cls,dimensions in definitions:
        source=root/(name+'.obj');v,uv,_,faces=obj(source);scale=np.asarray(dimensions)/(v.max(0)-v.min(0))[[2,0,1]]
        vertices=v[:,[2,0,1]]*scale;groups=defaultdict(list);colors={}
        samples=[]
        for group,corners in faces:
            t=uv[[c[1] for c in corners]].mean(0)
            samples.append(palette[int(np.clip((1-t[1])*palette.shape[0],0,palette.shape[0]-1)),int(np.clip(t[0]*palette.shape[1],0,palette.shape[1]-1))]/255)
        # UV gradients do not need hundreds of separate draw calls. Preserve
        # twelve fitted color clusters and let physical lighting provide shading.
        cv2.setRNGSeed(1729);cv2.setNumThreads(1)
        _,labels,centers=cv2.kmeans(np.asarray(samples,np.float32),12,None,(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,40,1e-6),1,cv2.KMEANS_PP_CENTERS)
        for (group,corners),label in zip(faces,labels[:,0]):
            f=[c[0] for c in corners];rgb=centers[label]
            key='paint_'+str(int(label))
            if 'wheel' in group and max(rgb)<.35:key='rubber_'+key
            if max(rgb)-min(rgb)>.08 and rgb[2]>rgb[0]*1.3:key='glass_'+key
            # Keep source material distinctions while muting the bright kit palette.
            colors[key]=np.clip(rgb*.75+.04,0,1).tolist();groups[key].append(f)
        index=sum(a['category']==cls for a in result);held_out=index==3
        result.append(mesh_asset(f'{cls}_mesh_{index}',cls,vertices,groups,colors,
                                dict(source_uri='https://kenney.nl/assets/car-kit',provider_author='Kenney',upstream_version='Car Kit 3.1',
                                     upstream_model=name,upstream_checksum=file_hash(source),model_scale=scale.tolist(),template_family='kenney-'+name,
                                     material_color_clusters=12),held_out,
                                notes='CC0 vehicle mesh with wheels, beveled body, cabin/glazing and lights; axis-normalized to plausible full-size dimensions. Stylized geometry remains.'))
    return result


def buses():
    """Original beveled coach/minibus bodies, curved roofs and explicit glazing/wheels."""
    result=[]
    for i,(length,width,height) in enumerate([(8.2,2.35,2.85),(11.5,2.5,3.15),(12.4,2.55,3.45)]):
        verts=[];groups=defaultdict(list)
        def shape(name,points,triangles):
            offset=len(verts);verts.extend(points);groups[name].extend([[x+offset for x in f] for f in triangles])
        def box(name,center,size):
            points=(np.array(list(product((-1,1),repeat=3)))*np.asarray(size)/2+center).tolist()
            tris=[[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]]
            shape(name,points,tris)
        # Chamfered cross section and longitudinally rounded/chamfered front/rear.
        section=[(-width/2,.65),(-width/2,height-.20),(-width/2+.16,height), (width/2-.16,height),(width/2,height-.20),(width/2,.65)]
        points=[]
        for x,s in [(-length/2,.90),(-length/2+.2,1),(length/2-.3,1),(length/2,.9)]:
            points.extend([[x,y*s,z] for y,z in section])
        tris=[];n=len(section)
        for ring in range(3):
            for k in range(n):a=ring*n+k;b=ring*n+(k+1)%n;c=b+n;d=a+n;tris.extend([[a,b,c],[a,c,d]])
        for ring in (0,3):
            for k in range(1,n-1):tris.append([ring*n,ring*n+k,ring*n+k+1] if ring==3 else [ring*n,ring*n+k+1,ring*n+k])
        shape('paint_body',points,[f[::-1] for f in tris])
        box('chassis',[0,0,.6],[length*.95,width*.92,.25])
        # Side glazing retains individual pillars and door breaks.
        for x in np.arange(-length/2+.7,length/2-.6,1.1):
            for sign in (-1,1):box('glass_windows',[x,sign*(width/2+.009),height-.8],[.85,.012,.85])
        box('glass_front',[length/2+.011,0,height-1.0],[.018,width*.8,1.0])
        box('glass_rear',[-length/2-.011,0,height-.75],[.018,width*.65,.7])
        for x in (-length*.32,length*.31):
            for sign in (-1,1):
                wheel=[];r=.43
                for y in (sign*width*.45-.14,sign*width*.45+.14):
                    wheel.extend([[x+r*math.cos(a),y,r+r*math.sin(a)] for a in np.linspace(0,2*math.pi,24,endpoint=False)])
                ts=[]
                for k in range(24):q=(k+1)%24;ts.extend([[k,q,q+24],[k,q+24,k+24]])
                for k in range(1,23):ts.extend([[0,k+1,k],[24,24+k,24+k+1]])
                shape('rubber_wheels',wheel,[f[::-1] for f in ts])
        for x in (-length*.19,length*.2):box('roof_detail',[x,0,height+.08],[1.3,1.2,.16])
        for sign in (-1,1):
            box('lamps',[length/2+.025,sign*width*.34,.95],[.03,.25,.2])
            box('mirrors',[length/2-.4,sign*(width/2+.16),height-1.1],[.3,.23,.27])
        colors={'paint_body':[(.52,.55,.52),(.17,.32,.39),(.53,.38,.25)][i], 'chassis':(.09,.09,.09),
                'glass_windows':(.075,.14,.17),'glass_front':(.07,.13,.16),'glass_rear':(.07,.13,.16),
                'rubber_wheels':(.045,.045,.045),'roof_detail':(.24,.26,.25),'lamps':(.86,.82,.63),'mirrors':(.18,.19,.19)}
        result.append(mesh_asset(f'bus_mesh_{i}','bus',verts,groups,colors,
                                dict(source_uri='repo:tools/synthetic_dataset/scripts/prepare_realism_assets.py#buses',provider_author='Wildlife project',
                                     upstream_version='beveled-bus-v2',model_scale=1,template_family='procedural-bus-'+str(i)),i==2,
                                notes='Original static beveled coach body, pillars, glazing, wheels, mirrors and roof units. Simplified, not a real manufacturer model.'))
    return result


def terrains():
    sources={'grass':['grass_ground','leafy_grass','grass_path_2','grass_path_3'],
             'dirt':['dirt_aerial_02','dirt_aerial_03','aerial_mud_1','dry_mud_field_001'],
             'road':['aerial_asphalt_01','asphalt_02','asphalt_05','asphalt_04']}
    result=[]
    folder=TOOL/'assets/terrain';folder.mkdir(parents=True,exist_ok=True)
    for family in ['grass','dirt','road','mixed']:
        for i in range(4):
            names=[sources[family][i]] if family!='mixed' else [sources[k][i] for k in ['grass','dirt','road']]
            inputs=[];maps={};deps=[]
            # 80 m physical mosaic, tiled three times across the 240 m plane.
            # Photo texture detail is maintained; irregular transitions/road margins
            # are prepared as underlying terrain materials, not exported-image edits.
            size=2048;y,x=np.mgrid[:size,:size];u=(x-size/2)/size*80;v=(y-size/2)/size*80
            boundary=8*np.sin(v*.07+i)+2*np.sin(v*.43)
            road_width=7 if family=='road' else 5.5
            if family=='road': road_mask=np.clip((road_width/2-abs(u))/1.0+.5,0,1);dirt_mask=1-road_mask
            elif family=='mixed':road_mask=np.clip((road_width/2-abs(u-boundary))/1+.5,0,1);dirt_mask=np.clip((u-boundary+12)/5,0,1)*(1-road_mask)
            else:road_mask=np.zeros_like(u);dirt_mask=np.zeros_like(u)
            # Road scenes use the same-family index's grass/dirt margin source,
            # including disjoint index-3 heldout source textures.
            if family=='road':names=[sources['grass'][i],sources['dirt'][i],sources['road'][i]]
            for name in names:
                p=UPSTREAM/'polyhaven'/name;info=json.loads((p/'info.json').read_text())
                inputs.append({'source_uri':'https://polyhaven.com/a/'+name,'asset_id':name,'authors':info['authors'],
                               'api_files_sha256':file_hash(p/'files.json'),'license':'CC0-1.0'})
            for mapname,suffix in [('albedo','diff'),('roughness','rough'),('normal','nor_gl')]:
                images=[]
                for name in names:
                    p=next((UPSTREAM/'polyhaven'/name).glob('*_'+suffix+'_1k.*'));im=cv2.imread(str(p))
                    # Scale photo tile widths conservatively where no metric scale exists.
                    tile_m={'dirt_aerial_02':20,'dirt_aerial_03':25,'aerial_mud_1':40,'aerial_asphalt_01':15}.get(name,6)
                    xx=((u/tile_m+i*.137)%1*(im.shape[1]-1)).astype(np.float32)
                    yy=((v/tile_m+i*.193)%1*(im.shape[0]-1)).astype(np.float32)
                    tiled=cv2.remap(im,xx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_WRAP).astype(float)
                    images.append(tiled)
                if family in ('road','mixed'):
                    g,d,a=images;blend=g*(1-dirt_mask-road_mask)[...,None]+d*dirt_mask[...,None]+a*road_mask[...,None]
                    if mapname=='albedo':
                        # Worn road markings in ground coordinates, not huge stripes.
                        center=u if family=='road' else u-boundary
                        marks=(abs(center)<.07)&((v%9)<3.5)
                        edges=(abs(abs(center)-road_width/2+.25)<.06)
                        worn=.55+.25*np.sin(v*17)*np.cos(u*23)
                        alpha=(marks|edges)*worn
                        blend=blend*(1-alpha[...,None])+np.array([155,177,186])*alpha[...,None]
                else:blend=images[0]
                # Low frequency natural tonal variation reduces visible tile repetition.
                if mapname=='albedo':blend*= (1+.045*np.sin(u*.18+i)*np.cos(v*.11))[...,None]
                p=folder/f'{family}_{i}_{mapname}.jpg';cv2.imwrite(str(p),np.clip(blend,0,255).astype(np.uint8),[cv2.IMWRITE_JPEG_QUALITY,93])
                maps[mapname]=str(p.relative_to(TOOL));deps.append({'local_path':maps[mapname],'checksum':file_hash(p)})
            mesh=folder/f'{family}_{i}.dae'
            dae(mesh,[[-120,-120,0],[120,-120,0],[120,120,0],[-120,120,0]],[[0,1,2],[0,2,3]],texcoords=[[0,0],[3,0],[3,3],[0,3]])
            deps.append({'local_path':str(mesh.relative_to(TOOL)),'checksum':file_hash(mesh)})
            result.append(dict(asset_id=f'{family}_{i}',category='background',family=family,model_name=f'{family}_photo_mosaic_{i}',
                               local_path=maps['albedo'],checksum=file_hash(TOOL/maps['albedo']),dependencies=deps,maps=maps,
                               surface_mesh=str(mesh.relative_to(TOOL)),physical_dimensions_m=[240,240,0],held_out=i==3,
                               eligibility=['test'] if i==3 else ['train','val','test'],source_uri=';'.join(a['source_uri'] for a in inputs),
                               source_assets=inputs,provider_author='Poly Haven photographers; project terrain mosaics',upstream_version='pinned-photo-mosaic-v2',
                               license='CC0-1.0',download_date=DATE,creation_date=DATE,model_scale=1,
                               notes='CC0 photographic PBR terrain maps, meter-scale detail and irregular road/terrain transitions. Index 3 uses disjoint photographic source assets; other index sources may be combined across background families.'))
    return result


def context_assets():
    result=[]
    definitions=[f'clutter_{i}' for i in range(6)]+['canopy_mild','canopy_moderate','shadow_wall']
    for index,aid in enumerate(definitions):
        verts=[];groups=defaultdict(list)
        def shape(name,points,triangles):
            offset=len(verts);verts.extend(np.asarray(points).tolist());groups[name].extend([[x+offset for x in f] for f in triangles])
        def box(name,center,size):
            points=np.array(list(product((-1,1),repeat=3)))*np.asarray(size)/2+center
            tris=[[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]]
            shape(name,points,tris)
        def cylinder(name,center,radius,height,n=12):
            points=[[center[0]+radius*math.cos(t),center[1]+radius*math.sin(t),center[2]+z] for z in [-height/2,height/2] for t in np.linspace(0,2*math.pi,n,endpoint=False)]
            tris=[]
            for k in range(n):q=(k+1)%n;tris.extend([[k,q,q+n],[k,q+n,k+n]])
            for k in range(1,n-1):tris.extend([[0,k+1,k],[n,n+k,n+k+1]])
            shape(name,points,tris)
        def crown(name,center,scale,seed):
            rng=np.random.default_rng(seed);points=[]
            for _ in range(60):
                d=rng.normal(size=3);d/=np.linalg.norm(d);points.append(np.asarray(center)+d*np.asarray(scale)*rng.uniform(.8,1))
            hull=ConvexHull(points);points=np.asarray(points);ts=[]
            for tri in hull.simplices:
                a,b,c=points[tri]
                if np.dot(np.cross(b-a,c-a),a-np.asarray(center))<0:tri=tri[::-1]
                ts.append(tri.tolist())
            shape(name,points,ts)
        if aid.startswith('clutter') and index%3==0:
            # Wooden crates with visible slats and cross supports.
            for z in np.arange(.12,1.31,.24):
                for y in [-.65,.65]:box('wood',[0,y,z],[1.4,.10,.20])
                for x in [-.65,.65]:box('wood',[x,0,z],[.10,1.2,.20])
            for x in [-.45,.45]:box('wood_dark',[x,0,1.30],[.08,1.4,.08])
            for y in [-.52,-.26,0,.26,.52]:box('wood',[0,y,1.26],[1.4,.22,.08])
        elif aid.startswith('clutter') and index%3==1:
            cylinder('bark',[0,0,1.6],.14,3.2)
            for k,(x,y,z) in enumerate([(-.65,0,3.1),(.65,.1,3.4),(0,-.55,3.6),(0,.5,3.9),(0,0,4.3)]):
                crown('foliage_'+str(k%3),[x,y,z],[.95,.9,1.05],100+index*20+k)
        elif aid.startswith('clutter'):
            box('concrete',[0,0,.60],[3,.45,1.2])
            for x in [-1.25,1.25]:box('concrete',[x,0,.15],[.38,.75,.3])
            for x in np.arange(-1.3,1.4,.45):box('concrete_dark',[x,-.229,.65],[.04,.012,1.0])
        elif aid.startswith('canopy'):
            length=2 if aid=='canopy_mild' else 4
            # Corrugated 5 m carport roof clears the tallest bus geometry.
            for y in np.arange(-1.5,1.51,.15):box('roof',[0,y,5.1+(round((y+1.5)/.15)%2)*.025],[length,.16,.035])
            for x in [-length/2+.07,length/2-.07]:
                for y in [-1.42,1.42]:cylinder('steel',[x,y,2.55],.045,5.1,8)
            for y in [-1.4,1.4]:box('steel',[0,y,5.0],[length,.08,.10])
        else:
            # Masonry wall with mortar courses, instead of a featureless slab.
            box('concrete',[0,0,4],[6,.25,8])
            for z in np.arange(.4,8,.4):box('concrete_dark',[0,-.128,z],[6,.012,.018])
            for z in np.arange(.2,8,.4):
                for x in np.arange(-2.8+(int(z/.4)%2)*.3,3,.6):box('concrete_dark',[x,-.128,z],[.018,.012,.4])
        colors={'wood':(.42,.32,.20),'wood_dark':(.25,.19,.12),'bark':(.23,.17,.12),
                'foliage_0':(.20,.28,.13),'foliage_1':(.17,.24,.12),'foliage_2':(.25,.32,.16),
                'concrete':(.46,.46,.42),'concrete_dark':(.30,.30,.27),'roof':(.46,.44,.38),'steel':(.23,.24,.24)}
        result.append(mesh_asset(aid,'distractor',verts,groups,colors,
                                dict(source_uri='repo:tools/synthetic_dataset/scripts/prepare_realism_assets.py#context_assets',provider_author='Wildlife project',
                                     upstream_version='outdoor-context-v2',model_scale=1,template_family=aid),
                                notes='Original static outdoor context mesh; approximate vegetation/masonry/wood, no target class label.'))
    return result


def main():
    folder=TOOL/'assets/manifests'
    for name in ['assets.json','assets.csv']:
        archive=folder/('legacy_primitive_'+name)
        if not archive.exists():shutil.copyfile(folder/name,archive)
    assets=humans()+vehicles()+buses()+terrains()+context_assets()
    write_json(folder/'assets.json',assets)
    fields=['asset_id','category','model_name','source_uri','provider_author','upstream_version','license','download_date','creation_date','checksum','local_path','model_scale','physical_dimensions_m','eligibility','notes']
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(assets)
    atomic_write(folder/'assets.csv',stream.getvalue())
    print('Prepared',len(assets),'pinned assets; legacy files preserved')


if __name__=='__main__':main()
