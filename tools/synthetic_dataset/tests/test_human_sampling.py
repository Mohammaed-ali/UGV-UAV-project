"""Quotas, retained difficult human instances and honest subset invariants."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import TOOL,load_config
from sampling import Sampler,quota_schedule
from human_qa import evaluation_subsets,human_statistics,person_band


class HumanSamplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=load_config(TOOL/'configs/synthetic_dataset.yaml');cls.sampler=Sampler(cls.cfg,2000,12345)

    def test_explicit_training_and_evaluation_quotas(self):
        s=self.sampler
        for split,expected in [('train',{'human_positive':960,'vehicle_only':320,'distractor_only':160,'empty':160}),
                               ('test',{'human_positive':60,'vehicle_only':100,'distractor_only':20,'empty':20}),
                               ('val',{'human_positive':60,'vehicle_only':100,'distractor_only':20,'empty':20})]:
            self.assertEqual(Counter(s.compositions[i] for i in range(s.count) if s.splits[i]==split),expected)

    def test_person_and_crowd_count_allocation(self):
        s=self.sampler;indices=[i for i in range(s.count) if s.splits[i]=='train' and s.person_counts[i]]
        self.assertEqual(sum(s.person_counts[i]==1 for i in indices),432)
        self.assertEqual(Counter(s.human_bands[i] for i in indices),{'1':432,'2_3':211,'4_6':185,'7_10':106,'11_plus':26})
        self.assertTrue(all(person_band(s.person_counts[i])==s.human_bands[i] for i in indices))

    def test_distance_quotas_are_instance_based(self):
        s=self.sampler;counts=Counter(x for i,bands in s.person_distances.items() if s.splits[i]=='train' for x in bands)
        n=sum(counts.values())
        for band,target in self.cfg['human_priority']['distance_weights'].items():self.assertLessEqual(abs(counts[band]-n*target),1)

    def test_largest_remainders_do_not_lose_frames(self):
        x=quota_schedule({'a':.6,'b':.2,'c':.1,'d':.1},17,9)
        self.assertEqual(len(x),17);self.assertEqual(x,quota_schedule({'a':.6,'b':.2,'c':.1,'d':.1},17,9))

    def test_humans_do_not_change_distance_to_fit(self):
        s=self.sampler
        for i in [i for i in range(s.count) if s.person_counts[i]][:25]:
            scene=s.scene(i);humans=[o for o in scene['objects'] if o['class_name']=='person']
            self.assertEqual(len(humans),s.person_counts[i]);self.assertEqual([o['distance_category'] for o in humans],s.person_distances[i])

    def test_mixed_classes_and_heldout_source_restrictions(self):
        s=self.sampler;found=set()
        for i in [i for i in range(s.count) if s.splits[i]=='test' and s.compositions[i] in ('human_positive','vehicle_only')][:40]:
            scene=s.scene(i)
            for o in scene['objects']:
                if o['class_name']!='person':self.assertTrue(s.assets[o['asset_id']]['held_out']);found.add(o['class_name'])
        self.assertEqual(found,{'car','truck','bus'})

    def test_evaluation_lists_do_not_copy_or_count_ignored(self):
        scene=deepcopy(self.sampler.scene(next(i for i in range(2000) if self.sampler.splits[i]=='test' and self.sampler.person_counts[i]>=2)))
        for o in scene['objects']:o.update(label_state='labelled',bbox_px=[0,0,5,8])
        people=[o for o in scene['objects'] if o['class_name']=='person']
        for o in people[1:]:o['label_state']='ignored_tiny'
        subsets=evaluation_subsets([scene],self.cfg)
        self.assertEqual(len(subsets['test_person_single']),1);self.assertFalse(subsets['test_person_multi'])
        self.assertEqual(subsets['test_person_small'],subsets['test_person_all'])
        stats=human_statistics([scene],self.cfg)['splits']['test']
        self.assertEqual(stats['person_instances_labelled'],1)
        self.assertEqual(stats['ignored_persons']['ignored_tiny'],len(people)-1)


if __name__=='__main__':unittest.main()
