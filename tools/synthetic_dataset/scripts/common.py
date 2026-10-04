"""Shared configuration and deterministic serialization; no ROS or ML dependency."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[3]
TOOL = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def git_revision(ref='HEAD'):
    return subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', ref], text=True).strip()


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode()
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_json(path, value):
    atomic_write(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def camera_model(source):
    path = ROOT / source
    sensor = ET.parse(path).find('.//sensor[@type="camera"]')
    camera = sensor.find('camera')
    import math
    w, h = int(camera.findtext('image/width')), int(camera.findtext('image/height'))
    hfov = float(camera.findtext('horizontal_fov'))
    f = w / (2 * math.tan(hfov / 2))
    return {'source': source, 'source_sha256': file_hash(path), 'width': w, 'height': h,
            'horizontal_fov': hfov, 'vertical_fov': 2 * math.atan(h / (2 * f)),
            'fx': f, 'fy': f, 'cx': w / 2, 'cy': h / 2,
            'near': float(camera.findtext('clip/near')), 'far': float(camera.findtext('clip/far')),
            'update_rate_hz': float(sensor.findtext('update_rate')),
            'noise': None if sensor.find('.//noise') is None else ET.tostring(sensor.find('.//noise')).decode(),
            'convention': '+X forward, -Y image right, -Z image down; world ENU'}


def load_config(path):
    path = Path(path).resolve()
    cfg = yaml.safe_load(path.read_text())
    cfg['classes'] = yaml.safe_load((path.parent / cfg['class_mapping']).read_text())['classes']
    expected = ['person', 'car', 'truck', 'bus']
    if [c['name'] for c in cfg['classes']] != expected or [c['yolo_id'] for c in cfg['classes']] != list(range(4)):
        raise ValueError('Class order must be person/car/truck/bus with YOLO IDs 0/1/2/3')
    labels = [c['gazebo_label'] for c in cfg['classes']]
    if len(set(labels)) != 4 or any(not 0 < label < 256 for label in labels):
        raise ValueError('Simulator class labels must be unique, non-background uint8 values')
    if set(cfg['split_fractions']) != {'train', 'val', 'test'} or abs(sum(cfg['split_fractions'].values()) - 1) > 1e-9:
        raise ValueError('Train/val/test fractions must sum to one')
    s = cfg['sampling']
    if s['negative_ratio'] < 0 or s['distractor_only_ratio'] < 0 or s['negative_ratio'] + s['distractor_only_ratio'] >= 1:
        raise ValueError('Invalid negative/distractor mixture')
    if cfg['annotation']['method'] != 'native_visible_2d':
        raise ValueError('Only the validated native visible_2d method is enabled')
    cfg['camera'] = camera_model(cfg['camera_source'])
    cfg['assets'] = json.loads((path.parent / cfg['asset_manifest']).read_text())
    for asset in cfg['assets']:
        p = TOOL / asset['local_path']
        if not p.is_file() or file_hash(p) != asset['checksum']:
            raise ValueError('Missing or changed pinned asset: ' + str(p))
    return cfg
