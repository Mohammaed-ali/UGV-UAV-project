"""Scientific summary figures from committed metadata, without image alteration."""
import argparse,json,sys
from pathlib import Path
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/synthetic_dataset/scripts'))
from storage import committed_records
from human_qa import person_band,visible_people
p=argparse.ArgumentParser(description=__doc__);p.add_argument('dataset');p.add_argument('output');args=p.parse_args()
root=Path(args.dataset);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
r=committed_records(root);h=json.loads((root/'human_statistics.json').read_text())
fig,axes=plt.subplots(2,3,figsize=(13,7.5),constrained_layout=True)
compositions=['human_positive','vehicle_only','distractor_only','empty'];x=np.arange(4)
for j,split in enumerate(['train','val','test']):
 s=h['splits'][split];n=s['training_or_evaluation_images'];axes[0,0].bar(x+(j-1)*.24,[100*s['composition_visible'].get(k,0)/n for k in compositions],width=.24,label=split)
axes[0,0].set_xticks(x,['person','vehicle only','distractor','empty'],rotation=15);axes[0,0].set_ylabel('% images');axes[0,0].set_title('Visible frame composition');axes[0,0].legend()
s=h['splits']['train'];bands=['1','2_3','4_6','7_10','11_plus'];labels=['1','2–3','4–6','7–10','11+']
axes[0,1].bar(labels,[s['visible_person_count_histogram'].get(k,0) for k in bands]);axes[0,1].set_title('TRAIN person frames by crowd size');axes[0,1].set_ylabel('images')
axes[0,2].bar(labels,[s['instances_by_scene_person_count'].get(k,0) for k in bands]);axes[0,2].set_title('TRAIN instances by frame crowd size');axes[0,2].set_ylabel('person boxes')
people=[(z,o) for z in r for o in visible_people(z)];altitudes=sorted(set(z['camera']['nominal_altitude_m'] for z,o in people))
area=lambda o:(o['bbox_px'][2]-o['bbox_px'][0])*(o['bbox_px'][3]-o['bbox_px'][1])
axes[1,0].boxplot([[area(o) for z,o in people if z['camera']['nominal_altitude_m']==a] for a in altitudes],labels=[str(a) for a in altitudes],showfliers=False);axes[1,0].set_yscale('log');axes[1,0].set_title('Valid person pixel area by altitude');axes[1,0].set_xlabel('nominal altitude (m)');axes[1,0].set_ylabel('box area (px²)')
dist=s['labelled_person_instances_by']['distance'];distance_bands=['near','medium','far','edge'];total=s['person_instances_labelled']
axes[1,1].bar(distance_bands,[100*dist.get(k,0)/total for k in distance_bands]);axes[1,1].set_title('TRAIN valid person distance coverage');axes[1,1].set_ylabel('% person boxes')
size=s['pixel_size_percentages'];size_bands=['very_small','small','medium','large'];axes[1,2].bar(size_bands,[size.get(k,0) for k in size_bands]);axes[1,2].set_title('TRAIN person pixel-area groups');axes[1,2].set_ylabel('% person boxes');axes[1,2].tick_params(axis='x',rotation=15)
fig.suptitle(f'Gazebo synthetic aerial dataset: {len(r):,} committed frames');fig.savefig(out/'human_balance_and_size.png',dpi=160);plt.close(fig)
audit=json.loads((root/'qa/annotation_audit.json').read_text());fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
for cls in ['person','car','truck','bus']:
 vals=[o['iou'] for o in audit['observations'] if o['class']==cls]
 axes[0].hist(vals,bins=np.linspace(0,1,26),histtype='step',label=cls)
axes[0].set_title(f"{audit['audited_frames']}-frame projection audit");axes[0].set_xlabel('native visible / full projected box IoU');axes[0].set_ylabel('instances');axes[0].legend()
for requested,color in [('none','tab:blue'),('mild','tab:orange'),('moderate','tab:red')]:
 vals=[o['iou'] for o in audit['observations'] if o['occlusion_requested']==requested]
 axes[1].hist(vals,bins=np.linspace(0,1,26),histtype='step',color=color,label=requested)
axes[1].set_title('IoU by requested occlusion');axes[1].set_xlabel('IoU');axes[1].legend();fig.savefig(out/'annotation_iou_distribution.png',dpi=160);plt.close(fig)
print('Saved figures',str(out))
