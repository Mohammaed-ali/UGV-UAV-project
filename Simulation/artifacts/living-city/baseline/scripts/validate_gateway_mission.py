"""Run one physical regression through the operator API and restore the saved plan."""
import argparse,json,time,uuid
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--drones',type=int,choices=[1,2,3,4,8],default=3);parser.add_argument('--wheels',type=int,choices=[4,6],default=4);parser.add_argument('--timeout',type=float,default=600)
    parser.add_argument('--city',action='store_true');parser.add_argument('--target',action='store_true')
    parser.add_argument('--split',action='store_true',help='Divide the selected fleet over two stops')
    args=parser.parse_args();ids=[f'uav{i:02d}' for i in range(1,args.drones+1)]
    if args.split and len(ids)<2:parser.error('--split requires at least two aircraft')
    client=httpx.Client(base_url='http://127.0.0.1:8765',timeout=90)
    def get(path):
        response=client.get('/api/'+path);response.raise_for_status();return response.json()
    def command(name,state):
        response=client.post('/api/command',json={'name':name,'run_id':state['run_id'],'request_id':str(uuid.uuid4())});response.raise_for_status();return response.json()
    state=get('state')
    if state['runtime']['state']!='offline':raise SystemExit('Reset the runtime before starting this owned regression.')
    original=get('config')['mission'];mission=dict(original)
    mission.update(name=f'Carousel validation · {args.drones} aircraft',wheels=args.wheels,terrain='proving_ground' if args.city else 'field',population=18 if args.target else 0,traffic=10 if args.city else 0,target_present=args.target,search_timeout=30 if args.target else 6,loiter_seconds=5,observation_seconds=8,wind=0,
                   stops=[{'id':'regression','label':'Landing check','x':original['start']['x']+4,'y':original['start']['y'],'drones':ids,'search_radius':12}])
    if args.split:
        half=len(ids)//2;mission['stops'][0]['drones']=ids[:half]
        mission['stops'].append({'id':'regression-b','label':'Second deployment','x':original['start']['x']+12,
                                 'y':original['start']['y'],'drones':ids[half:],'search_radius':12})
    saved=client.put('/api/config',json=mission);saved.raise_for_status();state=get('state')
    out=ROOT/'artifacts'/f'gateway-validation-{state["run_id"]}';out.mkdir(parents=True,exist_ok=True)
    (out/'original-mission.json').write_text(json.dumps(original,indent=2));(out/'mission.json').write_text(json.dumps(mission,indent=2))
    result={'run_id':state['run_id'],'drones':ids,'wheels':args.wheels,'split':args.split,'passed':False};start=time.monotonic();last=None;started=False;last_print=-10
    try:
        command('initialize',state)
        with open(out/'telemetry.jsonl','w') as telemetry:
            while time.monotonic()-start<args.timeout:
                state=get('state');telemetry.write(json.dumps(state)+'\n');telemetry.flush()
                selected=[d for d in state['drones'] if d['id'] in ids]
                signature=(state['state'],tuple(d['state'] for d in selected))
                if signature!=last or time.monotonic()-start-last_print>10:
                    if signature!=last:
                        for d in selected:
                            image=client.get('/api/camera/'+d['id'])
                            if image.status_code==200:(out/f'{d["id"]}-{d["state"].lower()}.jpg').write_bytes(image.content)
                    print(json.dumps({'wall_seconds':round(time.monotonic()-start,1),'sim_time':state['sim_time'],'mission':state['state'],'runtime':state['runtime']['progress'],
                                      'drones':[{k:d[k] for k in ('id','state','ready','armed','tag_error','extension')} for d in selected]}),flush=True)
                    last=signature;last_print=time.monotonic()-start
                if state['state']=='READY' and all(d['ready'] for d in selected) and not started:
                    command('start',state);started=True
                if state['state'] in ('COMPLETE','FAULT','ERROR','ABORTED'):break
                # Mission authority logs at 2 Hz; this observer need not add
                # ten expensive fleet snapshots per second to a loaded host.
                time.sleep(.5)
        result.update(final=state,wall_seconds=round(time.monotonic()-start,2),
                      passed=state['state']=='COMPLETE' and all(d['state']=='DOCKED' and not d['armed'] and d['latched'] and d['extension']<.03 for d in selected)
                      and (not args.target or bool(state['tracks'])))
    except Exception as exc:result['error']=str(exc)
    finally:
        (out/'result.json').write_text(json.dumps(result,indent=2))
        import shutil
        if (ROOT/'.runtime/logs').is_dir():shutil.copytree(ROOT/'.runtime/logs',out/'runtime-logs',dirs_exist_ok=True)
        # Only the generated test run is reset; the original paused run was
        # explicitly reset by the operator before this script was started.
        try:
            command('reset',get('state'))
            restored=client.put('/api/config',json=original);restored.raise_for_status();result['original_mission_restored']=True
        except Exception as exc:result['restore_error']=str(exc)
        (out/'result.json').write_text(json.dumps(result,indent=2));client.close()
        print('EVIDENCE',str(out),'PASS' if result['passed'] else 'FAIL',flush=True)
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
