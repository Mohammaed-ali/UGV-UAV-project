"""Native city / carrier gate, without PX4 flight or detector load."""
import sys,time,json,uuid,argparse,math,statistics,shutil
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.config import Mission,Stop
from backend.runtime import Runtime
from backend.mission import Engine

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fault',action='store_true');parser.add_argument('--seconds',type=float,default=130);parser.add_argument('--wheels',type=int,default=4);parser.add_argument('--single-bay',action='store_true');args=parser.parse_args()
    m=Mission(living_city=True,tracking_enabled=False,wheels=args.wheels,stops=[
        Stop(id='a',label='Alpha',x=-12,y=-22),Stop(id='b',label='Bravo',x=28,y=-24),Stop(id='c',label='Charlie',x=29.5,y=34.5)])
    if args.single_bay:m=Mission(living_city=True,tracking_enabled=False,wheels=args.wheels,stops=[Stop(id='bay',label='Crowded fleet bay',x=-24,y=-22)])
    out=ROOT/'artifacts/living-city'/('city-'+str(uuid.uuid4()));out.mkdir(parents=True)
    runtime=Runtime(ROOT);runtime.render_cameras=False;vision=SimpleNamespace(confidence=.4,detector_ready=True,tag_ready=True,error=None,latest={},searching=set())
    engine=Engine(ROOT,runtime,vision);engine.configure(m);result={'passed':False,'mission':m.model_dump(),'thresholds':{'maximum_lane_error_m':1.,'minimum_actor_travel_m':3.,'carrier_contact_count':0},'wheels':args.wheels}
    start=time.monotonic();last_print=-10;last_log=-1;initial={};max_errors={};distances={};pause_checked=False;rtfs=[];footprints={};fault_at=None;initial_carrier=None
    try:
        engine.command('initialize')
        with (out/'telemetry.jsonl').open('w') as log:
            while time.monotonic()-start<args.seconds*3+70:
                engine.tick();now=engine.now()
                if engine.state=='READY':engine.command('start')
                if args.fault and now>12 and fault_at is None:
                    from gz.msgs10.pose_pb2 import Pose
                    from gz.msgs10.boolean_pb2 import Boolean
                    carrier=runtime.gz.poses['carrier'];q=carrier['position'];yaw=carrier['yaw'];p=Pose(name='person_0');p.position.x=q[0]+4.*math.cos(yaw);p.position.y=q[1]+4.*math.sin(yaw);p.position.z=.02;p.orientation.w=1.
                    injection_started=time.monotonic()
                    # A long synchronous transport wait blocks this Python mission
                    # loop while Gazebo keeps moving. Bound the deliberate test
                    # injection; actual measured intrusion is the stop trigger.
                    acknowledged,_=runtime.gz.node.request('/world/fieldlab/set_pose',p,Pose,Boolean,50)
                    fault_at=now;initial_carrier=q;result['fault_injection']={'time':now,'actor':'person_0','position':[p.position.x,p.position.y],'request_wall_seconds':time.monotonic()-injection_started,'request_acknowledged':acknowledged}
                if now-last_log>.5:
                    last_log=now;state=engine.snapshot();log.write(json.dumps(state)+'\n');log.flush()
                    for actor in (state.get('city') or {}).get('actors',[]):
                        initial.setdefault(actor['id'],actor['position']);max_errors[actor['id']]=max(max_errors.get(actor['id'],0),actor['lane_error'])
                        distances[actor['id']]=engine.city.actors[actor['id']]['distance']
                        if actor['parked']:continue
                        from backend.city import project,DIMENSIONS,rounded_loop,DISTRICTS
                        body=DIMENSIONS[actor['kind']];yaw=actor['yaw'];x,y=actor['position'][:2]
                        center=engine.city.paths[engine.city.actors[actor['id']]['path_id']] if actor['kind']=='person' else rounded_loop(DISTRICTS[engine.city.actors[actor['id']]['district']])
                        width=1.1 if actor['kind']=='person' else 5.
                        excess=max(project(center,[x+dx*math.cos(yaw)-dy*math.sin(yaw),y+dx*math.sin(yaw)+dy*math.cos(yaw)])[0]-width for dx in (-body[0]/2,body[0]/2) for dy in (-body[1]/2,body[1]/2))
                        footprints[actor['id']]=max(footprints.get(actor['id'],0.),excess)
                    rtfs.append(state['physics']['real_time_factor'])
                if now-last_print>=10:
                    last_print=now;print(json.dumps({'sim_time':round(now,2),'state':engine.state,'max_lane_error':max(max_errors.values(),default=0),'rtf':runtime.gz.rtf if runtime.gz else 0}),flush=True)
                if now>30 and not pause_checked:
                    runtime.gz.pause(True);time.sleep(.5);before={k:p['position'][:] for k,p in runtime.gz.poses.items()};stamp=now;time.sleep(1)
                    after={k:p['position'][:] for k,p in runtime.gz.poses.items()};result['pause_displacement']=max((math.dist(v,after[k]) for k,v in before.items() if k in after),default=0)
                    runtime.gz.pause(False);pause_checked=True
                if engine.state in ('ERROR','FAULT') or engine.hold or now>=args.seconds:break
                time.sleep(.04)
        if args.fault and engine.hold:
            deadline=time.monotonic()+1.5
            while time.monotonic()<deadline:engine.tick();time.sleep(.05)
        result.update(final=engine.snapshot(),wall_seconds=round(time.monotonic()-start,2),maximum_lane_errors=max_errors,actor_travel_m=distances,maximum_footprint_excess_m=footprints,median_rtf=statistics.median(rtfs) if rtfs else None)
        if engine.city is None:raise RuntimeError(runtime.error or 'City telemetry did not become ready.')
        moving=[o['id'] for o in engine.city.layout['objects'] if o['kind']!='building' and not o['parked']]
        result['destination_error_m']=math.dist(runtime.gz.poses['carrier']['position'][:2],[m.stops[-1].x,m.stops[-1].y])
        result['passed']=result['destination_error_m']<.6 and engine.state=='COMPLETE' and not engine.hold and not engine.city.violations and not runtime.gz.city_contacts and not engine.city.crossing_violations and (args.seconds<400 or engine.city.crossing_passes>0) and not runtime.gz.actor_contacts and max(footprints.values(),default=0)<.1 and result.get('pause_displacement',999)<.001 and all(distances.get(k,0)>3 for k in moving)
        if args.fault:result['passed']=engine.hold and abs((runtime.gz.odom or {}).get('speed',999))<.04 and not runtime.gz.city_contacts and fault_at is not None and math.dist(runtime.gz.poses['carrier']['position'],initial_carrier)<.8;result['controlled_stop_displacement']=math.dist(runtime.gz.poses['carrier']['position'],initial_carrier) if initial_carrier else None
    except Exception as error:result['error']=str(error);import traceback;traceback.print_exc()
    finally:
        (out/'result.json').write_text(json.dumps(result,indent=2));shutil.copytree(ROOT/'.runtime/logs',out/'runtime-logs',dirs_exist_ok=True);runtime.stop();print('EVIDENCE',out,'PASS' if result['passed'] else 'FAIL',flush=True)
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
