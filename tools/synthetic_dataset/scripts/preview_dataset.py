#!/usr/bin/env python3
"""Seeded representative overlays, contact sheets and independent projection audit."""
import argparse
from collections import defaultdict
import json
import random
from pathlib import Path
import cv2
import numpy as np
from common import atomic_write, write_json, file_hash, git_revision
from storage import committed_records, distribution
from geometry import clip_box, iou, rotation, project_points


def fresh_projection(asset, obj, camera):
    """Reproject manifest geometry / realized poses without using stored boxes."""
    points=np.asarray(asset['geometry_points'],float)
    points=points@rotation(obj['pose']['quaternion']).T+obj['pose']['position']
    pixels=project_points(points,camera,camera['model'])
    if pixels is None: return None
    return [float(pixels[:,0].min()),float(pixels[:,1].min()),
            float(pixels[:,0].max()),float(pixels[:,1].max())]


def verify_projection(stored, fresh):
    if (stored is None)!=(fresh is None): raise ValueError('Fresh projection visibility differs')
    if stored is None: return 0.
    delta=float(np.max(np.abs(np.asarray(stored)-fresh)))
    if not np.isfinite(delta) or delta>1e-8: raise ValueError('Stored secondary box differs from fresh realized-pose projection')
    return delta


def factors(r):
    values=[f"altitude_{r['camera']['nominal_altitude_m']}",f"angle_{r['camera']['nominal_off_nadir_deg']}",
            'lighting_'+r['lighting']['family'],'background_'+r['background']['family'],r['kind']]
    if len(r['objects'])>1: values.append('multi_object')
    if r['lighting']['family']=='shadow': values.append('shadows')
    if r['occlusion_requested']!='none': values.append('occlusion')
    for o in r['objects']:
        values.extend(['class_'+o['class_name'],'distance_'+o['distance_category']])
        if o['truncated']: values.append('truncation')
    return set(values)


def representative(records,count,seed=12345):
    rng=random.Random(seed);shuffled=list(records);rng.shuffle(shuffled)
    uncovered=set().union(*(factors(r) for r in records)) if records else set()
    chosen=[]
    while uncovered and len(chosen)<count:
        r=max(shuffled,key=lambda x:len(factors(x)&uncovered));chosen.append(r);shuffled.remove(r);uncovered-=factors(r)
    chosen.extend(shuffled[:max(0,count-len(chosen))]);return chosen


def overlay(root,r,secondary=False):
    image=cv2.imread(str(Path(root)/'images'/r['split']/(r['frame_id']+'.png')))
    cam=r['camera']['model']
    for o in r['objects']:
        if secondary:
            b=clip_box(o['secondary_bbox_px'],cam)
            if b: cv2.rectangle(image,tuple(map(int,b[:2])),tuple(map(int,b[2:])),(255,100,20),1)
        b=o['bbox_px']
        if not b: continue
        color=(40,235,50) if o['label_state']=='labelled' else (0,165,255)
        cv2.rectangle(image,tuple(map(int,b[:2])),tuple(map(int,b[2:])),color,1)
        text=f"{o['class_name']} {o['distance_category']}"+(f" {o['label_state']}" if o['label_state']!='labelled' else '')+(f" IoU {o['annotation_iou']:.2f}" if secondary else '')
        cv2.putText(image,text,(int(b[0]),max(30,int(b[1])-3)),cv2.FONT_HERSHEY_SIMPLEX,.32,(255,255,255),1,cv2.LINE_AA)
    cv2.rectangle(image,(0,0),(cam['width'],24),(20,20,20),-1)
    text=f"#{r['index']} {r['split']} {r['camera']['nominal_altitude_m']}m {r['camera']['nominal_off_nadir_deg']}deg {r['lighting']['family']} {r['background']['family']} {r['kind']}"
    cv2.putText(image,text,(4,16),cv2.FONT_HERSHEY_SIMPLEX,.37,(255,255,255),1,cv2.LINE_AA)
    return image


def save_image(path,image):
    ok,data=cv2.imencode(Path(path).suffix,image);assert ok;atomic_write(path,data.tobytes())


def sheet(root,records,path,secondary=False):
    if not records: return
    w,h=320,240;cols=4;rows=(len(records)+cols-1)//cols
    canvas=np.zeros((rows*h,cols*w,3),np.uint8)
    for i,r in enumerate(records):
        thumbnail=cv2.resize(overlay(root,r,secondary),(w,h));y,x=divmod(i,cols);canvas[y*h:(y+1)*h,x*w:(x+1)*w]=thumbnail
    save_image(path,canvas)


