#!/usr/bin/env python3
"""Compare independent Gazebo runs. Timing fields are measured, not deterministic."""
import argparse
import json
import math
from pathlib import Path
from common import file_hash, write_json
from storage import committed_records


TIMING_FIELDS = {'simulation_timestamp', 'annotation_timestamp', 'timestamp_delta_s',
                 'scene_readback_timestamp', 'settling_sim_seconds', 'generation_timestamp'}
# Absolute tolerances only, substantially below capture tolerances / one pixel.
# Retained a2/b2 maxima: 1.82e-12 m, 3.33e-16 quaternion, 4.18e-11 px,
# 3.31e-12 IoU. These limits allow numerical readback, never scene variation.
TOLERANCES = {'position_m': 1e-10, 'quaternion_component': 1e-14,
              'secondary_projection_px': 1e-8, 'derived_iou': 1e-9}
CAMERA_KEYS = set('position quaternion roll pitch yaw viewing_azimuth_deg nominal_altitude_m altitude_agl_m ground_reference_z nominal_off_nadir_deg actual_off_nadir_deg'.split())
POSE_KEYS = {'position', 'quaternion'}
SCHEMA = {
    (): set('annotation_method background camera distractors frame_id index kind lighting master_seed native_box_count objects occlusion_requested placement_shortfall planned_target_count scenario_sha256 scene_family scene_id scene_seed split composition_requested person_count_band_requested planned_person_count planned_vehicle_count human_grouping_requested'.split()),
    ('camera',): CAMERA_KEYS | {'commanded_pose', 'model', 'live_camera_info'},
    ('camera', 'commanded_pose'): CAMERA_KEYS,
    ('camera', 'model'): set('convention cx cy far fx fy height horizontal_fov near noise source source_sha256 update_rate_hz vertical_fov width'.split()),
    ('camera', 'live_camera_info'): {'K', 'height', 'width'},
    ('lighting',): set('ambient azimuth_deg cast_shadows color direction elevation_deg family intensity'.split()),
    ('background',): set('asset_id family texture_offset texture_rotation_deg texture_scale zone_x_m'.split()),
    ('objects', '*'): set('annotation_iou asset_id bbox_px class_id class_name commanded_pose distance_category footprint_radius_m footprint_reference gazebo_label horizontal_range_m ignored_reason instance_id label_state normalized_footprint_distance occlusion_requested physical_dimensions_m pose secondary_bbox_px slant_range_m truncated usable_direction_radius_m visibility_method visible_fraction yaw_deg yolo_bbox'.split()),
    ('objects', '*', 'pose'): POSE_KEYS,
    ('objects', '*', 'commanded_pose'): POSE_KEYS,
    ('distractors', '*'): {'instance_id', 'pose'},
    ('distractors', '*', 'pose'): POSE_KEYS,
}
HUMAN_SCENE_FIELDS=set('composition_requested person_count_band_requested planned_person_count planned_vehicle_count human_grouping_requested'.split())
LEGACY_ROOT=SCHEMA[()]-HUMAN_SCENE_FIELDS


def normalized(record):
    return {k:v for k,v in record.items() if k not in TIMING_FIELDS}


