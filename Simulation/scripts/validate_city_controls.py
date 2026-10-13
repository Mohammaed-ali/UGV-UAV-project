"""Focused native gate for adjustable speeds and explicit operator placement."""
import sys,json,time,math,uuid
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.config import Mission,Point,Stop
from backend.runtime import Runtime
from backend.mission import Engine
from backend.city import DIMENSIONS,placement_plan,point_at,lengths

m=Mission(living_city=True,tracking_enabled=False,population=6,traffic=6,ugv_speed=10,walking_speed=5,traffic_speed=20,
          start=Point(x=-108,y=-22),stops=[Stop(id='finish',label='Finish',x=108,y=-22)])
out=ROOT/'artifacts/instant-tracking'/('city-controls-'+str(uuid.uuid4()));out.mkdir(parents=True)
runtime=Runtime(ROOT);runtime.render_cameras=False
vision=SimpleNamespace(confidence=.4,latest={},searching=set(),detector_ready=True,tag_ready=True,error=None)
engine=Engine(ROOT,runtime,vision);engine.configure(m)
result={'passed':False,'mission':m.model_dump(),'placement_checks':[]};wall=time.monotonic();last=-10;last_log=-1;placed=False;peak_ugv=0;peaks={};max_lane={}
try:
 engine.command('initialize')
 with (out/'telemetry.jsonl').open('w') as log:
  while time.monotonic()-wall<210:
   engine.tick();now=engine.now()
   if engine.state=='READY':engine.command('start')
   if now>10 and engine.city and not placed:
    for name,x,y in [('person_0',-90,40),('vehicle_0',-90,15),('vehicle_2',-90,-55)]:
     row=engine.city.relocate(name,x,y,0);deadline=time.monotonic()+1.5
     while time.monotonic()<deadline and math.dist(runtime.gz.poses[name]['position'][:2],[x,y])>.1:
      engine.tick();time.sleep(.03)
     error=math.dist(runtime.gz.poses[name]['position'][:2],[x,y]);actor=engine.city.actors[name]
     check={'id':name,'class':actor['kind'],'free_placement_error_m':error,'stationary':actor['parked']}
     proposals=[p for p in engine.city.layout['networks'] if p['kind']==('sidewalk' if actor['kind']=='person' else 'vehicle')]
     objects=[o for o in engine.city.layout['objects'] if o['kind']=='building']+[{**a,'x':runtime.gz.poses[a['id']]['position'][0],'y':runtime.gz.poses[a['id']]['position'][1]} for a in engine.city.actors.values()]
     destination=None
     for path in proposals:
      for s in range(0,int(lengths(path['points'])[-1]),7):
       point,yaw=point_at(path['points'],s)
       try:placement_plan(actor,*point,yaw,objects,engine.city.layout['networks'],m.stops,runtime.gz.poses['carrier']['position'])
       except ValueError:continue
       destination=point;break
      if destination:break
     if destination is None:raise RuntimeError('No free lane placement found')
     engine.city.relocate(name,*destination,0);deadline=time.monotonic()+1.5
     while time.monotonic()<deadline and math.dist(runtime.gz.poses[name]['position'][:2],destination)>.2:
      engine.tick();time.sleep(.03)
     check.update(lane_placement_error_m=math.dist(runtime.gz.poses[name]['position'][:2],destination),path=actor['path_id'],resumed=not actor['parked']);result['placement_checks'].append(check)
    try:engine.city.relocate('person_0',30,0,0)
    except ValueError:result['service_lane_rejected']=True
    placed=True
   if now-last_log>.5:
    last_log=now;state=engine.snapshot();log.write(json.dumps(state)+'\n');log.flush()
    peak_ugv=max(peak_ugv,abs(state['carrier']['speed']))
    for actor in (state.get('city') or {}).get('actors',[]):
     peaks[actor['id']]=max(peaks.get(actor['id'],0),actor['speed']);max_lane[actor['id']]=max(max_lane.get(actor['id'],0),actor['lane_error'])
   if now-last>=15:last=now;print(json.dumps({'time':round(now,1),'state':engine.state,'peak_ugv':peak_ugv,'max_lane_error':max(max_lane.values(),default=0)}),flush=True)
   if engine.state in ('ERROR','FAULT') or engine.hold or now>100:break
   time.sleep(.025)
 final=engine.snapshot();result.update(final=final,wall_seconds=round(time.monotonic()-wall,2),peak_ugv_speed=peak_ugv,peak_actor_speeds=peaks,maximum_lane_errors=max_lane)
 result['passed']=placed and result.get('service_lane_rejected') and all(c['free_placement_error_m']<.1 and c['lane_placement_error_m']<.2 and c['stationary'] and c['resumed'] for c in result['placement_checks']) and final['state']=='COMPLETE' and peak_ugv>3. and not final['city']['contact_events'] and not final['city']['actor_contacts'] and not final['city']['violations'] and not final['city']['crossing_violations']
except Exception as error:
 result['error']=str(error);import traceback;traceback.print_exc()
finally:
 runtime.stop();(out/'result.json').write_text(json.dumps(result,indent=2));print('EVIDENCE',out,'PASS' if result['passed'] else 'FAIL',flush=True)
raise SystemExit(0 if result['passed'] else 1)
