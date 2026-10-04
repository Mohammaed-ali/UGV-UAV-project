"""Atomic per-sample commit markers. Aggregates are rebuilt, never appended."""
from collections import Counter, defaultdict
import csv
import io
import json
from pathlib import Path
import cv2
import numpy as np
import yaml
from common import atomic_write, canonical, digest, file_hash, TOOL, write_json, utc_now


def paths(root,scene):
    base=Path(root);split=scene['split'];fid=scene['frame_id']
    return {'image':base/'images'/split/(fid+'.png'),'label':base/'labels'/split/(fid+'.txt'),
            'metadata':base/'metadata/frames'/split/(fid+'.json'),'status':base/'.state'/(fid+'.json')}


def complete(root,scene):
    p=paths(root,scene)
    try:
        state=json.loads(p['status'].read_text())
        if state['status']!='complete' or state['scenario_sha256']!=scene['scenario_sha256']: return False
        if any(not p[k].is_file() or file_hash(p[k])!=state['sha256'][k] for k in ('image','label','metadata')): return False
        return cv2.imread(str(p['image'])) is not None
    except (OSError,ValueError,KeyError): return False


def commit_sample(root,scene,image,label,metadata):
    p=paths(root,scene);success,data=cv2.imencode('.png',image)
    if not success: raise ValueError('PNG encoding failed')
    # Discard the old marker before repairing files; a killed writer is incomplete.
    if p['status'].exists(): p['status'].unlink()
    atomic_write(p['image'],data.tobytes());atomic_write(p['label'],label);write_json(p['metadata'],metadata)
    write_json(p['status'],{'status':'complete','frame_id':scene['frame_id'],'split':scene['split'],
                           'scenario_sha256':scene['scenario_sha256'],
                           'sha256':{k:file_hash(p[k]) for k in ('image','label','metadata')}})


def committed_records(root):
    root=Path(root);records=[]
    for p in sorted((root/'.state').glob('*.json')):
        state=json.loads(p.read_text());meta=root/'metadata/frames'/state['split']/(state['frame_id']+'.json')
        records.append(json.loads(meta.read_text()))
    return sorted(records,key=lambda r:r['index'])


def distribution(values):
    if not values: return {'count':0}
    x=np.asarray(values,float)
    return {'count':len(values),'min':float(x.min()),'p05':float(np.percentile(x,5)),
            'p25':float(np.percentile(x,25)),'median':float(np.median(x)),
            'p95':float(np.percentile(x,95)),'max':float(x.max()),'mean':float(x.mean())}


