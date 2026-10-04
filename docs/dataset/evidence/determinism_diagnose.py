#!/usr/bin/env python3
"""Preserve measured differences for the handoff; this does not accept Gate 4."""
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/synthetic_dataset/scripts'))
from check_determinism import normalized
from common import file_hash, write_json
from storage import committed_records


def diagnose():
    a = ROOT / 'datasets/determinism_a2'
    b = ROOT / 'datasets/determinism_b2'
    ra, rb = committed_records(a), committed_records(b)
    differences = []
    sign_changes = []
    structural = []

    def walk(x, y, path, frame):
        if isinstance(x, dict) and isinstance(y, dict):
            if set(x) != set(y):
                structural.append({'frame': frame, 'path': path, 'reason': 'keys differ'})
            for key in sorted(set(x) & set(y)):
                walk(x[key], y[key], f'{path}.{key}', frame)
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                structural.append({'frame': frame, 'path': path, 'reason': 'length differs'})
                return
            if path.endswith('.quaternion') and len(x) == 4:
                direct = max(abs(i-j) for i, j in zip(x, y))
                opposite = max(abs(i+j) for i, j in zip(x, y))
                if opposite < direct:
                    sign_changes.append({'frame': frame, 'path': path,
                                         'max_sign_invariant_component_difference': opposite})
                    y = [-v for v in y]
            for i, (vx, vy) in enumerate(zip(x, y)):
                walk(vx, vy, f'{path}[{i}]', frame)
        elif x != y:
            if type(x) in (int, float) and type(y) in (int, float):
                differences.append({'frame': frame, 'path': path, 'a': x, 'b': y,
                                    'absolute_difference': abs(x-y)})
            else:
                structural.append({'frame': frame, 'path': path, 'a': x, 'b': y})

    for x, y in zip(ra, rb):
        walk(normalized(x), normalized(y), 'record', x['frame_id'])

    def category(path):
        if '.quaternion[' in path:
            return 'sign_invariant_quaternion_components'
        if '.position[' in path:
            return 'world_position_m'
        if '.secondary_bbox_px[' in path:
            return 'secondary_projection_px'
        if '.annotation_iou' in path:
            return 'derived_iou'
        return 'other_numeric'

    maxima = {}
    counts = Counter()
    for difference in differences:
        key = category(difference['path'])
        counts[key] += 1
        maxima[key] = max(maxima.get(key, 0), difference['absolute_difference'])
    exact_metadata_count = sum(normalized(x) == normalized(y) for x, y in zip(ra, rb))
    labelled_equal = sum((a / 'labels' / x['split'] / (x['frame_id']+'.txt')).read_bytes()
                        == (b / 'labels' / y['split'] / (y['frame_id']+'.txt')).read_bytes()
                        for x, y in zip(ra, rb))
    report = {
        'status': 'DIAGNOSTIC_ONLY_GATE_4_NOT_PASSED',
        'runs': [str(a), str(b)],
        'frames': [len(ra), len(rb)],
        'exact_metadata_equal_frames_excluding_timing': exact_metadata_count,
        'exact_yolo_equal_frames': labelled_equal,
        'exact_scenarios_csv_equal': file_hash(a/'manifests/scenarios.csv') == file_hash(b/'manifests/scenarios.csv'),
        'quaternion_sign_changes': sign_changes,
        'numeric_difference_counts_after_sign_alignment': dict(counts),
        'max_absolute_difference_after_sign_alignment': maxima,
        'structural_or_non_numeric_differences': structural,
        'largest_numeric_differences': sorted(differences, key=lambda d: d['absolute_difference'], reverse=True)[:20],
        'note': 'Quaternion q and -q describe the same rotation. This diagnostic only measures differences; production comparator and its regression tests still need repair. Raw readback metadata remains unchanged.'
    }
    write_json(ROOT/'docs/dataset/evidence/determinism_diagnostic.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in
                      ('quaternion_sign_changes', 'largest_numeric_differences')}, indent=2))


if __name__ == '__main__':
    diagnose()