def preview(root,count=100,audit_count=300):
    root=Path(root);records=committed_records(root);selected=representative(records,min(count,len(records)))
    asset_path=root/'manifests/assets.json'
    assets={a['asset_id']:a for a in json.loads(asset_path.read_text())}
    groups=defaultdict(list)
    for r in records:
        for factor in factors(r): groups[factor].append(r)
    for r in selected: save_image(root/'qa/previews'/(r['frame_id']+'.jpg'),overlay(root,r))
    for i in range(0,len(selected),25): sheet(root,selected[i:i+25],root/'qa/review_pages'/f'{i//25+1:03d}.jpg')
    for name,group in sorted(groups.items()): sheet(root,representative(group,min(12,len(group))),root/'qa/contact_sheets'/(name+'.jpg'))
    audit=representative(records,min(audit_count,len(records)),54321);observations=[];projection_deltas=[]
    ignored=defaultdict(int);association_checks=[]
    for r in audit:
        projected={o['instance_id']:fresh_projection(assets[o['asset_id']],o,r['camera']) for o in r['objects']}
        for o in r['objects']:
            fresh=projected[o['instance_id']]
            projection_deltas.append(verify_projection(o['secondary_bbox_px'],fresh))
            if o['label_state']!='labelled': ignored[o['label_state']]+=1
            if o['bbox_px']:
                score=iou(o['bbox_px'],clip_box(fresh,r['camera']['model']))
                if abs(score-o['annotation_iou'])>1e-10: raise ValueError('Stored IoU does not reproduce')
                alternative=max([iou(o['bbox_px'],clip_box(projected[other['instance_id']],r['camera']['model']))
                                 for other in r['objects'] if other['class_id']==o['class_id'] and other['instance_id']!=o['instance_id']],default=0.)
                association_checks.append({'frame_id':r['frame_id'],'instance_id':o['instance_id'],
                                           'assigned_iou':score,'best_same_class_alternative_iou':alternative})
                observations.append({'frame_id':r['frame_id'],'instance_id':o['instance_id'],'class':o['class_name'],
                                     'altitude':r['camera']['nominal_altitude_m'],'angle':r['camera']['nominal_off_nadir_deg'],
                                     'background':r['background']['family'],'lighting':r['lighting']['family'],
                                     'distance':o['distance_category'],'label_state':o['label_state'],
                                     'iou':score,'truncated':o['truncated'],'occlusion_requested':r['occlusion_requested']})
    all_factors=sorted(set().union(*(factors(r) for r in audit)))
    summary={'audited_frames':len(audit),'matched_instances':len(observations),'method':'native visible box vs independent realized primitive silhouette projection',
             'iou':distribution([o['iou'] for o in observations]),'coverage':all_factors,
             'fresh_reprojection':{'status':'PASSED','objects_checked':len(projection_deltas),
                                  'max_stored_box_delta_px':max(projection_deltas,default=0.),
                                  'asset_manifest_sha256':file_hash(asset_path),'audit_code_sha256':file_hash(__file__),
                                  'audit_revision':git_revision()},
             'ignored_objects':dict(ignored),
             'same_class_association':{'checked_instances':len(association_checks),
                                      'close_or_better_alternatives':[o for o in association_checks if o['best_same_class_alternative_iou']>0 and o['assigned_iou']-o['best_same_class_alternative_iou']<.01],
                                      'note':'Spatial alternative check; class-only native labels still do not provide an independent instance-ID oracle.'},
             'by_class':{},'by_altitude':{},'by_angle':{},'observations':observations,
             'definition_note':'Visible boxes can disagree with full projected silhouettes under occlusion, clipping and pixel quantization; IoU is not a visibility fraction.'}
    for key in ('class','altitude','angle','lighting','background','distance','label_state'):
        grouped=defaultdict(list)
        for o in observations: grouped[str(o[key])].append(o['iou'])
        summary['by_'+key]={k:distribution(v) for k,v in grouped.items()}
    write_json(root/'qa/annotation_audit.json',summary)
    score=lambda r:min([o['annotation_iou'] for o in r['objects'] if o['bbox_px']],default=1)
    worst=sorted((r for r in audit if any(o['bbox_px'] for o in r['objects'])),key=score)[:50]
    for r in worst: save_image(root/'qa/low_iou'/(r['frame_id']+'.png'),overlay(root,r,True))
    sheet(root,worst,root/'qa/low_iou/contact_sheet.jpg',True)
    sheet(root,selected[:24],root/'qa/representative.jpg')
    write_json(root/'qa/preview_index.json',{'previews':[r['frame_id'] for r in selected],
                                            'sheets':{k:[r['frame_id'] for r in representative(v,min(12,len(v)))] for k,v in groups.items()},
                                            'audit_frames':[r['frame_id'] for r in audit],'lowest_iou_frames':[r['frame_id'] for r in worst]})
    return {k:v for k,v in summary.items() if k!='observations'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dataset');p.add_argument('--count',type=int,default=100);p.add_argument('--audit-count',type=int,default=300)
    args=p.parse_args();print(json.dumps(preview(args.dataset,args.count,args.audit_count),indent=2))


if __name__=='__main__': main()
