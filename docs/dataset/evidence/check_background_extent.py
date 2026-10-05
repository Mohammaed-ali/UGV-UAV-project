"""Measure retained high/oblique-view finite terrain / camera far-clip artifacts."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import cv2
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[3]/'tools/synthetic_dataset/scripts'))
from common import write_json
from storage import committed_records
from geometry import rotation
p=argparse.ArgumentParser(description=__doc__);p.add_argument('dataset');args=p.parse_args()
root=Path(args.dataset);records=committed_records(root)
reference=None
for r in records:
    c=r['camera'];cam=c['model']
    for u,v in [(0,0),(639,0)]:
        ray=rotation(c['quaternion'])@np.array([1,(cam['cx']-u)/cam['fx'],(cam['cy']-v)/cam['fy']])
        t=-c['position'][2]/ray[2];q=np.asarray(c['position'])+t*ray
        if t>cam['far']+2 or max(abs(q[0]-r['background']['zone_x_m']),abs(q[1]))>121:
            reference=r
            rgb=cv2.imread(str(root/'images'/r['split']/(r['frame_id']+'.png')))
            sky=rgb[v,u].copy();break
    if reference is not None:break
if reference is None:raise ValueError('No unambiguous finite-ground/far-clip background reference in this run')
findings=[];groups=Counter();fracs=[]
for r in records:
    rgb=cv2.imread(str(root/'images'/r['split']/(r['frame_id']+'.png')))
    mask=np.all(rgb==sky,axis=2);n=int(mask.sum())
    if not n:continue
    groups[f"{r['camera']['nominal_altitude_m']}m/{r['camera']['nominal_off_nadir_deg']}deg"]+=1
    fraction=n/mask.size;fracs.append(fraction)
    findings.append({'frame_id':r['frame_id'],'background_pixel_fraction':fraction})
c=reference['camera'];cam=c['model']
v,u=np.mgrid[0:480,0:640];rays=np.stack([np.ones_like(u),(cam['cx']-u)/cam['fx'],(cam['cy']-v)/cam['fy']],axis=-1)@rotation(c['quaternion']).T
t=-c['position'][2]/rays[:,:,2];q=np.asarray(c['position'])+t[:,:,None]*rays
plane=(abs(q[:,:,0]-reference['background']['zone_x_m'])>120)|(abs(q[:,:,1])>120)
far=t>cam['far'];predicted=plane|far
mask=np.all(cv2.imread(str(root/'images'/reference['split']/(reference['frame_id']+'.png')))==sky,axis=2)
overlap=(predicted&mask).sum();union=(predicted|mask).sum()
write_json(root/'qa/background_extent_review.json',{
 'status':'DIAGNOSTIC_COMPLETE','method':'Exact constant environment-background pixels; analytical ground ray/240m terrain and 100m camera-forward clip check on a geometrically selected reference. Antialiased boundary pixels are excluded from the exact-color count.',
 'frames':len(records),'affected_frames':len(findings),'affected_frame_fraction':len(findings)/len(records),
 'max_background_pixel_fraction':max(fracs,default=0),'mean_fraction_in_affected_frames':float(np.mean(fracs)) if fracs else 0,
 'by_altitude_angle':dict(groups),'environment_background_bgr':sky.tolist(),
 'example':{'frame_id':reference['frame_id'],'predicted_background_fraction':float(predicted.mean()),
  'native_background_fraction':float(mask.mean()),'predicted_vs_native_mask_iou':float(overlap/union),
  'finite_plane_only_fraction':float((plane&~far).mean()),'far_clip_fraction':float(far.mean())},
 'findings':findings,'interpretation':'Some high/oblique image corners show the environment background. Targets use a conservatively far-bounded footprint. Retain configured difficult views; document this synthetic background extent / fixed camera clipping limitation.'})
print(json.dumps({'affected_frames':len(findings),'max_fraction':max(fracs,default=0),'groups':dict(groups),'example_mask_iou':float(overlap/union)},indent=2))