def metadata_differences(a, b, metrics=None):
    """Compare exact metadata except four explicitly scoped realized quantities.

    Quaternion signs are aligned as a whole; component-wise absolute values
    would incorrectly equate different rotations. Raw captures are never edited.
    Unknown schema, non-finite values and type/structure changes fail closed.
    """
    errors = []
    metrics = metrics if metrics is not None else {}

    def walk(x, y, path=()):
        key = tuple('*' if isinstance(p, int) else p for p in path)
        location = '.'.join(map(str, path)) or 'record'
        if type(x) is not type(y):
            errors.append(location + ': type differs'); return
        if isinstance(x, dict):
            expected=LEGACY_ROOT if key==() and 'composition_requested' not in x else SCHEMA.get(key)
            if expected is None or set(x) != expected or set(y) != expected:
                errors.append(location + ': missing/unexpected fields'); return
            for name in sorted(x): walk(x[name], y[name], path + (name,))
            return
        category = None
        pose = key[:-1] in (('camera',), ('objects', '*', 'pose'), ('distractors', '*', 'pose'))
        if pose and key[-1] in POSE_KEYS:
            category = 'position_m' if key[-1] == 'position' else 'quaternion_component'
            length = 3 if category == 'position_m' else 4
        elif key == ('objects', '*', 'secondary_bbox_px') and x is not None:
            category, length = 'secondary_projection_px', 4
        if category:
            if (not isinstance(x, list) or len(x) != length or len(y) != length or
                any(type(v) not in (int, float) or not math.isfinite(v) for v in x + y)):
                errors.append(location + ': invalid numeric vector'); return
            sign = 1
            if category == 'quaternion_component':
                if any(abs(sum(v*v for v in q)-1) > 1e-12 for q in (x, y)):
                    errors.append(location + ': non-unit quaternion'); return
                sign = -1 if sum(u*v for u,v in zip(x,y)) < 0 else 1
                if sign == -1: metrics['quaternion_sign_changes'] = metrics.get('quaternion_sign_changes', 0) + 1
            delta = max(abs(u-sign*v) for u,v in zip(x,y))
            metrics[category] = max(metrics.get(category, 0), delta)
            if delta > TOLERANCES[category]: errors.append(location + ': exceeds absolute tolerance')
            return
        if key == ('objects', '*', 'annotation_iou'):
            if type(x) not in (int, float) or not math.isfinite(x) or not math.isfinite(y):
                errors.append(location + ': invalid IoU'); return
            delta = abs(x-y); metrics['derived_iou'] = max(metrics.get('derived_iou', 0), delta)
            if delta > TOLERANCES['derived_iou']: errors.append(location + ': exceeds absolute tolerance')
        elif isinstance(x, list):
            if len(x) != len(y): errors.append(location + ': length differs'); return
            for i, (u,v) in enumerate(zip(x,y)): walk(u,v,path+(i,))
        elif isinstance(x, float) and (not math.isfinite(x) or not math.isfinite(y)):
            errors.append(location + ': non-finite value')
        elif type(x) not in (str, int, float, bool, type(None)) or x != y:
            errors.append(location + ': exact value differs')

    # Do not let excluded timing fields hide invalid/non-finite metadata.
    from validate_dataset import finite_tree
    if not finite_tree(a) or not finite_tree(b): return ['record: non-finite value']
    for record in (a,b):
        expected=SCHEMA[()] if 'composition_requested' in record else LEGACY_ROOT
        if set(record) != expected | TIMING_FIELDS: return ['record: missing/unexpected fields']
        if any(type(record[k]) is not (str if k == 'generation_timestamp' else float) for k in TIMING_FIELDS):
            return ['record: invalid timing field type']
    walk(normalized(a), normalized(b))
    return errors


def compare(a,b):
    a,b=Path(a),Path(b);ra,rb=committed_records(a),committed_records(b)
    errors=[];rgb_equal=0;metrics={}
    xa=json.loads((a/'.run.json').read_text());xb=json.loads((b/'.run.json').read_text())
    for field in ('expected_count','seed','configuration_sha256','generator_code_sha256',
                  'generator_git_commit','asset_manifest_sha256','camera_configuration_sha256'):
        if field not in xa or field not in xb or xa[field]!=xb[field]: errors.append('Run identity differs: '+field)
    if len(ra)!=len(rb): errors.append('Frame counts differ')
    for x,y in zip(ra,rb):
        differences=metadata_differences(x,y,metrics)
        if differences: errors.append('Scene/pose/label metadata differs: '+x['frame_id']+'; '+'; '.join(differences[:10]))
        la=a/'labels'/x['split']/(x['frame_id']+'.txt');lb=b/'labels'/y['split']/(y['frame_id']+'.txt')
        if la.read_bytes()!=lb.read_bytes(): errors.append('YOLO bytes differ: '+x['frame_id'])
        ia=a/'images'/x['split']/(x['frame_id']+'.png');ib=b/'images'/y['split']/(y['frame_id']+'.png')
        rgb_equal+=file_hash(ia)==file_hash(ib)
    for name in ('scenarios.csv','generation_config.yaml','assets.json','assets.csv','class_mapping.yaml'):
        if file_hash(a/'manifests'/name)!=file_hash(b/'manifests'/name): errors.append('Manifest differs: '+name)
    return {'status':'PASSED' if not errors else 'FAIL','frames':len(ra),'errors':errors,'rgb_identical_frames':rgb_equal,
            'rgb_bytes_identical':len(ra)==len(rb) and rgb_equal==len(ra),
            'absolute_tolerances':TOLERANCES,'measured_max_differences':metrics,
            'comparison_note':'Commanded scenes, IDs, native boxes/labels, YOLO bytes and scenario/config/asset manifests are exact. Only realized positions, whole-sign-equivalent unit quaternions, secondary projection and derived IoU allow stated absolute roundoff. Timing fields are scheduling-dependent. RGB equality is reported separately.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run_a');p.add_argument('run_b');p.add_argument('--report',required=True)
    args=p.parse_args();r=compare(args.run_a,args.run_b);write_json(args.report,r);print(json.dumps(r,indent=2));return 0 if r['status']=='PASSED' else 1


if __name__=='__main__': raise SystemExit(main())
