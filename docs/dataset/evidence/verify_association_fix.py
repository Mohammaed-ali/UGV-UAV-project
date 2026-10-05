"""Verify the exact failed pilot scene in two independent Gazebo sessions."""
from pathlib import Path
import json
import sys
import cv2

sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/synthetic_dataset/scripts'))
from common import ROOT,TOOL,load_config,write_json,file_hash,canonical,atomic_write
from sampling import Sampler
from gazebo_backend import Gazebo
from check_determinism import metadata_differences
from phase0 import overlay_image

cfg=load_config(TOOL/'configs/synthetic_dataset.yaml');scene=Sampler(cfg,2000,12345).scene(968)
records=[];labels=[];images=[]
for i in range(2):
    with Gazebo(cfg,ROOT/f'datasets/pilot_association_fix/run{i}',headless=True) as g:
        image,label,record=g.capture(scene)
    records.append(json.loads(canonical(record)));labels.append(label)
    atomic_write(ROOT/f'docs/dataset/evidence/pilot_association_fixed_{i}.txt',label)
    path=ROOT/f'docs/dataset/evidence/pilot_association_fixed_{i}.png'
    cv2.imwrite(str(path),image);images.append(file_hash(path))
    record['case']='pilot index 968 association repair'
    cv2.imwrite(str(ROOT/f'docs/dataset/evidence/pilot_association_fixed_overlay_{i}.png'),overlay_image(image.copy(),record))
    del record['case']
    write_json(ROOT/f'docs/dataset/evidence/pilot_association_fixed_{i}.json',record)
errors=metadata_differences(*records)
passed=not errors and labels[0]==labels[1] and len(labels[0].splitlines())==3
write_json(ROOT/'docs/dataset/evidence/pilot_association_fix.json',{
    'status':'PASSED' if passed else 'FAIL','independent_runs':2,'native_boxes':records[0]['native_box_count'],
    'label_rows':len(labels[0].splitlines()),'metadata_errors':errors,'rgb_bytes_identical':images[0]==images[1],
    'yolo_bytes_identical':labels[0]==labels[1],
    'native_bboxes':[o['bbox_px'] for o in records[0]['objects']],
    'ious':[o['annotation_iou'] for o in records[0]['objects']],
    'label_states':[o['label_state'] for o in records[0]['objects']]})
raise SystemExit(0 if passed else 1)
