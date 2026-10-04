"""Preserve native boxes / realized geometry at the pilot's association failure."""
from pathlib import Path
import sys
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/synthetic_dataset/scripts'))
from common import ROOT, TOOL, load_config, write_json
from sampling import Sampler
from gazebo_backend import Gazebo, stamp

cfg=load_config(TOOL/'configs/synthetic_dataset.yaml')
scene=Sampler(cfg,2000,12345).scene(968)

def trace(frame,event,arg):
    if event=='exception' and frame.f_code.co_name=='capture' and 'cannot be associated' in str(arg[1]):
        d=frame.f_locals
        write_json(ROOT/'docs/dataset/evidence/pilot_rejected_scene.json', {
            'scene':scene,'realized_camera':d['actual']['dataset_rig'],'objects':d['objects'],
            'native_candidates':d['candidates'],'scores':d['scores'],'matches':d['matches'],
            'used_candidates':sorted(d['used']),'remaining_objects':sorted(d['remaining']),
            'rgb_timestamp':stamp(d['rgb']),'annotation_timestamp':stamp(d['boxes'])})
        cv2.imwrite(str(ROOT/'docs/dataset/evidence/pilot_rejected_scene.png'),d['image'])
    return trace

with Gazebo(cfg,ROOT/'datasets/pilot_rejected_scene_probe/runtime',headless=True) as g:
    sys.settrace(trace)
    try: g.capture(scene)
    finally: sys.settrace(None)
