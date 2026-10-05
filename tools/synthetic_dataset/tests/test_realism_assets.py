"""Prevent inward-facing coach surfaces and accidental material proliferation."""
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import TOOL,load_config


class RealismAssetTests(unittest.TestCase):
    def test_vehicle_draw_calls_are_bounded(self):
        cfg=load_config(TOOL/'configs/synthetic_dataset.yaml')
        for a in cfg['assets']:
            if a['category'] in ('car','truck'):self.assertLessEqual(len(a['dependencies']),24)

    def test_coach_mesh_has_outward_closed_surface(self):
        ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
        for i in range(3):
            for name in ['paint_body','rubber_wheels']:
                root=ET.parse(TOOL/f'models/bus_mesh_{i}/{name}.dae')
                vertices=np.array(list(map(float,root.find(".//c:source[@id='positions']/c:float_array",ns).text.split()))).reshape(-1,3)
                ix=np.array(list(map(int,root.find('.//c:triangles/c:p',ns).text.split()))).reshape(-1,3,2)[:,:,0]
                p=vertices[ix];volume=np.einsum('ij,ij->i',p[:,0],np.cross(p[:,1],p[:,2])).sum()/6
                self.assertGreater(volume,0,'Closed coach surface points inward')


if __name__=='__main__':unittest.main()
