"""Realized-state equivalence must never relax commanded/native determinism."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import TOOL, load_config, canonical
from sampling import Sampler
from check_determinism import metadata_differences, TOLERANCES


class DeterminismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg = load_config(TOOL / 'configs/synthetic_dataset.yaml')
        sampler = Sampler(cfg, 200, 12345)
        r = next(sampler.scene(i) for i in range(200) if sampler.scene(i)['objects'])
        r['camera']['commanded_pose'] = deepcopy(r['camera'])
        r['camera']['model'] = cfg['camera']
        r['camera']['live_camera_info'] = {'K': [cfg['camera']['fx'], 0., 320., 0., cfg['camera']['fy'], 240., 0., 0., 1.], 'width': 640, 'height': 480}
        for o in r['objects']:
            o['commanded_pose'] = deepcopy(o['pose'])
            o.update(secondary_bbox_px=[10., 20., 30., 40.], bbox_px=[10., 20., 30., 40.],
                     annotation_iou=1., yolo_bbox=[.03125, .0625, .03125, 1/24],
                     visible_fraction=None, visibility_method='not measured', truncated=False,
                     occlusion_requested=r['occlusion_requested'], label_state='labelled', ignored_reason=None)
        r.update(simulation_timestamp=1., annotation_timestamp=1., timestamp_delta_s=0.,
                 scene_readback_timestamp=.5, settling_sim_seconds=.5, generation_timestamp='test',
                 annotation_method='native_visible_2d', native_box_count=len(r['objects']))
        # Exercise the actual JSON metadata contract, not numpy sampler scalars.
        cls.record = json.loads(canonical(r))

    def test_identical(self):
        self.assertEqual(metadata_differences(self.record, deepcopy(self.record)), [])

    def test_equivalent_sign_and_roundoff(self):
        b = deepcopy(self.record)
        poses = [b['camera']] + [o['pose'] for o in b['objects']] + [d['pose'] for d in b['distractors']]
        for p in poses:
            p['position'][0] += 2e-12
            p['quaternion'] = [-v for v in p['quaternion']]
            p['quaternion'][0] += 3e-16
        b['objects'][0]['secondary_bbox_px'][0] += 5e-11
        b['objects'][0]['annotation_iou'] -= 4e-12
        metrics = {}
        self.assertEqual(metadata_differences(self.record, b, metrics), [])
        self.assertEqual(metrics['quaternion_sign_changes'], len(poses))

    def test_meaningful_realized_changes_fail(self):
        for path, delta in [('position', 1e-6), ('quaternion', 1e-6)]:
            for which in ('camera', 'object', 'distractor'):
                with self.subTest(path=path, which=which):
                    b = deepcopy(self.record)
                    p = b['camera'] if which == 'camera' else b['objects'][0]['pose'] if which == 'object' else b['distractors'][0]['pose']
                    p[path][0] += delta
                    self.assertTrue(metadata_differences(self.record, b))

    def test_component_signs_are_not_equivalent(self):
        b = deepcopy(self.record)
        b['camera']['quaternion'][2] *= -1
        self.assertTrue(metadata_differences(self.record, b))

    def test_projection_and_iou_above_tolerance_fail(self):
        for field, limit in [('secondary_bbox_px', TOLERANCES['secondary_projection_px']), ('annotation_iou', TOLERANCES['derived_iou'])]:
            b = deepcopy(self.record)
            if field == 'secondary_bbox_px': b['objects'][0][field][0] += limit * 2
            else: b['objects'][0][field] -= limit * 2
            self.assertTrue(metadata_differences(self.record, b))

    def test_commanded_pose_sign_and_roundoff_are_exact(self):
        for key in ('position', 'quaternion'):
            b = deepcopy(self.record)
            b['camera']['commanded_pose'][key][0] += 1e-13
            self.assertTrue(metadata_differences(self.record, b))
        b = deepcopy(self.record)
        b['objects'][0]['commanded_pose']['quaternion'] = [-v for v in b['objects'][0]['commanded_pose']['quaternion']]
        self.assertTrue(metadata_differences(self.record, b))

    def test_native_labels_and_scene_fields_are_exact(self):
        for field, value in [('bbox_px', [10. + 1e-12, 20., 30., 40.]), ('class_id', 3),
                             ('label_state', 'ignored_tiny'), ('instance_id', 'different'),
                             ('yolo_bbox', [0., 0., .1, .1])]:
            b = deepcopy(self.record); b['objects'][0][field] = value
            self.assertTrue(metadata_differences(self.record, b), field)
        for field, value in [('frame_id', 'other'), ('scene_seed', 0)]:
            b = deepcopy(self.record); b[field] = value
            self.assertTrue(metadata_differences(self.record, b), field)
        b = deepcopy(self.record); b['lighting']['intensity'] += 1e-12
        self.assertTrue(metadata_differences(self.record, b))

    def test_unexpected_fields_and_types_fail_even_when_equal(self):
        for field, value in [('position', 'invalid'), ('quaternion', [0., 0., 0.])]:
            b = deepcopy(self.record); b['camera'][field] = value
            self.assertTrue(metadata_differences(b, deepcopy(b)))
        b = deepcopy(self.record); b['camera']['unexpected'] = 1.
        self.assertTrue(metadata_differences(b, deepcopy(b)))
        b = deepcopy(self.record); b['objects'][0]['class_id'] = float(b['objects'][0]['class_id'])
        self.assertTrue(metadata_differences(self.record, b))

    def test_nonfinite_and_nonunit_fail(self):
        for field in ('simulation_timestamp', 'secondary_bbox_px', 'quaternion'):
            b = deepcopy(self.record)
            if field == 'simulation_timestamp': b[field] = float('nan')
            elif field == 'secondary_bbox_px': b['objects'][0][field][0] = float('inf')
            else: b['camera'][field] = [0., 0., 0., 2.]
            self.assertTrue(metadata_differences(b, deepcopy(b)))

    def test_only_timing_values_are_excluded(self):
        b = deepcopy(self.record); b['simulation_timestamp'] = 123.; b['generation_timestamp'] = 'later'
        self.assertEqual(metadata_differences(self.record, b), [])
        b['simulation_timestamp'] = '123'
        self.assertTrue(metadata_differences(self.record, b))


if __name__ == '__main__': unittest.main()
