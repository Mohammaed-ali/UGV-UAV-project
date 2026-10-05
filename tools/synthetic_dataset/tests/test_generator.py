"""Focused offline invariants and failure injection; no Gazebo launch required."""
from collections import Counter
from copy import deepcopy
import csv
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
import cv2
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import TOOL, canonical, load_config, digest, write_json, atomic_write
from geometry import quaternion, rotation, project_points, ground_ray, footprint, footprint_radius, distance_category, clip_box, yolo_box, iou
from sampling import Sampler, split_schedule, projected_geometry
from storage import complete, commit_sample, paths, summarize, distribution, statistics
from validate_dataset import validate, finite_tree


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=load_config(TOOL/'configs/synthetic_dataset.yaml');cls.cam=cls.cfg['camera']
        cls.sampler=Sampler(cls.cfg,200,12345);cls.scenes=[cls.sampler.scene(i) for i in range(200)]

    def test_class_order_and_mapping(self):
        self.assertEqual([(c['name'],c['yolo_id']) for c in self.cfg['classes']],[('person',0),('car',1),('truck',2),('bus',3)])

    def test_gazebo_namespace(self):
        mapping={c['gazebo_label']:c['yolo_id'] for c in self.cfg['classes']}
        self.assertEqual(mapping,{10:0,20:1,30:2,40:3});self.assertNotIn(0,mapping)

    def test_yolo_conversion(self):
        self.assertEqual(yolo_box([0,0,640,480],self.cam),[.5,.5,1,1])
        np.testing.assert_allclose(yolo_box([160,120,320,240],self.cam),[.375,.375,.25,.25])

    def test_clipping(self): self.assertEqual(clip_box([-4,-2,700,520],self.cam),[0,0,640,480])

    def test_invalid_boxes(self):
        for box in ([0,0,0,4],[5,5,1,2],[float('nan'),0,1,1],[641,0,700,3],None):
            self.assertIsNone(clip_box(box,self.cam))
            with self.assertRaises(ValueError): yolo_box(box,self.cam)

    def test_yolo_edges_positive(self):
        v=yolo_box([-20,450,30,500],self.cam);self.assertGreater(v[2],0);self.assertAlmostEqual(v[1]+v[3]/2,1)

    def test_split_counts(self): self.assertEqual(Counter(split_schedule(10000,self.cfg['split_fractions'],3)),{'train':8000,'val':1000,'test':1000})

    def test_scene_family_isolation(self):
        sets={s:{r['scene_family'] for r in self.scenes if r['split']==s} for s in self.cfg['split_fractions']}
        for a,b in [('train','val'),('train','test'),('val','test')]: self.assertFalse(sets[a]&sets[b])

    def test_asset_holdout(self):
        assets={a['asset_id']:a for a in self.cfg['assets']}
        for r in self.scenes:
            for aid in [r['background']['asset_id']]+[o['asset_id'] for o in r['objects']]: self.assertIn(r['split'],assets[aid]['eligibility'])

    def test_seed_reproduction(self):
        other=Sampler(self.cfg,200,12345)
        self.assertEqual([canonical(other.scene(i)) for i in (0,50,199)],[canonical(self.scenes[i]) for i in (0,50,199)])

    def test_seed_changes_scene(self): self.assertNotEqual(self.scenes[1]['scenario_sha256'],Sampler(self.cfg,200,12346).scene(1)['scenario_sha256'])

    def test_altitude_quotas(self):
        for split in ('train','val','test'):
            counts=Counter(r['camera']['nominal_altitude_m'] for r in self.scenes if r['split']==split)
            self.assertEqual(set(counts),set(self.cfg['sampling']['altitude_buckets_m']));self.assertLessEqual(max(counts.values())-min(counts.values()),4)
            for composition in self.cfg['scene_composition'][split]:
                group=[r for r in self.scenes if r['split']==split and r['composition_requested']==composition]
                values=Counter(r['camera']['nominal_altitude_m'] for r in group)
                counts=[values[h] for h in self.cfg['sampling']['altitude_buckets_m']]
                self.assertLessEqual(max(counts)-min(counts),1)

    def test_angle_quotas(self): self.assertEqual(set(r['camera']['nominal_off_nadir_deg'] for r in self.scenes),{0,10,20,30})

    def test_yaw_ranges(self):
        for r in self.scenes:
            self.assertTrue(0<=r['camera']['viewing_azimuth_deg']<360)
            for o in r['objects']: self.assertTrue(0<=o['yaw_deg']<360)

    def test_off_nadir_definition(self):
        for r in self.scenes:
            forward=rotation(r['camera']['quaternion'])[:,0]
            self.assertAlmostEqual(math.degrees(math.acos(float(np.clip(-forward[2],-1,1)))),r['camera']['actual_off_nadir_deg'],places=5)

    def test_distance_categories(self):
        bands=self.cfg['sampling']['distance_bands']
        self.assertEqual([distance_category(x,bands) for x in (0,.35,.70,.90,1,1.1)],['near','medium','far','edge','edge','outside'])

    def test_ground_footprint(self):
        pose={'position':[0,0,20],'quaternion':quaternion(0,math.pi/2,0)}
        np.testing.assert_allclose(ground_ray(320,240,pose,self.cam),[0,0,0],atol=1e-9)
        polygon=footprint(pose,self.cam);radius=footprint_radius(np.array([0,0]),np.array([1,0]),polygon,pose,self.cam)
        self.assertAlmostEqual(radius,20*240/self.cam['fy'])

    def test_upward_rays_rejected(self):
        with self.assertRaises(ValueError): ground_ray(320,240,{'position':[0,0,20],'quaternion':[0,0,0,1]},self.cam)

    def test_projection_optical_axes(self):
        p={'position':[0,0,0],'quaternion':[0,0,0,1]}
        result=project_points([[10,0,0],[10,-1,0],[10,0,-1]],p,self.cam)
        self.assertEqual(result[0].tolist(),[320,240]);self.assertGreater(result[1,0],320);self.assertGreater(result[2,1],240)

    def test_spacing_and_grounding(self):
        for r in self.scenes:
            for i,o in enumerate(r['objects']):
                self.assertEqual(o['pose']['position'][2],0)
                for b in r['objects'][i+1:]: self.assertGreaterEqual(np.linalg.norm(np.asarray(o['pose']['position'][:2])-b['pose']['position'][:2]),o['footprint_radius_m']+b['footprint_radius_m']+self.cfg['sampling']['min_spacing_m'])

    def test_negative_mixture(self):
        self.assertEqual(Counter(r['kind'] for r in self.scenes),{'negative':20,'distractor_only':20,'positive':160})
        for r in self.scenes:
            if r['kind']!='positive': self.assertEqual(r['objects'],[])
            if r['kind']=='negative': self.assertEqual(r['distractors'],[])

    def test_metadata_serialization(self):
        self.assertEqual(json.loads(canonical(self.scenes[1])),self.scenes[1]);self.assertFalse(finite_tree({'invalid':float('inf')}))

    def test_iou_semantics(self):
        self.assertEqual(iou([0,0,5,5],[0,0,5,5]),1);self.assertEqual(iou([0,0,1,1],[2,2,3,3]),0)

    def test_distribution_order_independence(self):
        values=[1e16,1,1]
        self.assertEqual(distribution(values),distribution(list(reversed(values))))

    def test_asset_dimensions(self):
        for a in self.cfg['assets']:
            if a['category']=='background': continue
            points=np.asarray(a['geometry_points']);self.assertAlmostEqual(points[:,2].min(),0)
            np.testing.assert_allclose(points.max(0)-points.min(0),a['physical_dimensions_m'])

    def test_atomic_resume_and_corruption(self):
        r=deepcopy(next(x for x in self.scenes if x['kind']=='negative'));r.update(simulation_timestamp=1,annotation_timestamp=1,
                 scene_readback_timestamp=.5,timestamp_delta_s=0,settling_sim_seconds=.5)
        with tempfile.TemporaryDirectory() as directory:
            image=np.zeros((480,640,3),np.uint8);commit_sample(directory,r,image,'',r)
            self.assertTrue(complete(directory,r));p=paths(directory,r)
            self.assertEqual(p['label'].read_bytes(),b'');p['image'].write_bytes(b'broken')
            self.assertFalse(complete(directory,r));commit_sample(directory,r,image,'',r);self.assertTrue(complete(directory,r))
            p['status'].unlink();self.assertFalse(complete(directory,r))

    def test_manifest_and_dataset_yaml(self):
        r=deepcopy(next(x for x in self.scenes if x['kind']=='negative'))
        with tempfile.TemporaryDirectory() as directory:
            commit_sample(directory,r,np.zeros((480,640,3),np.uint8),'',r)
            run={'expected_count':1};manifest=summarize(directory,self.cfg,run)
            self.assertEqual(manifest['accepted_samples'],1)
            import yaml
            d=yaml.safe_load((Path(directory)/'data.yaml').read_text());self.assertEqual(d['names'],{0:'person',1:'car',2:'truck',3:'bus'})
            entries=list(csv.DictReader((Path(directory)/'manifests/scenarios.csv').open()));self.assertEqual(len(entries),1)
            self.assertEqual(json.loads((Path(directory)/'statistics.json').read_text()),statistics([r]))

    def test_ignored_objects_stay_accounted(self):
        r=deepcopy(self.scenes[1]);o=r['objects'][0];o.update(label_state='ignored_tiny',ignored_reason='unit-test tiny fixture',bbox_px=[0,0,2,2],yolo_bbox=None)
        self.assertEqual(json.loads(canonical(r))['objects'][0]['ignored_reason'],'unit-test tiny fixture')

    def test_validator_missing_files(self):
        with tempfile.TemporaryDirectory() as directory: self.assertEqual(validate(directory)['status'],'FAIL')

    def test_validator_detects_duplicate_images_and_orphans(self):
        import yaml
        negatives=[deepcopy(r) for r in self.scenes if r['kind']=='negative'][:2]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for r in negatives:
                r.update(simulation_timestamp=1,annotation_timestamp=1,scene_readback_timestamp=.5,timestamp_delta_s=0)
                commit_sample(root,r,np.zeros((480,640,3),np.uint8),'',r)
            atomic_write(root/'manifests/generation_config.yaml',yaml.safe_dump(self.cfg))
            write_json(root/'manifests/assets.json',self.cfg['assets'])
            summarize(root,self.cfg,{'expected_count':2})
            errors=validate(root)['errors'];self.assertTrue(any('Duplicate image SHA256' in e for e in errors))
            p=paths(root,negatives[0]);p['label'].unlink()
            errors=validate(root)['errors'];self.assertTrue(any('missing/orphaned file IDs' in e for e in errors))


if __name__=='__main__': unittest.main()