def statistics(records):
    stats={'frames':len(records),'frames_per_split':dict(Counter(r['split'] for r in records)),
           'frame_types':dict(Counter(r['kind'] for r in records)),'objects_per_image':dict(Counter(str(len(r['objects'])) for r in records)),
           'marginals':{},'cross_tables':{},'ignored_by_reason':{},'instances_per_class':{},
           'occlusion_requested':dict(Counter(r['occlusion_requested'] for r in records)),
           'placement_shortfall':sum(r['placement_shortfall'] for r in records)}
    factor_functions={'altitude':lambda r:r['camera']['nominal_altitude_m'],
                      'off_nadir':lambda r:r['camera']['nominal_off_nadir_deg'],
                      'lighting':lambda r:r['lighting']['family'],'background':lambda r:r['background']['family']}
    objects=[o for r in records for o in r['objects']]
    for name,fn in factor_functions.items():
        stats['marginals'][name]=dict(Counter(str(fn(r)) for r in records));table=defaultdict(Counter)
        for r in records:
            for o in r['objects']: table[str(fn(r))][o['class_name']]+=1
        stats['cross_tables'][name+'_x_class']={k:dict(v) for k,v in table.items()}
    table=defaultdict(Counter)
    for o in objects: table[o['distance_category']][o['class_name']]+=1
    stats['cross_tables']['distance_x_class']={k:dict(v) for k,v in table.items()}
    stats['instances_per_class']=dict(Counter(o['class_name'] for o in objects))
    stats['labelled_per_class']=dict(Counter(o['class_name'] for o in objects if o['label_state']=='labelled'))
    stats['ignored_by_reason']=dict(Counter(o['label_state'] for o in objects if o['label_state']!='labelled'))
    stats['truncated_objects']=sum(o['truncated'] for o in objects)
    widths=[o['bbox_px'][2]-o['bbox_px'][0] for o in objects if o['label_state']=='labelled']
    heights=[o['bbox_px'][3]-o['bbox_px'][1] for o in objects if o['label_state']=='labelled']
    areas=[w*h for w,h in zip(widths,heights)]
    for name,v in [('bbox_width_px',widths),('bbox_height_px',heights),('bbox_area_px',areas),('iou',[o['annotation_iou'] for o in objects if o['bbox_px']])]: stats[name]=distribution(v)
    stats['object_size_counts']={'small_under_32_squared':sum(a<32**2 for a in areas),
                                 'medium_32_to_96_squared':sum(32**2<=a<96**2 for a in areas),
                                 'large_96_squared_and_above':sum(a>=96**2 for a in areas)}
    for name,values in [('object_yaw',[o['yaw_deg'] for o in objects]),('camera_yaw',[r['camera']['viewing_azimuth_deg'] for r in records])]:
        stats[name+'_histogram_30deg']=np.histogram(values,bins=np.arange(0,361,30))[0].tolist()
    return stats


def summarize(root,cfg,run):
    root=Path(root);records=committed_records(root)
    for split in cfg['split_fractions']:
        atomic_write(root/'metadata'/(split+'.jsonl'),''.join(canonical(r)+'\n' for r in records if r['split']==split))
    stats=statistics(records);write_json(root/'statistics.json',stats)
    stream=io.StringIO();fields=['frame_id','scene_id','scene_family','scene_seed','split','scenario_sha256']
    w=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(records)
    atomic_write(root/'manifests/scenarios.csv',stream.getvalue())
    atomic_write(root/'data.yaml',yaml.safe_dump({'path':str(root.resolve()),'train':'images/train','val':'images/val','test':'images/test',
                                               'names':{c['yolo_id']:c['name'] for c in cfg['classes']}},sort_keys=False))
    file_index=[]
    for r in records:
        p=paths(root,r);state=json.loads(p['status'].read_text())
        for k in ('image','label','metadata'): file_index.append({'path':str(p[k].relative_to(root)),'sha256':state['sha256'][k]})
    for p in sorted((root/'manifests').glob('*')):
        if p.is_file() and p.name!='files.sha256.json': file_index.append({'path':str(p.relative_to(root)),'sha256':file_hash(p)})
    for name in ('statistics.json','data.yaml'): file_index.append({'path':name,'sha256':file_hash(root/name)})
    write_json(root/'manifests/files.sha256.json',sorted(file_index,key=lambda x:x['path']))
    manifest=dict(run);manifest.update(accepted_samples=len(records),completed=len(records)==run['expected_count'],
                                     generation_end=utc_now(),split_counts=stats['frames_per_split'],class_counts=stats['instances_per_class'],
                                     factor_distributions=stats['marginals'],asset_manifest='manifests/assets.json',
                                     file_index_sha256=file_hash(root/'manifests/files.sha256.json'))
    write_json(root/'manifest.json',manifest)
    atomic_write(root/'README.md','# Gazebo aerial detection dataset\n\nSynthetic Gazebo imagery is not equivalent to real aerial-camera imagery.\n\n'
                 'Classes: 0 person, 1 car, 2 truck, 3 bus. Native visible 2D boxes; fixed V0.4 camera.\n'
                 'See manifest.json, statistics.json and metadata/*.jsonl for provenance and factors.\n'
                 'Original procedural assets are CC0-1.0; human variants share one template.\n'
                 'This dataset establishes no real-world detector accuracy or sim-to-real success.\n')
    return manifest
