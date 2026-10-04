"""Native visible-box association must handle occlusion without guessing IDs."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gazebo_backend import associate_visible_boxes


class AssociationTests(unittest.TestCase):
    cam={'width':640,'height':480}

    def match(self,objects,candidates):
        return associate_visible_boxes(objects,candidates,self.cam,.01,1.)

    def test_occluded_pilot_sliver_uniquely_contained(self):
        objects=[{'gazebo_label':20,'secondary_bbox_px':[311.004884,170.280282,408.112951,283.588697]},
                 {'gazebo_label':20,'secondary_bbox_px':[74.318676,267.935821,233.249804,338.143496]},
                 {'gazebo_label':20,'secondary_bbox_px':[438.079870,293.591141,611.710356,375.458697]}]
        candidates=[(20,[438.,294.,611.,375.]),(20,[75.,268.,233.,338.]),(20,[357.,276.,370.,283.])]
        self.assertEqual(self.match(objects,candidates),{0:candidates[2][1],1:candidates[1][1],2:candidates[0][1]})

    def test_wrong_class_sliver_rejected(self):
        with self.assertRaises(RuntimeError):
            self.match([{'gazebo_label':20,'secondary_bbox_px':[0,0,100,100]}],[(10,[30,30,35,35])])

    def test_overlapping_same_class_sliver_is_ambiguous(self):
        with self.assertRaises(RuntimeError):
            self.match([{'gazebo_label':20,'secondary_bbox_px':[0,0,100,100]},
                        {'gazebo_label':20,'secondary_bbox_px':[20,20,120,120]}],[(20,[30,30,35,35])])

    def test_outside_and_noncontained_native_box_rejected(self):
        for box in ([120,120,125,125],[99,30,110,35]):
            with self.assertRaises(RuntimeError):
                self.match([{'gazebo_label':20,'secondary_bbox_px':[0,0,100,100]}],[(20,box)])

    def test_regular_iou_matches_and_empty_candidates_unchanged(self):
        objects=[{'gazebo_label':20,'secondary_bbox_px':[0,0,100,100]}]
        self.assertEqual(self.match(objects,[(20,[0,0,100,100])]),{0:[0,0,100,100]})
        self.assertEqual(self.match(objects,[]),{})


if __name__=='__main__': unittest.main()
