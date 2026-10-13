"""Run an owned, measured end-to-end mission and preserve telemetry and sensor evidence."""
import argparse,json,time,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.config import Mission,Stop
from backend.runtime import Runtime
from backend.vision import Vision
from backend.mission import Engine

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--drones',type=int,choices=[1,2,4,8],default=1)
    parser.add_argument('--wheels',type=int,choices=[4,6],default=4)
    parser.add_argument('--target',action='store_true')
    parser.add_argument('--timeout',type=float,default=600)
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    runtime=Runtime(root);vision=Vision(root,runtime);engine=Engine(root,runtime,vision)
    config=Mission(wheels=args.wheels,terrain='field',population=4 if args.target else 0,traffic=0,target_present=args.target,
        stops=[Stop(id='check',label='Validation',x=-24,y=-22,drones=[f'uav{i:02d}' for i in range(1,args.drones+1)])],
        search_timeout=25 if args.target else 6,loiter_seconds=5,observation_seconds=8)
    engine.configure(config);out=root/'artifacts'/f'validation-{engine.run_id}';out.mkdir(parents=True,exist_ok=True)
    (out/'mission.json').write_text(config.model_dump_json(indent=2));start=time.monotonic();last=None;started=False
    poses=[];summary={'run_id':engine.run_id,'configuration':config.model_dump(),'passed':False};last_print=-10
    try:
        engine.command('initialize')
        while time.monotonic()-start<args.timeout:
            engine.tick();snapshot=engine.snapshot()
            signature=(snapshot['state'],snapshot['runtime']['progress'],tuple(d['state'] for d in snapshot['drones']))
            if signature!=last or time.monotonic()-start-last_print>=10:
                if signature!=last:
                    for did,data in vision.annotated.items():(out/f'{did}-{engine.drones[did]["state"].lower()}.jpg').write_bytes(data)
                print(json.dumps({'wall_seconds':round(time.monotonic()-start,1),'sim_time':snapshot['sim_time'],'state':snapshot['state'],
                    'runtime':snapshot['runtime']['progress'],'drones':[{k:d[k] for k in ['id','state','ready','armed','position','extension','tag_error']} for d in snapshot['drones'][:args.drones]]}),flush=True)
                last=signature;last_print=time.monotonic()-start
            if snapshot['state']=='READY' and all(d['ready'] for d in snapshot['drones'][:args.drones]) and not started:
                engine.command('start');started=True
            poses.append(snapshot)
            if snapshot['state'] in ('COMPLETE','FAULT','ERROR','ABORTED'):break
            time.sleep(.05)
        summary.update(final=engine.snapshot(),wall_seconds=round(time.monotonic()-start,2),passed=engine.state=='COMPLETE',contacts=runtime.gz.contacts if runtime.gz else {},commands=runtime.fleet.commands if runtime.fleet else [])
        for did,data in vision.annotated.items():(out/f'{did}-camera.jpg').write_bytes(data)
        for did,data in vision.raw.items():(out/f'{did}-raw.jpg').write_bytes(data)
        (out/'telemetry.jsonl').write_text(''.join(json.dumps(p)+'\n' for p in poses))
    except Exception as e:
        summary['error']=str(e);traceback.print_exc()
    finally:
        (out/'result.json').write_text(json.dumps(summary,indent=2));vision.close();runtime.stop()
        print('EVIDENCE',str(out),'PASS' if summary['passed'] else 'FAIL',flush=True)
    return 0 if summary['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
