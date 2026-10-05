"""Emit measured human/class/size/subset tables for the report, without setting gates."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/synthetic_dataset/scripts'))
from storage import committed_records
from common import write_json

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('dataset');p.add_argument('prefix');args=p.parse_args()
root=Path(args.dataset);prefix=Path(args.prefix)
records=committed_records(root);stats=json.loads((root/'statistics.json').read_text())
human=json.loads((root/'human_statistics.json').read_text());splits=human['splits']
run=json.loads((root/'manifest.json').read_text());rows=[]

def table(headers, values):
    rows.append('| '+' | '.join(headers)+' |')
    rows.append('| '+' | '.join('---' for _ in headers)+' |')
    for v in values:rows.append('| '+' | '.join(map(str,v))+' |')
    rows.append('')

def percent(v,total):return f'{100*v/max(total,1):.3f}%'

rows.append('Actual split composition uses valid exported visible-person boxes; ignored targets remain counted separately.\n')
table(['Measure','Train','Validation','Test'],[
 [label]+[getter(splits[s]) for s in ['train','val','test']]
 for label,getter in [
 ('Images',lambda d:d['training_or_evaluation_images']),
 ('Person frames',lambda d:f"{d['person_frames']} ({percent(d['person_frames'],d['training_or_evaluation_images'])})"),
 ('Vehicle-only frames',lambda d:d['composition_visible'].get('vehicle_only',0)),
 ('Distractor-only frames',lambda d:d['composition_visible'].get('distractor_only',0)),
 ('Empty negative frames',lambda d:d['composition_visible'].get('empty',0)),
 ('Intended positives with all targets ignored',lambda d:d['composition_visible'].get('all_targets_ignored',0)),
 ('Single-person frames',lambda d:d['single_person_frames']),
 ('Multi-person frames',lambda d:d['multi_person_frames']),
 ('Labelled person instances',lambda d:d['person_instances_labelled']),
 ('All person instances, including ignored',lambda d:d['person_instances_all_including_ignored']),
 ('Ignored persons: tiny',lambda d:d['ignored_persons'].get('ignored_tiny',0)),
 ('Ignored persons: occluded',lambda d:d['ignored_persons'].get('ignored_occluded',0)),
 ('Human + vehicle frames',lambda d:d['mixed_person_vehicle_frames'].get('any_vehicle',0))]])

classes={s:Counter(o['class_name'] for r in records if r['split']==s for o in r['objects'] if o['label_state']=='labelled') for s in splits}
table(['Class','Train labels','Validation labels','Test labels','Total labels','All targets'],[
 [c]+[classes[s][c] for s in ['train','val','test']]+[stats['labelled_per_class'].get(c,0),stats['instances_per_class'].get(c,0)]
 for c in ['person','car','truck','bus']])

t=splits['train']
table(['Visible people per TRAIN frame','Frames','Fraction of multi-person frames','Person instances','Fraction of person instances'],[
 [label,t['visible_person_count_histogram'].get(b,0),percent(t['visible_person_count_histogram'].get(b,0),t['multi_person_frames']) if b!='1' else 'single',
  t['instances_by_scene_person_count'].get(b,0),percent(t['instances_by_scene_person_count'].get(b,0),t['person_instances_labelled'])]
 for b,label in [('1','1'),('2_3','2–3'),('4_6','4–6'),('7_10','7–10'),('11_plus','11+')]])

for name in ['altitude','angle','distance','background','lighting','asset','occlusion_requested']:
    rows.append(f'Valid TRAIN person instances by {name}:\n')
    table([name,'Instances','Fraction'],[[k,v,percent(v,t['person_instances_labelled'])] for k,v in sorted(t['labelled_person_instances_by'][name].items())])

rows.append('Person pixel-area categories: very small <64 px²; small 64–<1,024; medium 1,024–<9,216; large ≥9,216.\n')
table(['Pixel area group','Train','Validation','Test'],[
 [b]+[f"{splits[s]['labelled_person_instances_by']['pixel_size'].get(b,0)} ({splits[s]['pixel_size_percentages'].get(b,0):.3f}%)" for s in ['train','val','test']]
 for b in ['very_small','small','medium','large']])

for name in ['altitude','distance','angle']:
    rows.append(f'Native valid TRAIN person box size by {name} (width/height are separately summarized, not one actual median box):\n')
    table([name,'Count','Width median / p05 / p95 (px)','Height median / p05 / p95 (px)','Area median / p05 / p95 (px²)'],[
     [k,v['area_px']['count']]+[' / '.join(f"{v[m][q]:.2f}" for q in ['median','p05','p95']) for m in ['width_px','height_px','area_px']]
     for k,v in sorted(t['bbox_distributions'][name].items())])

subsets=json.loads((root/'manifests/human_evaluation_subsets.json').read_text())['subsets']
table(['Test subset file list','Images'],[[name,len(values)] for name,values in subsets.items()])

yaws={};ranges={}
for split in splits:
    people=[o for r in records if r['split']==split for o in r['objects'] if o['class_name']=='person']
    bins=np.histogram([o['yaw_deg'] for o in people],bins=np.arange(0,361,30))[0].tolist()
    yaws[split]={f'{start}–{start+30}':v for start,v in zip(range(0,360,30),bins)}
    ranges[split]={'min_yaw_deg':min(o['yaw_deg'] for o in people),'max_yaw_deg':max(o['yaw_deg'] for o in people)}
table(['Person yaw bin (all realized people)','Train','Validation','Test'],[[k]+[yaws[s][k] for s in ['train','val','test']] for k in yaws['train']])
write_json(str(prefix)+'_human_yaw.json',{'histogram_30deg':yaws,'ranges':ranges,'definition':'All realized person instances, including ignored; continuous yaw samples, not additional duplicate views.'})

all_ignored=Counter(o['label_state'] for r in records for o in r['objects'] if o['label_state']!='labelled')
rows.append(f"All classes ignored: {dict(all_ignored)}. Placement shortfall: {stats['placement_shortfall']}. Truncated target instances: {stats['truncated_objects']}.\n")
Path(str(prefix)+'_tables.md').write_text('\n'.join(rows))
print(str(prefix)+'_tables.md')
