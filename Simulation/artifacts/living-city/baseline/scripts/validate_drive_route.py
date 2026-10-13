"""Drive the saved edited route in Gazebo with the full rack payload, no flights."""
import json,time,uuid,shutil
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]

def main():
    client=httpx.Client(base_url='http://127.0.0.1:8765',timeout=90)
    def get(path):
        r=client.get('/api/'+path);r.raise_for_status();return r.json()
    def command(name,state):
        r=client.post('/api/command',json={'name':name,'run_id':state['run_id'],'request_id':str(uuid.uuid4())});r.raise_for_status()
    state=get('state')
    if state['runtime']['state']!='offline':raise SystemExit('Route validation requires an idle owned runtime.')
    original=get('config')['mission'];mission={**original,'name':'Edited route · physical clearance validation',
        'stops':[{**s,'drones':[]} for s in original['stops']]}
    r=client.put('/api/config',json=mission);r.raise_for_status();state=get('state')
    folder=ROOT/f'artifacts/route-validation-{state["run_id"]}';folder.mkdir(parents=True)
    (folder/'original-mission.json').write_text(json.dumps(original,indent=2))
    (folder/'config.json').write_text(json.dumps(get('config'),indent=2))
    start=time.monotonic();started=False;visited=set();held=False;last=None
    result={'run_id':state['run_id'],'passed':False,'payload':'All eight aircraft physically stored and latched; no PX4 flights'}
    try:
        command('initialize',state)
        with (folder/'telemetry.jsonl').open('w') as output:
            while time.monotonic()-start<600:
                state=get('state');output.write(json.dumps(state)+'\n');output.flush()
                visited.add(state['stop_index']);held|=state['hold']
                signature=(state['state'],state['stop_index'],state['hold'])
                if signature!=last:
                    print(json.dumps({'time':state['sim_time'],'state':state['state'],'stop':state['stop_index'],'position':state['carrier']['position'],'hold':state['hold']}),flush=True);last=signature
                if state['state']=='READY' and not started:command('start',state);started=True
                if state['state'] in ('COMPLETE','FAULT','ERROR') or state['hold']:break
                time.sleep(.5)
        goal=mission['stops'][-1];position=state['carrier']['position']
        distance=((position[0]-goal['x'])**2+(position[1]-goal['y'])**2)**.5
        result.update(final=state,stops_observed=sorted(visited),final_goal_distance_m=distance,wall_seconds=round(time.monotonic()-start,2),
            passed=state['state']=='COMPLETE' and not held and len(visited)==len(mission['stops']) and distance<.5
            and all(d['latched'] and not d['armed'] for d in state['drones']))
    except Exception as error:result['error']=str(error)
    finally:
        if (ROOT/'.runtime/logs').is_dir():shutil.copytree(ROOT/'.runtime/logs',folder/'runtime-logs',dirs_exist_ok=True)
        try:
            command('reset',get('state'));r=client.put('/api/config',json=original);r.raise_for_status();result['original_mission_restored']=True
        except Exception as error:result['restore_error']=str(error)
        (folder/'result.json').write_text(json.dumps(result,indent=2));client.close()
        print('EVIDENCE',str(folder),'PASS' if result['passed'] else 'FAIL',flush=True)
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
