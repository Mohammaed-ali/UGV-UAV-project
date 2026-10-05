"""Measured dataset distributions, ignored targets, pose/timing and disk cost."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/synthetic_dataset/scripts'))
from common import write_json, file_hash
from storage import committed_records, statistics, distribution

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('dataset'); p.add_argument('report',nargs='?');p.add_argument('--output');args=p.parse_args()
args.report=args.report or args.output
if not args.report:p.error('report path or --output is required')
root = Path(args.dataset); records = committed_records(root)
manifest = json.loads((root / 'manifest.json').read_text())
stats = statistics(records)
assets = {a['asset_id']: a for a in json.loads((root / 'manifests/assets.json').read_text())}
usage = {s: Counter() for s in ('train', 'val', 'test')}
wall = Counter(); realized_position_deltas = []; realized_quaternion_deltas = []
all_ignored = []; ignored = []; distances = Counter(); same_class_frames = 0
for r in records:
    usage[r['split']][r['background']['asset_id']] += 1
    wall[r['lighting']['family'] + ('_with_wall' if any(d['instance_id']=='shadow_wall' for d in r['distractors']) else '_without_wall')] += 1
    names = [o['class_name'] for o in r['objects']]
    same_class_frames += len(names) != len(set(names))
    if r['kind']=='positive' and not any(o['label_state']=='labelled' for o in r['objects']): all_ignored.append(r['frame_id'])
    pairs = [(r['camera'], r['camera']['commanded_pose'])]
    for o in r['objects']:
        pairs.append((o['pose'], o['commanded_pose'])); usage[r['split']][o['asset_id']] += 1
        distances[o['distance_category']] += 1
        if o['label_state']!='labelled': ignored.append({'frame_id':r['frame_id'], 'instance_id':o['instance_id'], 'class':o['class_name'], 'state':o['label_state'], 'reason':o['ignored_reason']})
    for actual, commanded in pairs:
        realized_position_deltas.append(float(np.linalg.norm(np.asarray(actual['position'])-commanded['position'])))
        q = np.asarray(actual['quaternion']); c = np.asarray(commanded['quaternion'])
        realized_quaternion_deltas.append(float(min(np.linalg.norm(q-c), np.linalg.norm(q+c))))
files = list(root.rglob('*')); sizes = defaultdict(int)
for f in files:
    if f.is_file(): sizes[f.relative_to(root).parts[0]] += f.stat().st_size
image_bytes = [f.stat().st_size for f in root.glob('images/*/*.png')]
elapsed = manifest['last_run_performance']['elapsed_s']
total_instances = sum(distances.values())
report = {'status':'ANALYSIS_COMPLETE', 'dataset':str(root.resolve()),
          'manifest_sha256':file_hash(root/'manifest.json'), 'generator_revision':manifest['generator_git_commit'],
          'frames':len(records), 'statistics':stats, 'intended_positive_frames_without_exported_labels':all_ignored,
          'ignored_objects':ignored, 'same_class_multi_target_frames':same_class_frames,
          'asset_usage_per_split':{s:dict(c) for s,c in usage.items()},
          'heldout_assets':{a['asset_id']:{s:usage[s][a['asset_id']] for s in usage} for a in assets.values() if a['held_out']},
          'distance_instance_percent':{k:100*v/total_instances for k,v in distances.items()},
          'distance_bias_explanation':'Requested distance bands are drawn once and retained across placement retries. Human-instance quotas are explicit. Far/edge targets may be clipped or ignored by configured size/visibility rules; no difficult level is removed or relabelled. Actual labelled coverage is reported separately from all planned/realized objects.',
          'shadow_wall_presence':dict(wall),
          'synchronization':{'max_delta_s':max(r['timestamp_delta_s'] for r in records),
                             'minimum_settling_sim_seconds':min(r['settling_sim_seconds'] for r in records)},
          'actual_vs_commanded':{'max_position_error_m':max(realized_position_deltas),
                                  'max_sign_invariant_quaternion_error':max(realized_quaternion_deltas)},
          'performance':dict(manifest['last_run_performance'], attempted_samples=manifest['attempted_samples'],
                             rejected_samples=manifest['rejected_samples'], rejection_reasons=manifest['rejection_reasons'],
                             attempted_per_minute=manifest['attempted_samples']/elapsed*60,
                             average_image_bytes=sum(image_bytes)/len(image_bytes), image_write_bytes_per_second=sum(image_bytes)/elapsed),
          'disk_bytes_per_folder':dict(sizes), 'total_disk_bytes':sum(sizes.values()),
          'image_bytes_distribution':distribution(image_bytes),
          'estimated_10000_generation_seconds':elapsed/len(records)*10000,
          'estimated_10000_rgb_bytes':sum(image_bytes)/len(records)*10000,
          'estimated_10000_base_dataset_bytes':sum(sizes.values())/len(records)*10000,
          'limitations':['Pinned synthetic assets; consult manifest for actual source/template/fidelity limitations.',
                         'Distance categories use optical-center ground footprint fraction, not absolute slant range; truncation/visibility can change labelled-instance balance.',
                         'Requested occlusion is not measured pixel visibility.',
                         'Shadow wall presence does not measure calibrated shadow fraction.',
                         'CPU resource samples are recorded separately; generation timing includes startup/rendering/per-frame export/shutdown, and excludes aggregate rebuild/validation/QA.']}
write_json(args.report, report)
print(json.dumps({k:report[k] for k in ('frames','performance','total_disk_bytes','distance_instance_percent','shadow_wall_presence','estimated_10000_generation_seconds','estimated_10000_rgb_bytes')}, indent=2))
