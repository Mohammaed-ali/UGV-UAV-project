"""Native loaded carousel indexing, without aircraft flight or perception load."""
import sys,time,json,uuid,shutil,math
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.config import Mission,Stop
from backend.runtime import Runtime
from backend.mission import Engine

def main():
 out=ROOT/'artifacts/living-city'/('loaded-carousel-'+str(uuid.uuid4()));out.mkdir(parents=True)
 m=Mission(living_city=True,tracking_enabled=False,population=0,traffic=0,target_present=False,wheels=6,stops=[Stop(id='bay',label='Native carousel check',x=-24,y=-22,drones=[])])
 runtime=Runtime(ROOT);runtime.render_cameras=False
 vision=SimpleNamespace(confidence=.4,detector_ready=True,tag_ready=True,error=None,latest={},searching=set())
 engine=Engine(ROOT,runtime,vision);engine.configure(m);result={'passed':False,'mission':m.model_dump(),'gate':'Physical indexing with eight stored, natively attached aircraft. No flight/detection/docking claim.','legs':[]}
 started=time.monotonic();leg=None;original={};stage=0;last_log=-1
 try:
  engine.command('initialize')
  with (out/'telemetry.jsonl').open('w') as log:
   while time.monotonic()-started<600:
    engine.tick();now=engine.now();state=engine.snapshot()
    if now-last_log>.5:last_log=now;log.write(json.dumps(state)+'\n');log.flush()
    if engine.state in ('ERROR','FAULT') or engine.carousel.error:raise RuntimeError(engine.carousel.error or runtime.error or engine.state)
    if runtime.state=='running' and engine.state=='READY':
     if not original:
      if not all(runtime.gz.latches.get(d)=='attached' for d in engine.drones):time.sleep(.05);continue
      original={d:runtime.gz.poses[d]['position'] for d in engine.drones}
     if leg is None and stage<2:
      level=('lower','upper')[stage]
      if engine.carousel.request(level,engine.carousel_can_move()):leg={'level':level,'started_sim_time':now};print('START',level,now,flush=True)
     elif leg is not None and engine.carousel.ready(runtime.gz,leg['level']):
      leg.update(finished_sim_time=now,duration=now-leg['started_sim_time'],native_latches=dict(runtime.gz.latches),carousel=engine.carousel.snapshot(runtime.gz));result['legs'].append(leg);print('INDEXED',leg['level'],now,flush=True);stage+=1;leg=None
     if stage==2:
      movement={d:math.dist(original[d],runtime.gz.poses[d]['position']) for d in original};result.update(final=state,final_aircraft_displacement_m=movement,passed=all(runtime.gz.latches.get(d)=='attached' for d in original) and max(movement.values())<.05);break
    time.sleep(.04)
 except Exception as error:result['error']=str(error)
 finally:
  result['wall_seconds']=time.monotonic()-started;runtime.stop();(out/'result.json').write_text(json.dumps(result,indent=2));shutil.copytree(ROOT/'.runtime/logs',out/'runtime-logs',dirs_exist_ok=True);print('EVIDENCE',out,'PASS' if result['passed'] else 'FAIL',flush=True)
 return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
