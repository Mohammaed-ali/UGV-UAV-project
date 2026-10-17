"""Native first-leg regression using the saved route, with aircraft stored."""
import sys,json,time,math,uuid,hashlib
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.config import Mission,spawn_pose,wrap
from backend.runtime import Runtime
from backend.mission import Engine

original=(ROOT/'missions/current.json').read_bytes()
saved=Mission.model_validate_json(original)
data=saved.model_dump()
data.update(tracking_enabled=False,stops=[{**data['stops'][0],'drones':[]}])
mission=Mission.model_validate(data)
out=ROOT/'artifacts/start-heading'/('native-'+str(uuid.uuid4())[:8])
out.mkdir(parents=True)
runtime=Runtime(ROOT);runtime.render_cameras=False
vision=SimpleNamespace(confidence=.4,latest={},searching=set(),detector_ready=True,tag_ready=True,error=None)
engine=Engine(ROOT,runtime,vision);engine.configure(mission)
result={'passed':False,'mission':mission.model_dump(),'expected_yaw_degrees':math.degrees(spawn_pose(mission)['yaw'])}
wall=time.monotonic();previous=None;rotation=0.;total_rotation=0.;started=None;initial=None;worst_bay_error=0.
try:
    engine.command('initialize')
    with (out/'telemetry.jsonl').open('w') as log:
        while time.monotonic()-wall<100:
            engine.tick();now=engine.now();gz=runtime.gz
            if engine.state=='READY':
                initial=dict(gz.poses['carrier']);started=now;engine.command('start')
                print('START',json.dumps(initial),flush=True)
            if started is not None and gz and 'carrier' in gz.poses:
                p=gz.poses['carrier'];yaw=p['yaw']
                if previous is not None:
                    step=wrap(yaw-previous);rotation+=step;total_rotation+=abs(step)
                previous=yaw
                bay_errors=[]
                for d in engine.drones.values():
                    aircraft=gz.poses.get(d['id']);tray=engine.tray_pose(d)
                    if aircraft and tray:bay_errors.append(math.dist(aircraft['position'][:2],tray[:2]))
                worst_bay_error=max(worst_bay_error,max(bay_errors,default=0.))
                log.write(json.dumps({'time':now,'state':engine.state,'carrier':p,'odom':gz.odom,'bay_errors_m':bay_errors})+'\n')
                log.flush()
            if engine.state in ('COMPLETE','ERROR','FAULT') or engine.hold:break
            time.sleep(.03)
    final=engine.snapshot();goal=mission.stops[0]
    distance=math.dist(final['carrier']['position'][:2],[goal.x,goal.y])
    result.update(initial=initial,final=final,wall_seconds=round(time.monotonic()-wall,2),
                  signed_rotation_degrees=math.degrees(rotation),total_rotation_degrees=math.degrees(total_rotation),
                  maximum_aircraft_to_bay_xy_error_m=worst_bay_error,arrival_distance_m=distance)
    result['passed']=bool(initial and final['state']=='COMPLETE' and not engine.hold
                          and abs(wrap(initial['yaw']-spawn_pose(mission)['yaw']))<.02
                          and total_rotation<math.radians(30) and worst_bay_error<.1
                          and distance<.5 and all(d['latched'] for d in final['drones'])
                          and not (final.get('city') or {}).get('contact_events'))
except Exception as error:
    result['error']=str(error)
    import traceback;traceback.print_exc()
finally:
    runtime.stop()
    result['saved_mission_unchanged']=hashlib.sha256(original).digest()==hashlib.sha256((ROOT/'missions/current.json').read_bytes()).digest()
    result['passed']=result['passed'] and result['saved_mission_unchanged']
    (out/'result.json').write_text(json.dumps(result,indent=2))
    print('EVIDENCE',out,'PASS' if result['passed'] else 'FAIL',flush=True)
    print(json.dumps({k:v for k,v in result.items() if k not in ('initial','final','mission')}),flush=True)
raise SystemExit(0 if result['passed'] else 1)
