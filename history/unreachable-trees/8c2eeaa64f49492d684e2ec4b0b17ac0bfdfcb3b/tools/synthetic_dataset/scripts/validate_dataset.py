#!/usr/bin/env python3
"""Standalone validator for every image, label, metadata record and split."""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import cv2
import numpy as np
import yaml
from common import file_hash, canonical, write_json
from storage import paths, complete, statistics


def finite_tree(value):
    if isinstance(value,float) and not math.isfinite(value): return False
    if isinstance(value,dict): return all(finite_tree(v) for v in value.values())
    if isinstance(value,list): return all(finite_tree(v) for v in value)
    return True


def validate(root):
    root=Path(root);errors=[];warnings=[];records=[];hashes={};frame_ids=set();scene_splits={};scenario_hashes=set()
    try:
        cfg=yaml.safe_load((root/'manifests/generation_config.yaml').read_text());manifest=json.loads((root/'manifest.json').read_text())
        assets={a['asset_id']:a for a in json.loads((root/'manifests/assets.json').read_text())}
        data=yaml.safe_load((root/'data.yaml').read_text())
        if data['names']!={0:'person',1:'car',2:'truck',3:'bus'}: errors.append('data.yaml class mapping invalid')
        if not (root/'data.yaml').is_file(): errors.append('Missing data.yaml')
    except (OSError,ValueError,KeyError) as e:
        return {'status':'FAIL','errors':['Cannot read manifest/config: '+str(e)],'warnings':[]}
    expected=set()
    for split in ('train','val','test'):
        try:
            split_records=[json.loads(line) for line in (root/'metadata'/(split+'.jsonl')).read_text().splitlines()]
        except (OSError,ValueError) as e: errors.append(f'{split}: invalid JSONL: {e}');continue
        for r in split_records:
            fid=r.get('frame_id','');prefix=f'{split}/{fid}: '
            try:
                if not finite_tree(r): errors.append(prefix+'NaN/Inf metadata')
                if r['split']!=split: errors.append(prefix+'Wrong metadata split')
                if fid in frame_ids: errors.append(prefix+'Duplicate frame ID')
                frame_ids.add(fid)
                for key in ('scene_id','scene_family'):
                    old=scene_splits.setdefault((key,r[key]),split)
                    if old!=split: errors.append(prefix+'Scene split leakage')
                if r['scenario_sha256'] in scenario_hashes: errors.append(prefix+'Duplicate scene specification')
                scenario_hashes.add(r['scenario_sha256'])
                p=paths(root,r);expected.add((split,fid))
                if not complete(root,r): errors.append(prefix+'Incomplete/corrupt commit or file hashes')
                if json.loads(p['metadata'].read_text())!=r: errors.append(prefix+'Per-frame and JSONL metadata disagree')
                image=cv2.imread(str(p['image']))
                if image is None: errors.append(prefix+'Undecodable image');continue
                if image.shape[:2]!=(cfg['camera']['height'],cfg['camera']['width']): errors.append(prefix+'Image dimensions incorrect')
                if p['image'].stat().st_size==0 or p['metadata'].stat().st_size==0: errors.append(prefix+'Zero-byte image/metadata')
                h=file_hash(p['image'])
                if h in hashes: errors.append(prefix+'Duplicate image SHA256 with '+hashes[h])
                hashes[h]=fid
                lines=p['label'].read_text().splitlines();labelled=[o for o in r['objects'] if o['label_state']=='labelled']
                if len(lines)!=len(labelled): errors.append(prefix+'Label/metadata object count mismatch')
                if r['kind'] in ('negative','distractor_only') and (lines or r['objects']): errors.append(prefix+'Nonempty negative/distractor-only targets')
                if r['kind']=='negative' and r['distractors']: errors.append(prefix+'Negative contains distractors')
                for line,o in zip(lines,labelled):
                    values=line.split()
                    if len(values)!=5: errors.append(prefix+'Malformed YOLO row');continue
                    cls=int(values[0]);x,y,w,h=map(float,values[1:])
                    if cls not in range(4) or cls!=o['class_id']: errors.append(prefix+'Invalid or wrong YOLO class')
                    if not all(math.isfinite(v) for v in (x,y,w,h)) or not (0<=x<=1 and 0<=y<=1 and 0<w<=1 and 0<h<=1): errors.append(prefix+'Invalid normalized coordinates')
                    if min(x-w/2,y-h/2)<-1e-8 or max(x+w/2,y+h/2)>1+1e-8: errors.append(prefix+'Box exceeds image')
                    if not np.allclose([x,y,w,h],o['yolo_bbox'],atol=1e-8,rtol=0): errors.append(prefix+'YOLO and metadata disagree')
                    b=o['bbox_px']
                    if not (0<=b[0]<b[2]<=cfg['camera']['width'] and 0<=b[1]<b[3]<=cfg['camera']['height']): errors.append(prefix+'Invalid clipped pixel bbox')
                for o in r['objects']:
                    if o['label_state'] not in ('labelled','ignored_tiny','ignored_outside','ignored_occluded','ignored_invalid','ignored_other'): errors.append(prefix+'Unaccounted target')
                    if o['label_state']!='labelled' and not o['ignored_reason']: errors.append(prefix+'Missing ignored reason')
                    if split not in assets[o['asset_id']]['eligibility']: errors.append(prefix+'Heldout asset leakage')
                    cls=cfg['classes'][o['class_id']]
                    if o['class_name']!=cls['name'] or o['gazebo_label']!=cls['gazebo_label']: errors.append(prefix+'Simulator/YOLO mapping disagrees')
                    if np.linalg.norm(np.asarray(o['pose']['position'])-o['commanded_pose']['position'])>cfg['capture']['pose_tolerance_m']: errors.append(prefix+'Actual target pose differs')
                if split not in assets[r['background']['asset_id']]['eligibility']: errors.append(prefix+'Heldout background leakage')
                if r['timestamp_delta_s']>cfg['capture']['sync_tolerance_s'] or r['simulation_timestamp']<r['scene_readback_timestamp']+cfg['capture']['settling_frames']/cfg['camera']['update_rate_hz']-1e-8: errors.append(prefix+'Stale/mismatched capture')
                records.append(r)
            except (OSError,ValueError,KeyError,TypeError,IndexError) as e: errors.append(prefix+'Invalid record: '+str(e))
    actual_counts={}
    for kind,folder,suffix in [('images','images','.png'),('labels','labels','.txt'),('metadata','metadata/frames','.json')]:
        actual={(p.parent.name,p.stem) for p in (root/folder).glob('*/*'+suffix)}
        actual_counts[kind]=len(actual)
        if actual!=expected: errors.append(f'{kind}: missing/orphaned file IDs: {sorted(actual.symmetric_difference(expected))[:10]}')
    statuses=list((root/'.state').glob('*.json'));actual_counts['status']=len(statuses)
    scenarios=list(csv.DictReader((root/'manifests/scenarios.csv').open()));actual_counts['scenario_manifest']=len(scenarios)
    actual_counts['jsonl_metadata']=len(records)
    if set(r['frame_id'] for r in scenarios)!=frame_ids or len(scenarios)!=len(frame_ids): errors.append('Scenario manifest IDs or duplicate entries disagree')
    if any(n!=manifest['expected_count'] for n in actual_counts.values()) or manifest['accepted_samples']!=len(records): errors.append('Expected/image/label/metadata/manifest counts disagree')
    stats=statistics(records)
    if set(stats['labelled_per_class'])!=set(c['name'] for c in cfg['classes']): errors.append('All four exported classes are not represented')
    for factor,required in [('altitude',cfg['sampling']['altitude_buckets_m']),('off_nadir',cfg['sampling']['off_nadir_buckets_deg']),('lighting',list(cfg['lighting'])),('background',cfg['backgrounds'])]:
        if set(map(str,required))-set(stats['marginals'][factor]): errors.append(f'Missing {factor} coverage')
    if {'near','medium','far','edge'}-set(stats['cross_tables']['distance_x_class']): errors.append('Missing distance/edge coverage')
    try:
        index=json.loads((root/'manifests/files.sha256.json').read_text())
        if file_hash(root/'manifests/files.sha256.json')!=manifest['file_index_sha256']: errors.append('File index changed')
        for item in index:
            relative=Path(item['path'])
            if relative.is_absolute() or '..' in relative.parts: errors.append('Unsafe file index path');continue
            if file_hash(root/relative)!=item['sha256']: errors.append('File index hash mismatch: '+str(relative))
        if len({i['path'] for i in index})!=len(index): errors.append('Duplicate file index paths')
        if stats!=json.loads((root/'statistics.json').read_text()): errors.append('Statistics do not reproduce from metadata')
    except (OSError,ValueError,KeyError) as e: errors.append('Invalid file index/statistics: '+str(e))
    warnings.append('KNOWN LIMITATION: Person variants share one template; person model holdout is not claimed.')
    heldout=[a['asset_id'] for a in assets.values() if a['held_out']]
    used_test={o['asset_id'] for r in records if r['split']=='test' for o in r['objects']}|{r['background']['asset_id'] for r in records if r['split']=='test'}
    missing=set(heldout)-used_test
    if missing: errors.append('Configured heldout assets absent from test: '+str(sorted(missing)))
    return {'status':'PASSED' if not errors else 'FAIL','errors':errors,'warnings':warnings,
            'counts':actual_counts,'frames_per_split':stats['frames_per_split'],'heldout_assets_used':sorted(used_test&set(heldout)),
            'duplicate_frame_ids':len(records)-len(frame_ids),'unique_image_hashes':len(hashes),
            'coverage':stats['marginals'],'leakage_checks':['frame IDs','image SHA256','scene IDs/families','scenario specification replay','heldout assets']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dataset');p.add_argument('--report')
    args=p.parse_args();r=validate(args.dataset)
    if args.report: write_json(args.report,r)
    print(json.dumps(r,indent=2));return 0 if r['status']=='PASSED' else 1


if __name__=='__main__': raise SystemExit(main())
