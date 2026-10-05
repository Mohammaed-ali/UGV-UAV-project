"""Independent low-tail instance identity check: private unique simulator labels.
The production dataset/classes/assets/captures are never modified.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import cv2
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/synthetic_dataset/scripts'))
from common import load_config,TOOL,write_json,file_hash,canonical
from storage import committed_records
from sampling import Sampler
import gazebo_backend as backend

p=argparse.ArgumentParser(description=__doc__);p.add_argument('dataset');args=p.parse_args()
root=Path(args.dataset);index=json.loads((root/'qa/preview_index.json').read_text())
records={r['frame_id']:r for r in committed_records(root)};run=json.loads((root/'.run.json').read_text())
cfg=load_config(TOOL/'configs/synthetic_dataset.yaml');sampler=Sampler(cfg,run['expected_count'],run['seed'])
label_map={};classes=[]
for a in cfg['assets']:
 if a['category'] not in ['person','car','truck','bus']:continue
 base=next(c for c in cfg['classes'] if c['name']==a['category'])
 for slot in range(cfg['world']['pool_copies_per_variant']):
  label=100+len(label_map);name=f"pool_{a['asset_id']}_{slot}";label_map[name]=label
  classes.append(dict(base,gazebo_label=label))
assert max(label_map.values())<256
audit_cfg=deepcopy(cfg);audit_cfg['classes']=classes
original=backend.write_world
def unique_world(c,path):
 original(c,path);tree=ET.parse(path)
 for model in tree.findall('.//world/model'):
  if model.get('name') in label_map:model.find("plugin/label").text=str(label_map[model.get('name')])
 tree.write(path,encoding='utf-8',xml_declaration=True)
backend.write_world=unique_world
observations=[];failed=[]
with backend.Gazebo(audit_cfg,root/'qa/instance_oracle/runtime') as g:
 for fid in index['lowest_iou_frames']:
  reference=records[fid];scene=sampler.scene(reference['index'])
  assert scene['scenario_sha256']==reference['scenario_sha256']
  for o in scene['objects']:o['gazebo_label']=label_map[o['instance_id']]
  image,labels,meta=g.capture(scene)
  differences=[]
  for primary,oracle in zip(reference['objects'],meta['objects']):
   for key in ['instance_id','bbox_px','label_state','yolo_bbox']:
    if primary[key]!=oracle[key]:differences.append({'instance_id':primary['instance_id'],'field':key,'primary':primary[key],'oracle':oracle[key]})
  label_equal=labels==(root/'labels'/reference['split']/(fid+'.txt')).read_text()
  if differences or not label_equal:
   failed.append(fid);cv2.imwrite(str(root/'qa/instance_oracle'/(fid+'.png')),image)
  observations.append({'frame_id':fid,'status':'PASSED' if not differences and label_equal else 'FAIL',
                       'target_count':len(meta['objects']),'differences':differences,'yolo_bytes_identical':label_equal})
  print(fid,observations[-1]['status'],flush=True)
write_json(root/'qa/instance_identity_audit.json',{'status':'PASSED' if not failed else 'FAIL','frames':observations,'failed_frames':failed,
 'method':'Replay the same commanded scenes/assets/camera with a unique uint8 label per model instance. This disambiguates primary class-only native boxes independently of geometry matching.',
 'primary_dataset_unchanged':True,'private_instance_labels':label_map,'primary_asset_manifest_sha256':run['asset_manifest_sha256'],
 'script_sha256':file_hash(__file__),'limitation':'This checks simulator instance association, not real-world annotation or pixel visibility fraction.'})
raise SystemExit(0 if not failed else 1)
