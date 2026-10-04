"""Reproduce only the failed crash-test scene; retain all ignored-object evidence."""
import json
from pathlib import Path
import sys
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/synthetic_dataset/scripts'))
from common import ROOT, TOOL, load_config, write_json
from sampling import Sampler
from gazebo_backend import Gazebo

cfg = load_config(TOOL / 'configs/synthetic_dataset.yaml')
scene = Sampler(cfg, 200, 76543).scene(147)
# Only bypass the positive/no-label exception for this diagnostic. Camera,
# target, lighting, clutter and annotation policy are unchanged.
scene['kind'] = 'positive_diagnostic'
with Gazebo(cfg, ROOT / 'datasets/crash_rejected_scene_probe/runtime', headless=True) as gazebo:
    image, labels, metadata = gazebo.capture(scene)
write_json(ROOT / 'docs/dataset/evidence/crash_rejected_scene.json', {
    'purpose': 'Diagnose original seed 76543/index 147; kind guard bypassed only for this probe',
    'metadata': metadata, 'yolo_labels': labels})
cv2.imwrite(str(ROOT / 'docs/dataset/evidence/crash_rejected_scene.png'), image)
print(json.dumps({'objects': metadata['objects'], 'native_box_count': metadata['native_box_count']}, indent=2))
