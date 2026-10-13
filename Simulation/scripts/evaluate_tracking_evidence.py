"""Offline, ground-truth-only evaluation. Never imported by runtime perception."""
import sys,json,math,argparse
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.transport import quaternion_matrix
from backend.config import Mission,scene
from backend.city import DIMENSIONS

def ray_box(a,b,o):
 lo,hi=0.,1.;d=b-a
 for axis,size in enumerate(('sx','sy','sz')):
  center=o['x'] if axis==0 else o['y'] if axis==1 else o['sz']/2
  lower=center-o[size]/2;upper=center+o[size]/2
  if abs(d[axis])<1e-9:
   if not lower<=a[axis]<=upper:return False
  else:
   u,v=(lower-a[axis])/d[axis],(upper-a[axis])/d[axis];lo=max(lo,min(u,v));hi=min(hi,max(u,v))
   if lo>hi:return False
 return hi>=0 and lo<=1

def in_view(drone,actor,buildings):
 rotation=quaternion_matrix(drone['quaternion']);pos=np.array(drone['position']);origin=pos+rotation@np.array([0,0,-.08]);size=DIMENSIONS[actor['kind']]
 point=np.array(actor['position'])+np.array([0,0,size[2]*.55]);body=rotation.T@(point-pos);depth=-body[2]-.08
 if depth<=.1:return False
 f=640/(2*math.tan(1.22/2));u=320-f*body[1]/depth;v=240-f*body[0]/depth
 return 0<=u<640 and 0<=v<480 and not any(ray_box(origin,point,o) for o in buildings)

def evaluate(folder):
 result=json.loads((folder/'result.json').read_text());actor_id=result.get('evaluation_actor');source=folder/'telemetry.jsonl'
 if not source.exists():return None
 mission=Mission.model_validate(result['mission']);buildings=[o for o in scene(mission)['objects'] if o['kind']=='building'];selected=result.get('selected_id');allowed={selected,*[c['candidate']['id'] for c in result.get('operator_confirmations',[])]}
 metrics={'method':'0.5 s measured-world samples; calibrated camera centre visibility with static building ray obstruction, not pixel segmentation','selected_actor':actor_id,'geometrically_visible_samples':0,'visible_fresh_tracking_samples':0,'truth_identity_switches':0,'false_reacquisitions':0,'indeterminate_identity_samples':0,'unconfirmed_perception_id_changes':0,'ambiguous_samples':0,'maximum_ugv_actor_contacts':0,'maximum_actor_contacts':0}
 last_truth=None;last_id=None;last_phase=None;fresh=0;active=0
 for line in source.open():
  state=json.loads(line);tracking=state['tracking'];phase=tracking['state'];city=state.get('city') or {};drone=state['drones'][0]
  metrics['maximum_ugv_actor_contacts']=max(metrics['maximum_ugv_actor_contacts'],len(city.get('contact_events',[])));metrics['maximum_actor_contacts']=max(metrics['maximum_actor_contacts'],len(city.get('actor_contacts',[])))
  row=next((t for t in state.get('catalogue',[]) if t['id']==tracking['target_id']),None)
  if row and row['ambiguous']:metrics['ambiguous_samples']+=1
  if phase not in ('TRACKING','OCCLUDED','SEARCHING','REACQUIRING'):continue
  active+=1;actor=next((a for a in city.get('actors',[]) if a['id']==actor_id),None)
  visible=actor is not None and in_view(drone,actor,buildings)
  if visible:metrics['geometrically_visible_samples']+=1
  if phase=='TRACKING' and row:
   fresh+=1
   if visible:metrics['visible_fresh_tracking_samples']+=1
   if last_id is not None and row['id']!=last_id and row['id'] not in allowed:metrics['unconfirmed_perception_id_changes']+=1
   last_id=row['id']
   actors=[a for a in city.get('actors',[]) if a['kind']==row['class'] or row['class']!='person' and a['kind']!='person']
   matches=sorted((math.dist(a['position'][:2],row['position'][:2]),a['id']) for a in actors)
   if not matches or matches[0][0]>2.5 or len(matches)>1 and matches[1][0]-matches[0][0]<.75:metrics['indeterminate_identity_samples']+=1
   else:
    truth=matches[0][1]
    if last_truth is not None and truth!=last_truth:metrics['truth_identity_switches']+=1
    if last_phase is not None and last_phase!='TRACKING' and actor_id is not None and truth!=actor_id:metrics['false_reacquisitions']+=1
    last_truth=truth
  last_phase=phase
 metrics['geometric_visible_tracking_coverage']=metrics['visible_fresh_tracking_samples']/max(1,metrics['geometrically_visible_samples']);metrics['active_samples']=active;metrics['fresh_samples']=fresh
 (folder/'evaluation.json').write_text(json.dumps(metrics,indent=2));return metrics

def main():
 parser=argparse.ArgumentParser();parser.add_argument('folders',nargs='+',type=Path);args=parser.parse_args()
 for folder in args.folders:
  value=evaluate(folder)
  if value:print(folder.name,json.dumps(value))
if __name__=='__main__':main()
