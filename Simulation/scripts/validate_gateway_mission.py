"""Run one physical regression through the operator API and restore the saved plan."""
import argparse,json,time,uuid,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--drones',type=int,choices=[1,2,3,4,8],default=3);parser.add_argument('--wheels',type=int,choices=[4,6],default=4);parser.add_argument('--timeout',type=float,default=600)
    parser.add_argument('--aircraft',nargs='+',choices=[f'uav{i:02d}' for i in range(1,9)],help='Focused physical regression for specific aircraft');parser.add_argument('--resume-run',help='Continue recording the same owned run after a recorder interruption');parser.add_argument('--extended-seconds',type=float,default=0);parser.add_argument('--city',action='store_true');parser.add_argument('--target',action='store_true')
    parser.add_argument('--split',action='store_true',help='Divide the selected fleet over two stops')
    args=parser.parse_args();ids=args.aircraft or [f'uav{i:02d}' for i in range(1,args.drones+1)]
    if args.split and len(ids)<2:parser.error('--split requires at least two aircraft')
    client=httpx.Client(base_url='http://127.0.0.1:8765',timeout=90)
    def get(path):
        response=client.get('/api/'+path);response.raise_for_status();return response.json()
    def command(name,state):
        response=client.post('/api/command',json={'name':name,'run_id':state['run_id'],'request_id':str(uuid.uuid4())});response.raise_for_status();return response.json()
    captures=[];camera_pool=ThreadPoolExecutor(max_workers=1);previous_phases={}
    def capture(did,phase,sim_time):
        try:
            image=httpx.get('http://127.0.0.1:8765/api/camera/'+did,timeout=3)
            if image.status_code==200:(out/f'{did}-{phase.lower()}.jpg').write_bytes(image.content)
            captures.append({'drone':did,'requested_phase':phase,'requested_sim_time':sim_time,'http_status':image.status_code})
        except Exception as exc:captures.append({'drone':did,'requested_phase':phase,'requested_sim_time':sim_time,'error':str(exc)})
    state=get('state')
    if args.resume_run:
        if state['run_id']!=args.resume_run or state['runtime']['state']=='offline':raise SystemExit('The requested owned runtime is not active.')
        out=ROOT/'artifacts'/f'gateway-validation-{state["run_id"]}'
        original=json.loads((out/'original-mission.json').read_text());mission=json.loads((out/'mission.json').read_text())
        args.city=mission.get('living_city',False);args.wheels=mission['wheels'];args.target=mission['target_present'];ids=[d for stop in mission['stops'] for d in stop['drones']]
        get_config_scene=get('config')['scene']
    else:
        if state['runtime']['state']!='offline':raise SystemExit('Reset the runtime before starting this owned regression.')
        original=get('config')['mission'];mission=dict(original)
        mission.update(living_city=args.city,tracking_enabled=False,city_scenario='custom',name=f'Carousel validation · {len(ids)} aircraft',wheels=args.wheels,terrain='proving_ground' if args.city else 'field',population=18 if args.target else 0,traffic=10 if args.city else 0,target_present=args.target,search_timeout=30 if args.target else 6,loiter_seconds=5,observation_seconds=8,wind=0,
                       stops=[{'id':'regression','label':'Landing check','x':original['start']['x']+4,'y':original['start']['y'],'drones':ids,'search_radius':12}])
        if args.split:
            half=len(ids)//2;mission['stops'][0]['drones']=ids[:half]
            mission['stops'].append({'id':'regression-b','label':'Second deployment','x':original['start']['x']+12,
                                     'y':original['start']['y'],'drones':ids[half:],'search_radius':12})
        saved=client.put('/api/config',json=mission);saved.raise_for_status();get_config_scene=saved.json()['scene'];state=get('state')
        out=ROOT/'artifacts'/f'gateway-validation-{state["run_id"]}';out.mkdir(parents=True,exist_ok=True)
        (out/'original-mission.json').write_text(json.dumps(original,indent=2));(out/'mission.json').write_text(json.dumps(mission,indent=2))
    result={'run_id':state['run_id'],'drones':ids,'wheels':args.wheels,'split':args.split,'passed':False,'living_city':args.city,'thresholds':{'carrier_contacts':0,'actor_contacts':0,'maximum_footprint_excess_m':.1}};start=time.monotonic();last=None;started=False;last_print=-10;actor_travel={};previous_actors={};footprints={};rtfs=[];telemetry_ages=[];landing_ages=[];servo_ages=[]
    # Re-read only compact freshness metrics before continuing. Full footprint
    # compliance is recalculated from preserved measured traces after completion.
    if args.resume_run:
        result['recorder_resumed']={'sim_time':state['sim_time'],'reason':'Recording window extended for measured host real-time factor; physical runtime was preserved.'}
        started=True
        for line in (out/'telemetry.jsonl').open():
            old=json.loads(line);rtfs.append(old['physics']['real_time_factor']);telemetry_ages.extend(d['telemetry_age'] for d in old['drones'] if d['armed'] and d['telemetry_age'] is not None)
        start-=max(0,time.time()-(out/'original-mission.json').stat().st_mtime)
    try:
        if not args.resume_run:command('initialize',state)
        with open(out/'telemetry.jsonl','a' if args.resume_run else 'w') as telemetry:
            while time.monotonic()-start<args.timeout:
                state=get('state');telemetry.write(json.dumps(state)+'\n');telemetry.flush()
                selected=[d for d in state['drones'] if d['id'] in ids]
                rtfs.append(state['physics']['real_time_factor'])
                telemetry_ages.extend(d['telemetry_age'] for d in selected if d['armed'] and d['telemetry_age'] is not None)
                landing_ages.extend(state['sim_time']-d['vision'].get('tag_time',state['sim_time']) for d in selected if d['state'] in ('TAG_ACQUIRE','ALIGNING','DESCENDING') and (d.get('vision') or {}).get('tag_time') is not None)
                servo_ages.extend(state['sim_time']-d['vision']['tag_time'] for d in selected if d['state']=='DESCENDING' and (d.get('vision') or {}).get('tag_time') is not None)
                if args.city and not args.resume_run and state.get('city'):
                    import math
                    from backend.city import project,DIMENSIONS,rounded_loop,DISTRICTS
                    for actor in state['city']['actors']:
                        name=actor['id'];position=actor['position']
                        if name in previous_actors:actor_travel[name]=actor_travel.get(name,0)+math.dist(position,previous_actors[name])
                        previous_actors[name]=position
                        if actor['parked']:continue
                        network=next(o for o in get_config_scene['objects'] if o['id']==name)
                        path=next(n['points'] for n in get_config_scene['networks'] if n['id']==network['path_id']) if actor['kind']=='person' else rounded_loop(DISTRICTS[network['district']])
                        x,y=position[:2];yaw=actor['yaw'];body=DIMENSIONS[actor['kind']];width=1.1 if actor['kind']=='person' else 5.
                        excess=max(project(path,[x+dx*math.cos(yaw)-dy*math.sin(yaw),y+dx*math.sin(yaw)+dy*math.cos(yaw)])[0]-width for dx in (-body[0]/2,body[0]/2) for dy in (-body[1]/2,body[1]/2))
                        footprints[name]=max(footprints.get(name,0.),excess)
                signature=(state['state'],tuple(d['state'] for d in selected))
                if signature!=last or time.monotonic()-start-last_print>10:
                    if signature!=last:
                        for d in selected:
                            if previous_phases.get(d['id'])!=d['state']:
                                camera_pool.submit(capture,d['id'],d['state'],state['sim_time'])
                            previous_phases[d['id']]=d['state']
                    print(json.dumps({'wall_seconds':round(time.monotonic()-start,1),'sim_time':state['sim_time'],'mission':state['state'],'runtime':state['runtime']['progress'],
                                      'drones':[{k:d[k] for k in ('id','state','ready','armed','tag_error','extension')} for d in selected]}),flush=True)
                    last=signature;last_print=time.monotonic()-start
                if state['state']=='READY' and all(d['ready'] for d in selected) and not started:
                    command('start',state);started=True
                if state['state'] in ('FAULT','ERROR','ABORTED') or state['state']=='COMPLETE' and state['sim_time']>=args.extended_seconds:break
                # Mission authority logs at 2 Hz; this observer need not add
                # ten expensive fleet snapshots per second to a loaded host.
                time.sleep(.5)
        import statistics
        result.update(final=state,wall_seconds=round(time.monotonic()-start,2),actor_travel_m=actor_travel,maximum_footprint_excess_m=footprints,median_rtf=statistics.median(rtfs),maximum_airborne_telemetry_age=max(telemetry_ages,default=None),maximum_landing_image_age=max(landing_ages,default=None),maximum_descending_image_age=max(servo_ages,default=None),
                      passed=state['state']=='COMPLETE' and all(d['state']=='DOCKED' and not d['armed'] and d['latched'] and d['extension']<.03 for d in selected)
                      and (not args.target or bool(state['catalogue'] if args.city else state['tracks'])) and (not args.city or not state['city']['contact_events'] and not state['city']['actor_contacts'] and not state['city']['violations'] and not state['city']['crossing_violations'] and max(footprints.values(),default=0)<.1))
    except Exception as exc:result['error']=str(exc)
    finally:
        camera_pool.shutdown(wait=True)
        (out/'camera-captures.json').write_text(json.dumps(captures,indent=2))
        native_completed=result['passed']
        if args.city:result['passed']=False;result['city_evaluation_pending']=True
        (out/'result.json').write_text(json.dumps(result,indent=2))
        import shutil
        if (ROOT/'.runtime/logs').is_dir():shutil.copytree(ROOT/'.runtime/logs',out/'runtime-logs',dirs_exist_ok=True)
        # Only the generated test run is reset; the original paused run was
        # explicitly reset by the operator before this script was started.
        try:
            command('reset',get('state'))
            restored=client.put('/api/config',json=original);restored.raise_for_status();result['original_mission_restored']=True
        except Exception as exc:result['restore_error']=str(exc)
        if args.city:
            from evaluate_fleet_evidence import evaluate
            measured=evaluate(out);result.update(measured);result['passed']=native_completed and measured['passed'];result['city_evaluation_pending']=False
        (out/'result.json').write_text(json.dumps(result,indent=2));client.close()
        print('EVIDENCE',str(out),'PASS' if result['passed'] else 'FAIL',flush=True)
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
