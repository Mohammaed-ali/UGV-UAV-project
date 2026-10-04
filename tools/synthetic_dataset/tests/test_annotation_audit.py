"""Audit must recompute secondary geometry and catch corrupted stored boxes."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from preview_dataset import fresh_projection, verify_projection


class AuditTests(unittest.TestCase):
    def test_known_optical_projection(self):
        camera={'position':[0,0,0],'quaternion':[0,0,0,1],
                'model':{'cx':320,'cy':240,'fx':270,'fy':270,'near':.1}}
        asset={'geometry_points':[[10,-1,-2],[10,1,2]]}
        obj={'pose':{'position':[0,0,0],'quaternion':[0,0,0,1]},'secondary_bbox_px':[0,0,1,1]}
        self.assertEqual(fresh_projection(asset,obj,camera),[293.,186.,347.,294.])

    def test_corrupted_stored_geometry_rejected(self):
        with self.assertRaisesRegex(ValueError,'Stored secondary box'):
            verify_projection([0,0,3,4],[0,0,3.5,4])
        with self.assertRaisesRegex(ValueError,'visibility differs'):
            verify_projection(None,[0,0,3,4])
        with self.assertRaises(ValueError): verify_projection([float('nan'),0,3,4],[0,0,3,4])
        self.assertEqual(verify_projection(None,None),0.)


if __name__=='__main__': unittest.main()
