"""No visible targets is valid only with explicit simulator-derived accounting."""
from copy import deepcopy
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import TOOL, load_config
from sampling import Sampler
from gazebo_backend import Gazebo


class CapturePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config(TOOL / 'configs/synthetic_dataset.yaml')
        # Actual failure: single person beneath canopy at seed 76543/index 147.
        cls.scene = Sampler(cls.cfg, 200, 76543).scene(147)

    def capture(self, candidates):
        scene = deepcopy(self.scene)
        g = Gazebo.__new__(Gazebo); g.cfg = self.cfg; g.active = set()
        g.buffers = {'rgb': {0.: None}}; g.entity_ids = {'sun': 1}
        g.camera_info = {'width': 640, 'height': 480, 'K': []}
        g.request = Mock()
        actual = {'dataset_rig': scene['camera']}
        actual.update({o['instance_id']: o['pose'] for o in scene['objects'] + scene['distractors']})
        header = SimpleNamespace(stamp=SimpleNamespace(sec=2, nsec=0))
        rgb = SimpleNamespace(width=640, height=480, pixel_format_type=3,
                              step=1920, data=bytes(640*480*3), header=header)
        boxes = SimpleNamespace(annotated_box=candidates, header=header)
        g.wait = Mock(side_effect=[(1., actual), (rgb, boxes)])
        modules = {}
        for module, name in [('pose_v_pb2', 'Pose_V'), ('boolean_pb2', 'Boolean'), ('light_pb2', 'Light')]:
            m = ModuleType('gz.msgs10.' + module)
            setattr(m, name, Mock(return_value=Mock()))
            modules[m.__name__] = m
        with patch.dict(sys.modules, modules): return g.capture(scene)

    def test_fully_occluded_scene_keeps_target_and_empty_label(self):
        image, labels, metadata = self.capture([])
        self.assertEqual(image.shape, (480, 640, 3)); self.assertEqual(labels, '')
        self.assertEqual(metadata['kind'], 'positive'); self.assertEqual(metadata['native_box_count'], 0)
        self.assertEqual(len(metadata['objects']), 1)
        self.assertEqual(metadata['objects'][0]['label_state'], 'ignored_occluded')
        self.assertIn('no visible simulator pixels', metadata['objects'][0]['ignored_reason'])
        self.assertIsNone(metadata['objects'][0]['bbox_px'])

    def test_all_tiny_scene_keeps_native_box_without_yolo_row(self):
        box = SimpleNamespace(label=10, box=SimpleNamespace(
            min_corner=SimpleNamespace(x=10., y=10.), max_corner=SimpleNamespace(x=11., y=11.)))
        with patch('gazebo_backend.projected_geometry', return_value=[10., 10., 12., 12.]):
            _, labels, metadata = self.capture([box])
        self.assertEqual(labels, ''); self.assertEqual(metadata['objects'][0]['label_state'], 'ignored_tiny')
        self.assertEqual(metadata['objects'][0]['bbox_px'], [10., 10., 12., 12.])
        self.assertTrue(metadata['objects'][0]['ignored_reason'])

    def test_unexplained_native_class_is_still_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'Unexpected native semantic class'):
            self.capture([SimpleNamespace(label=0)])


if __name__ == '__main__': unittest.main()
