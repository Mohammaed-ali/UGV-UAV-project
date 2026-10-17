"""Native camera/depth close-hold gate through the running browser API.

Actor truth is used only for the evaluator's clearance metric. It never enters
the flight controller, image detector, registry or depth approach controller.
"""
import json,time,uuid,math,sys,urllib.request,urllib.error
from pathlib import Path
ROOT=Path('/home/mohammed-ali/Downloads/gpt /Simulation')
sys.path.insert(0,str(ROOT))
from backend.city import DIMENSIONS

BASE='http://127.0.0.1:8765'
def api(path,body=None,method=None):
    data=json.dumps(body).encode() if body is not None else None
    r=urllib.request.Request(BASE+'/api/'+path,data=data,method=method,
          headers={'Content-Type':'application/json','Origin':BASE})
    try:
        with urllib.request.urlopen(r,timeout=20) as response:return json.load(response)
    except urllib.error.HTTPError as error:raise RuntimeError(error.read().decode()) from error

def main():
    original=api('config')['mission'];initial=api('state')
    if initial['runtime']['state']!='offline':raise SystemExit('A runtime is already active; no test was started.')
    out=ROOT/'artifacts/close-approach'/('native-'+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
    (out/'original-mission.json').write_text(json.dumps(original,indent=2))
    m={**original,'living_city':True,'city_scenario':'moving-vehicle','population':0,'traffic':1,
       'actor_placements':[],'target_class':'vehicle','target_classes':['vehicle'],'aerial_vehicles':True,
       'target_present':True,'wheels':4,'walking_speed':.3,'traffic_speed':.3,'flight_speed':3.,
       'ugv_speed':1.5,'altitude':12.,'tracking_altitude':12.,'tracking_seconds':240.,
       'tracking_distance':1.,'reacquire_seconds':30.,'search_timeout':90.,'observation_seconds':20.,
       'no_target_policy':'return','approach_clearance':.5,'approach_speed':.4,
       'start':{'x':30.,'y':31.5},
       'stops':[{'id':'close-test','label':'Close approach test','x':30.,'y':34.5,
                 'drones':['uav01'],'search_radius':20.,'target_class':None,'search_timeout':None,'loiter_seconds':None}]}
    result={'passed':False,'mission':m,'phase':'starting','native_clearance_samples':0,
            'minimum_evaluated_aircraft_envelope_gap_m':None,'held_seconds':0.,'selected_id':None}
    started=time.monotonic();tracking=False;closing=False;backoff=False;recalling=False
    last=None;last_log=-1;hold_at=None;clearances=[];last_state=initial;run_id=None
    def command(name,**kw):return api('command',{'name':name,'request_id':str(uuid.uuid4()),'run_id':run_id,**kw})
    try:
        api('config',m,'PUT');run_id=api('state')['run_id'];command('initialize')
        with (out/'telemetry.jsonl').open('w') as log:
            while time.monotonic()-started<420:
                s=api('state');last_state=s;now=s['sim_time'];d=s['drones'][0];f=s['tracking'];close=f.get('close_approach',{})
                signature=(s['state'],d['state'],f['state'],close.get('state'))
                if signature!=last:
                    last=signature;print(json.dumps({'sim_time':now,'mission':signature[0],'uav':signature[1],'tracking':signature[2],'close':signature[3],'reason':close.get('reason')}),flush=True)
                    if closing and signature[3] in ('APPROACHING','HOLDING','RETREATING','CANCELLED'):
                        try:
                            with urllib.request.urlopen(BASE+'/api/camera/uav01?raw=true',timeout=5) as r:image=r.read()
                            if image:(out/f'{now:.2f}-{signature[3].lower()}.jpg').write_bytes(image)
                        except Exception:pass
                if s['state']=='READY' and d['ready'] and s['perception']['detector_ready'] and s['perception']['tag_ready']:command('start')
                eligible=s['state']=='DEPLOYING' and d['state'] in ('TAKEOFF','SEARCHING','OBSERVING','HOVERING','LOITERING','RETURNING')
                rows=[t for t in s['catalogue'] if t['class'] in ('vehicle','car','truck','bus') and t['age']<=.5]
                if eligible and rows and not tracking:
                    t=max(rows,key=lambda t:t['last_seen']);command('track_start',target_id=t['id']);tracking=True;result['selected_id']=t['id']
                t=next((t for t in s['catalogue'] if t['id']==f.get('target_id')),None)
                if tracking and not closing and f['state']=='TRACKING' and f.get('elapsed',0)>=2 and t and t['age']<=.5 and not t['ambiguous']:
                    try:command('approach_start',clearance_m=.5);closing=True;result['phase']='approaching'
                    except RuntimeError:pass
                if closing:
                    actual=next((a for a in (s.get('city') or {}).get('actors',[]) if a['id']=='vehicle_0'),None)
                    if actual:
                        dx=d['position'][0]-actual['position'][0];dy=d['position'][1]-actual['position'][1];yaw=actual['yaw']
                        local=[dx*math.cos(yaw)+dy*math.sin(yaw),-dx*math.sin(yaw)+dy*math.cos(yaw),d['position'][2]-actual['position'][2]]
                        size=DIMENSIONS[actual['kind']]
                        gap=math.sqrt(max(0.,abs(local[0])-size[0]/2)**2+max(0.,abs(local[1])-size[1]/2)**2+max(0.,local[2]-size[2],-local[2])**2)-.5
                        clearances.append(gap)
                    if close.get('measured_clearance_m') is not None:result['native_clearance_samples']+=1
                    if close.get('state')=='HOLDING':
                        if hold_at is None:hold_at=now
                        result['held_seconds']=max(result['held_seconds'],now-hold_at)
                        if now-hold_at>=8 and not backoff:command('approach_stop');backoff=True;result['phase']='backing-off'
                    elif hold_at is not None and not backoff:hold_at=None
                    if close.get('state')=='CANCELLED' and not recalling:
                        result['close_hold_reached']=result['held_seconds']>=2
                        if not backoff:result['close_failure']=close.get('reason');result['phase']='close-cancelled'
                        command('track_stop');recalling=True
                if now-last_log>=.5:
                    last_log=now;log.write(json.dumps({'time':now,'state':s['state'],'drone':{k:d.get(k) for k in ('state','position','estimated_position','armed','latched','telemetry_age')},'tracking':f,'target':t,'vision_debug':s['perception'].get('visual_tracking'),'depth_debug':s['perception'].get('performance',{}).get('depth_continuity')})+'\n');log.flush()
                if recalling and s['state']=='COMPLETE':break
                if s['state'] in ('FAULT','ERROR'):result['fault']=s['events'][-5:];break
                time.sleep(.1)
        result.update(wall_seconds=round(time.monotonic()-started,2),final_state=last_state['state'],
                      recovered=last_state['drones'][0]['state']=='DOCKED' and last_state['drones'][0]['latched'] and not last_state['drones'][0]['armed'],
                      minimum_evaluated_aircraft_envelope_gap_m=min(clearances,default=None),final_close=last_state['tracking'].get('close_approach'))
        result['passed']=bool(backoff and result['held_seconds']>=8 and result.get('close_hold_reached') and result['recovered'] and result['native_clearance_samples']>4 and min(clearances,default=0)>=.5)
    except Exception as e:
        result['error']=str(e);print('VALIDATION ERROR: '+str(e),flush=True)
    finally:
        (out/'result.json').write_text(json.dumps(result,indent=2))
        try:
            command('reset');api('config',original,'PUT');result['original_configuration_restored']=True
        except Exception as e:result['restore_error']=str(e)
        (out/'result.json').write_text(json.dumps(result,indent=2))
        print(json.dumps({'result_path':str(out/'result.json'),'passed':result['passed'],'held_seconds':result['held_seconds'],'recovered':result.get('recovered'),'minimum_gap':result.get('minimum_evaluated_aircraft_envelope_gap_m'),'error':result.get('error')}),flush=True)
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
