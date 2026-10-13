import json,time,uuid
from pathlib import Path
import httpx

root=Path('/home/mohammed-ali/Downloads/gpt /Simulation')
out=root/'artifacts/deployment-reset-cc4832ea-18fa-4c4a-ae6c-9c7262ef045f'
expected=json.loads((out/'mission.json').read_text())
client=httpx.Client(base_url='http://127.0.0.1:8765',timeout=30)
def get(path):
    response=client.get('/api/'+path);response.raise_for_status();return response.json()
def command(name,state):
    response=client.post('/api/command',json={'name':name,'run_id':state['run_id'],'request_id':str(uuid.uuid4())})
    response.raise_for_status();return response.json()
state=get('state');mission=get('config')['mission']
assert mission==expected,'Saved mission differs from the preserved operator plan'
assert state['runtime']['state']=='offline','An existing runtime must be preserved'
run=state['run_id'];selected=mission['stops'][0]['drones']
initial_z={d['id']:d['position'][2] for d in state['drones']}
result={'run_id':run,'previous_run':'cc4832ea-18fa-4c4a-ae6c-9c7262ef045f','mission_preserved':True,
        'physical_takeoffs':{},'passed':False,'scope':'Launch all three aircraft at the first stop after a fault/reset; keep the operator mission running.'}
command('initialize',state);start=time.monotonic();started=False;last=None;last_print=-10
try:
    with (out/'after-fix-telemetry.jsonl').open('w') as telemetry:
        while time.monotonic()-start<300:
            state=get('state');assert state['run_id']==run,'Operator changed the run during verification'
            telemetry.write(json.dumps(state)+'\n');telemetry.flush()
            first=[d for d in state['drones'] if d['id'] in selected]
            signature=(state['state'],tuple(d['state'] for d in first),state['runtime']['progress'])
            if signature!=last or time.monotonic()-start-last_print>=10:
                print(json.dumps({'wall_seconds':round(time.monotonic()-start,1),'sim_time':state['sim_time'],
                    'mission':state['state'],'runtime':state['runtime']['progress'],
                    'drones':[{k:d[k] for k in ('id','state','ready','armed','latched','position','extension')} for d in first]}),flush=True)
                last=signature;last_print=time.monotonic()-start
            assigned={d for stop in mission['stops'] for d in stop['drones']}
            if state['state']=='READY' and all(d['ready'] for d in state['drones'] if d['id'] in assigned) and not started:
                command('start',state);started=True
            for d in first:
                if d['measured'] and d['armed'] and not d['latched'] and d['position'][2]>initial_z[d['id']]+2:
                    result['physical_takeoffs'].setdefault(d['id'],{'sim_time':state['sim_time'],'initial_z':initial_z[d['id']],
                        'measured_position':d['position'],'mode':d['mode'],'state':d['state'],'armed':True,'latched':False})
            if all(d in result['physical_takeoffs'] for d in selected):
                result['passed']=True;break
            if state['state'] in ('FAULT','ERROR','ABORTED','COMPLETE'):
                result['error']='Mission ended before all scheduled first-stop aircraft achieved measured takeoff';break
            time.sleep(.3)
    result.update(final=state,wall_seconds=round(time.monotonic()-start,2))
    if not result['passed'] and 'error' not in result:result['error']='Takeoff verification timed out'
except Exception as exc:result['error']=str(exc)
finally:
    (out/'after-fix-result.json').write_text(json.dumps(result,indent=2));client.close()
    print('PHYSICAL DEPLOYMENT', 'PASS' if result['passed'] else 'FAIL',str(out),flush=True)
raise SystemExit(0 if result['passed'] else 1)
