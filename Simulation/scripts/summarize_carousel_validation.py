"""Summarize measured carousel flight evidence without changing a running world."""
import argparse,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);args=p.parse_args()
folder=args.directory;result=json.loads((folder/'result.json').read_text());ids=result['drones']
rows=[json.loads(line) for line in (folder/'telemetry.jsonl').open()]
events={};max_y=0.;moving_samples=0;unsafe=[];launch=[];docked=[];seen=set();image_ages=[];telemetry_ages=[];stops={}
for row in rows:
 for event in row['events']:events[(event['id'],event['time'])]=event
 stops.setdefault(row['stop_index'],{'stop_index':row['stop_index'],'first_observed_time':row['sim_time'],'carrier_position':row['carrier']['position']})
 rack=row['carousel']
 max_y=max(max_y,*(abs(t['y']) for t in rack['trays'].values()))
 if rack['moving']:
  moving_samples+=1
  for d in row['drones']:
   if d['state'] in ('STORED','DOCKED') and (d['armed'] or not d['latched']):unsafe.append([row['sim_time'],d['id']])
 for d in row['drones']:
  if d['id'] not in ids:continue
  if d['state'] not in ('STORED','DOCKED','PREPARING','ARMING','RELEASING') and d.get('telemetry_age') is not None:telemetry_ages.append(d['telemetry_age'])
  for state,order in [('TAKEOFF',launch),('DOCKED',docked)]:
   key=(d['id'],state)
   if d['state']==state and key not in seen:seen.add(key);order.append({'id':d['id'],'time':row['sim_time']})
  if d['state'] in ('ALIGNING','DESCENDING') and d.get('vision'):
   stamp=d['vision'].get('tag_time',d['vision']['time']);image_ages.append(max(0,row['sim_time']-stamp))
final=result.get('final',rows[-1]);landings=[]
for d in final['drones']:
 if d['id'] not in ids:continue
 tray=d.get('tray_position')
 landings.append({k:d.get(k) for k in ('id','state','armed','latched','tag_error','detection_latency')}|{'physical_xy_offset_m':math.hypot(d['position'][0]-tray[0],d['position'][1]-tray[1]) if tray else None})
summary={'run_id':result['run_id'],'passed':result['passed'],'wall_seconds':result.get('wall_seconds'),'sim_time':final['sim_time'],
 'launch_order':launch,'docking_order':docked,'carousel_events':[e for e in events.values() if 'Carousel' in e['message']],
 'maximum_measured_carriage_offset_m':max_y,'moving_samples':moving_samples,'unlatched_or_armed_stored_aircraft_during_indexing':unsafe,
 'maximum_landing_image_age_s':max(image_ages,default=None),'final_landings':landings,'detected_targets':len(final['tracks'])}
summary.update(maximum_airborne_telemetry_age_s=max(telemetry_ages,default=None),stops_observed=list(stops.values()))
(folder/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
