#!/usr/bin/env python3
"""Reproduce pixel feasibility, controlled alignment and a headless benchmark.
Creates evidence only; does not open acceptance gates without visual review."""
import argparse
from copy import deepcopy
import csv
import io
import math
from pathlib import Path
import subprocess
import time
import cv2
import numpy as np
from common import TOOL, ROOT, load_config, write_json, atomic_write, file_hash, git_revision
from sampling import Sampler, projected_geometry
from geometry import quaternion, clip_box
from gazebo_backend import Gazebo
from preview_dataset import save_image, overlay, sheet
from storage import distribution


def pixel_table(cfg,output):
    rows=[];cam=cfg['camera']
    for cls in cfg['classes']:
        asset=next(a for a in cfg['assets'] if a['category']==cls['name'])
        for h in sorted(set(cfg['sampling']['altitude_buckets_m']+[13,18])):
            for angle in cfg['sampling']['off_nadir_buckets_deg']:
                pose={'position':[0,0,h],'quaternion':quaternion(0,math.pi/2-math.radians(angle),0)}
                from geometry import ground_ray, footprint, footprint_radius
                center=ground_ray(cam['cx'],cam['cy'],pose,cam)[:2];poly=footprint(pose,cam)
                for band,(low,high) in cfg['sampling']['distance_bands'].items():
                    sizes=[]
                    for direction_angle in np.linspace(0,2*math.pi,8,endpoint=False):
                        direction=np.array([math.cos(direction_angle),math.sin(direction_angle)])
                        xy=center+direction*footprint_radius(center,direction,poly,pose,cam)*(low+high)/2
                        for yaw in (0,45,90,135):
                            obj={'position':[float(xy[0]),float(xy[1]),0],'quaternion':quaternion(0,0,math.radians(yaw))}
                            b=clip_box(projected_geometry(asset,obj,pose,cam),cam)
                            if b: sizes.append([b[2]-b[0],b[3]-b[1],(b[2]-b[0])*(b[3]-b[1])])
                    a=np.asarray(sizes)
                    rows.append({'class':cls['name'],'asset_id':asset['asset_id'],'altitude_m':h,'off_nadir_deg':angle,'distance':band,
                                 'min_width_px':float(a[:,0].min()),'mean_width_px':float(a[:,0].mean()),
                                 'min_height_px':float(a[:,1].min()),'mean_height_px':float(a[:,1].mean()),
                                 'min_area_px':float(a[:,2].min()),'mean_area_px':float(a[:,2].mean()),
                                 'below_min_box':bool(np.any(a[:,:2]<cfg['annotation']['min_box_px'])),
                                 'policy':'retain difficult factor levels; native visible boxes below threshold become ignored_tiny; normal placements must fit'} )
    stream=io.StringIO();w=csv.DictWriter(stream,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    atomic_write(output/'pixel_size_feasibility.csv',stream.getvalue());return rows


def controlled(cfg,sampler):
    base=next(sampler.scene(i) for i in range(200) if sampler.scene(i)['kind']=='positive')
    base['background']={'family':'grass','asset_id':'grass_0','zone_x_m':0,'texture_rotation_deg':0,'texture_scale':1,'texture_offset':[0,0]}
    base['lighting'].update(family='noon',direction=[-.3,.2,-1],color=[1,1,.96],intensity=1.1)
    base['distractors']=[];base['occlusion_requested']='none';base['objects']=[]
    base['camera'].update(position=[0,0,20],quaternion=quaternion(0,math.pi/2,0),nominal_altitude_m=20,altitude_agl_m=20,
                          roll=0,pitch=math.pi/2,yaw=0,nominal_off_nadir_deg=0,actual_off_nadir_deg=0,viewing_azimuth_deg=0)
    scenes=[]
    for cls in cfg['classes']:
        asset=next(a for a in cfg['assets'] if a['category']==cls['name'])
        template=deepcopy(next(o for i in range(200) for o in sampler.scene(i)['objects'] if o['class_name']==cls['name']))
        template.update(instance_id=f"pool_{asset['asset_id']}_0",asset_id=asset['asset_id'],yaw_deg=0,physical_dimensions_m=asset['physical_dimensions_m'],
                        pose={'position':[0,0,0],'quaternion':[0,0,0,1]})
        for case,xy in [('centered',(0,0)),('near',(0,3)),('far',(0,18)),('edge',(0,22.8)),('partial_occlusion',(0,0))]:
            scene=deepcopy(base);scene['case']=case+'_'+cls['name'];scene['frame_id']=scene['case'];scene['objects']=[deepcopy(template)]
            scene['objects'][0]['pose']['position']=[*xy,0];scene['objects'][0]['distance_category']='edge' if case=='edge' else 'far' if case=='far' else 'near'
            if case=='partial_occlusion':
                offset=1+asset['physical_dimensions_m'][0]*.25
                scene['distractors']=[{'instance_id':'canopy_mild','pose':{'position':[offset,0,0],'quaternion':[0,0,0,1]}}];scene['occlusion_requested']='mild'
            scenes.append(scene)
    multiple=deepcopy(base);multiple['case']='multiple_all_classes';multiple['frame_id']=multiple['case'];multiple['camera'].update(position=[0,0,30],nominal_altitude_m=30,altitude_agl_m=30)
    for cls,xy in zip(cfg['classes'],[(-8,-8),(-8,8),(8,-8),(8,8)]):
        obj=deepcopy(next(s['objects'][0] for s in scenes if s['case']=='centered_'+cls['name']));obj['pose']['position']=[*xy,0];multiple['objects'].append(obj)
    scenes.append(multiple)
    for i,scene in enumerate(scenes): scene['index']=i;scene['planned_target_count']=len(scene['objects']);scene['placement_shortfall']=0
    return scenes


def process_metrics(pgid):
    output=subprocess.check_output(['ps','-eo','pid,pgid,pcpu,rss,comm','--no-headers'],text=True)
    items=[]
    for line in output.splitlines():
        p=line.split()
        if int(p[1])==pgid: items.append({'pid':int(p[0]),'cpu_percent_lifetime':float(p[2]),'rss_kib':int(p[3]),'command':p[4]})
    return items


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',default=str(TOOL/'configs/synthetic_dataset.yaml'))
    p.add_argument('--output',default=str(ROOT/'docs/dataset/evidence/phase0'));p.add_argument('--benchmark-count',type=int,default=60)
    args=p.parse_args();cfg=load_config(args.config);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    pixel=pixel_table(cfg,out);sampler=Sampler(cfg,200,12345);alignment=[];benchmark=[];process=[]
    with Gazebo(cfg,out/'runtime',True) as g:
        print('Controlled alignment...',flush=True)
        for scene in controlled(cfg,sampler):
            image,label,meta=g.capture(scene)
            save_image(out/'alignment/images'/meta['split']/(meta['frame_id']+'.png'),image)
            save_image(out/'alignment/overlays'/(meta['frame_id']+'.png'),overlay_image(image,meta))
            write_json(out/'alignment/metadata'/(meta['frame_id']+'.json'),meta)
            atomic_write(out/'alignment/labels'/(meta['frame_id']+'.txt'),label)
            ok=all(o['bbox_px'] is not None for o in meta['objects'])
            alignment.append({'case':scene['case'],'status':'PASSED' if ok else 'FAIL','native_boxes':meta['native_box_count'],
                              'classes':[o['class_name'] for o in meta['objects']],'ious':[o['annotation_iou'] for o in meta['objects']],
                              'truncated':[o['truncated'] for o in meta['objects']], 'timestamp_delta_s':meta['timestamp_delta_s']})
        t=time.monotonic();bytes_written=0
        print('Representative single-generator benchmark...',flush=True)
        for i in range(args.benchmark_count):
            scene=sampler.scene(i);start=time.monotonic();image,label,meta=g.capture(scene)
            file=out/'benchmark'/f'{i:04d}.png';save_image(file,image);bytes_written+=file.stat().st_size
            benchmark.append({'index':i,'seconds':time.monotonic()-start,'image_bytes':file.stat().st_size})
            if i%10==0: process.extend(process_metrics(g.process.pid))
        duration=time.monotonic()-t
        metrics={'attempted_frames':args.benchmark_count,'accepted_frames':args.benchmark_count,
                 'elapsed_s':duration,'accepted_frames_per_minute':args.benchmark_count/duration*60,
                 'attempted_frames_per_minute':args.benchmark_count/duration*60,'average_image_bytes':bytes_written/args.benchmark_count,
                 'disk_write_bytes_per_second':bytes_written/duration,'process_metrics':process,'samples':benchmark,
                 'settings':'single generator; 640x480/10 Hz sensors; shadows; 1-8 targets and representative clutter; finite RTF '+str(cfg['world']['real_time_factor']),
                 'estimated_10000_seconds':10000*duration/args.benchmark_count,'estimated_10000_image_bytes':10000*bytes_written/args.benchmark_count}
    write_json(out/'benchmark.json',metrics);write_json(out/'alignment.json',{'status':'PASSED' if all(a['status']=='PASSED' for a in alignment) else 'FAIL','cases':alignment})
    rows=[]
    for f in sorted((out/'alignment/overlays').glob('*.png')):
        rows.append(cv2.resize(cv2.imread(str(f)),(320,240)))
    canvas=np.zeros((((len(rows)+3)//4)*240,1280,3),np.uint8)
    for i,im in enumerate(rows): y,x=divmod(i,4);canvas[y*240:(y+1)*240,x*320:(x+1)*320]=im
    save_image(out/'alignment/contact_sheet.jpg',canvas)
    report={'status':'PARTIALLY VALIDATED','programmatic_alignment':'PASSED' if all(a['status']=='PASSED' for a in alignment) else 'FAIL',
            'visual_inspection':'NOT TESTED','gazebo_version':subprocess.check_output(['gz','sim','--versions'],text=True).strip(),
            'headless_command':'gz sim -s -r --headless-rendering -v 2 <generated-world.sdf>',
            'camera_sha256':cfg['camera']['source_sha256'],'asset_manifest_sha256':file_hash(TOOL/'assets/manifests/assets.json'),
            'generator_git_commit':git_revision(),'pixel_cells':len(pixel),'flagged_small_cells':sum(r['below_min_box'] for r in pixel),
            'benchmark':metrics,'camera':cfg['camera']}
    write_json(out/'report.json',report)
    print({k:v for k,v in report.items() if k not in ('benchmark','camera')},flush=True)


def overlay_image(image,meta):
    for o in meta['objects']:
        b=o['bbox_px'];secondary=clip_box(o['secondary_bbox_px'],meta['camera']['model'])
        if secondary: cv2.rectangle(image,tuple(map(int,secondary[:2])),tuple(map(int,secondary[2:])),(255,100,20),1)
        if b:
            cv2.rectangle(image,tuple(map(int,b[:2])),tuple(map(int,b[2:])),(40,235,50),1)
            cv2.putText(image,f"{o['class_name']} {o['annotation_iou']:.2f}",(int(b[0]),max(40,int(b[1])-2)),cv2.FONT_HERSHEY_SIMPLEX,.4,(255,255,255),1)
    cv2.putText(image,meta['case'],(6,20),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
    return image


if __name__=='__main__': main()
