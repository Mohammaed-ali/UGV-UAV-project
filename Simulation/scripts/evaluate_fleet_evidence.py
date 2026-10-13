"""Offline measured-trace contacts, interpolated swept footprints and freshness.

Interpolation checks recorded pose intervals; this is not continuously
instrumented ground truth. Recording gaps and resolution are reported.
"""
from pathlib import Path
import sys,json,math,statistics
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.config import Mission,scene
from backend.city import project,DIMENSIONS,rounded_loop,DISTRICTS,SERVICE_X,SERVICE_Y,SERVICE_HALF

def sweep(previous,current,body):
 if previous is None:return [current]
 delta=math.remainder(current['yaw']-previous['yaw'],2*math.pi)
 steps=max(1,math.ceil(math.dist(previous['position'][:2],current['position'][:2])/.1),math.ceil(abs(delta)/math.radians(2)))
 return [{'position':[a+(b-a)*i/steps for a,b in zip(previous['position'],current['position'])],'yaw':previous['yaw']+delta*i/steps} for i in range(steps+1)]

def corners(pose,body):
 pos=pose['position'];c,s=math.cos(pose['yaw']),math.sin(pose['yaw'])
 return [[pos[0]+dx*c-dy*s,pos[1]+dx*s+dy*c] for dx in (-body[0]/2,body[0]/2) for dy in (-body[1]/2,body[1]/2)]

def evaluate(folder):
 config=folder/'mission.json'
 mission=Mission.model_validate_json(config.read_text()) if config.exists() else Mission.model_validate(json.loads((folder/'result.json').read_text())['mission'])
 layout=scene(mission);objects={o['id']:o for o in layout['objects']};networks={p['id']:p['points'] for p in layout['networks']};centres={i:rounded_loop(b) for i,b in enumerate(DISTRICTS)}
 footprints={};travel={};previous={};last_time=None;max_gap=0;contacts=0;actor_contacts=0;rtfs=[];telemetry=[];ages=[];final=None;carrier_previous=None;carrier_excess=0.;samples=0;lane_error=0.
 for line in (folder/'telemetry.jsonl').open():
  row=json.loads(line);now=row['sim_time'];final=row
  if last_time is not None:max_gap=max(max_gap,now-last_time)
  last_time=now;rtfs.append(row['physics']['real_time_factor'])
  for d in row['drones']:
   if d['armed'] and d['telemetry_age'] is not None:telemetry.append(d['telemetry_age'])
   if d['state']=='DESCENDING' and (d.get('vision') or {}).get('tag_time') is not None:ages.append(now-d['vision']['tag_time'])
  city=row.get('city')
  if not city:continue
  contacts=max(contacts,len(city['contact_events']));actor_contacts=max(actor_contacts,len(city['actor_contacts']))
  carrier=row.get('carrier')
  if carrier and carrier.get('position'):
   # Conservative loaded chassis/wheel rectangle. Indexed carousel clearance
   # is reserved separately by the larger deployment bay geometry.
   for pose in sweep(carrier_previous,carrier,(3.3,3.7)):
    carrier_excess=max(carrier_excess,max(min(abs(p[0]-SERVICE_X),abs(p[1]-SERVICE_Y))-SERVICE_HALF for p in corners(pose,(3.3,3.7))))
   carrier_previous=carrier
  for actor in city['actors']:
   name=actor['id'];pos=actor['position'];old=previous.get(name)
   if old is not None:travel[name]=travel.get(name,0)+math.dist(pos,old['position'])
   previous[name]=actor
   if actor['parked']:continue
   lane_error=max(lane_error,actor['lane_error'])
   network=objects[name];path=networks[network['path_id']] if actor['kind']=='person' else centres[network['district']];body=DIMENSIONS[actor['kind']];width=1.1 if actor['kind']=='person' else 5.
   for pose in sweep(old,actor,body):
    samples+=1;excess=max(project(path,p)[0]-width for p in corners(pose,body));footprints[name]=max(footprints.get(name,0.),excess)
 report={'actor_travel_m':travel,'maximum_footprint_excess_m':footprints,'maximum_carrier_swept_excess_m':carrier_excess,'maximum_actor_lane_error_m':lane_error,'maximum_carrier_contacts':contacts,'maximum_actor_contacts':actor_contacts,'maximum_recording_gap_sim_seconds':max_gap,'median_rtf':statistics.median(rtfs) if rtfs else None,'maximum_airborne_telemetry_age':max(telemetry,default=None),'maximum_descending_image_age':max(ages,default=None),'trace_final_sim_time':final['sim_time'] if final else None,'sweep_method':'Interpolate measured pose intervals at <=0.1 m translation and <=2 degree rotation; test full body corners against assigned sidewalk/road or protected UGV corridor. Trace approximation, not continuous occupancy instrumentation.','swept_actor_pose_samples':samples}
 report['passed']=contacts==0 and actor_contacts==0 and max(footprints.values(),default=0)<.1 and carrier_excess<.1 and lane_error<1. and max_gap<3.
 (folder/'city-evaluation.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':print(json.dumps(evaluate(Path(sys.argv[1])),indent=2))
