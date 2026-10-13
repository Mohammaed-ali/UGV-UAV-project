"""Offline scenario events from measured traces; never a perception input."""
import argparse,json,math,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.config import Mission,scene
from backend.city import DIMENSIONS
from backend.transport import quaternion_matrix
from evaluate_tracking_evidence import ray_box

def evaluate(folder):
 result=json.loads((folder/'result.json').read_text());mission=Mission.model_validate(result['mission']);actor_id=result.get('evaluation_actor')
 buildings=[o for o in scene(mission)['objects'] if o['kind']=='building'];rows=[]
 for line in (folder/'telemetry.jsonl').open():
  s=json.loads(line);a=next((a for a in (s.get('city') or {}).get('actors',[]) if a['id']==actor_id),None)
  if not a or s['tracking']['state'] not in ('TRACKING','OCCLUDED','SEARCHING','REACQUIRING'):continue
  d=s['drones'][0];r=quaternion_matrix(d['quaternion']);pos=np.array(d['position']);target=np.array(a['position'])+np.array([0,0,DIMENSIONS[a['kind']][2]*.55]);body=r.T@(target-pos);depth=-body[2]-.08
  f=640/(2*math.tan(1.22/2));inside=depth>.1 and 0<=320-f*body[1]/depth<640 and 0<=240-f*body[0]/depth<480
  blocked=inside and any(ray_box(pos+r@np.array([0,0,-.08]),target,b) for b in buildings)
  rows.append({'time':s['sim_time'],'phase':s['tracking']['state'],'speed':a['speed'],'yaw':a['yaw'],'position':a['position'],'inside_camera':bool(inside),'building_blocked':bool(blocked)})
 stopped=[a for a in rows if a['speed']<.1];blocked=[a for a in rows if a['building_blocked']]
 resumed=[a for a in rows if stopped and a['time']>stopped[0]['time'] and a['phase']=='TRACKING' and a['speed']>.5]
 reappeared=[a for a in rows if blocked and a['time']>blocked[0]['time'] and a['phase']=='TRACKING' and a['inside_camera'] and not a['building_blocked']]
 turn=max((abs((a['yaw']-rows[0]['yaw']+math.pi)%(2*math.pi)-math.pi) for a in rows if a['phase']=='TRACKING'),default=0)
 report={'scenario':mission.city_scenario,'actor':actor_id,'method':'Offline measured target/world/camera evaluation only; building obstruction counts only within the camera frustum.',
  'stopped_samples':len(stopped),'fresh_follow_after_stop':len(resumed),'fresh_tracking_yaw_change_rad':turn,
  'building_blocked_samples':len(blocked),'first_building_obstruction':blocked[0]['time'] if blocked else None,
  'fresh_reappearance_after_obstruction':reappeared[0]['time'] if reappeared else None,
  'maximum_target_coordinate_m':max((max(abs(v) for v in a['position'][:2]) for a in rows),default=0),
  'tracking_outcome':result['final']['tracking'].get('outcome'),'physical_gate_passed':result['passed']}
 if mission.city_scenario=='stopping-vehicle':report['scenario_event_verified']=bool(stopped and resumed and turn>.3)
 elif mission.city_scenario=='building-occlusion':report['scenario_event_verified']=bool(blocked and reappeared)
 elif mission.city_scenario=='leaving-area':report['scenario_event_verified']=report['tracking_outcome']=='left-area' and report['maximum_target_coordinate_m']>mission.flight_boundary
 else:report['scenario_event_verified']=None
 (folder/'scenario-events.json').write_text(json.dumps(report,indent=2));return report

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('folders',nargs='+',type=Path);args=parser.parse_args()
 for folder in args.folders:print(folder.name,json.dumps(evaluate(folder)))
