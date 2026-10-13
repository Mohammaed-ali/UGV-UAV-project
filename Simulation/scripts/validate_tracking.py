"""Camera discovery, operator selection and native PX4 follow/recovery gate.

Actor truth is read only by the evaluator after camera selection, never sent to
the detector, registry or follow controller.
"""
import sys,time,json,uuid,argparse,math,statistics,shutil,psutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.config import Mission,Stop,Point
from backend.runtime import Runtime
from backend.vision import Vision
from backend.mission import Engine

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--class',dest='target_class',default='person',choices=['person','vehicle','car','truck','bus']);parser.add_argument('--camera-drop',action='store_true');parser.add_argument('--scenario',default='custom');parser.add_argument('--after-survey',action='store_true');parser.add_argument('--confirm-candidates',action='store_true',help='Exercise the operator confirmation command for a fresh visual candidate');parser.add_argument('--expect-ambiguity',action='store_true');parser.add_argument('--expected-outcome',choices=['finished','lost','left-area'],default='finished');parser.add_argument('--duration',type=float,default=45);parser.add_argument('--wheels',type=int,default=4);args=parser.parse_args()
    if args.scenario=='custom':args.scenario='walking-person' if args.target_class=='person' else 'moving-vehicle'
    m=Mission(living_city=True,city_scenario=args.scenario,early_selection=not args.after_survey,wheels=args.wheels,population=(2 if args.scenario=='similar-people' else 1) if args.target_class=='person' else 0,traffic=0 if args.target_class=='person' else {'vehicle':1,'car':1,'truck':2,'bus':3}[args.target_class],
              start=Point(x=30,y=31.5),stops=[Stop(id='city',label='City survey',x=30,y=34.5,drones=['uav01'],search_radius=12 if args.target_class=='person' else 20)],
              confidence=.3 if args.expect_ambiguity else .4,target_class=args.target_class,altitude=9 if args.target_class=='person' else 15 if args.target_class=='bus' else 12,flight_speed=3.,walking_speed=1.2,traffic_speed=1.6,search_timeout=90,observation_seconds=20,
              no_target_policy='return',tracking_seconds=args.duration,reacquire_seconds=8 if args.camera_drop else 60,tracking_altitude=15 if args.target_class=='bus' else 12,tracking_distance=1.5 if args.target_class=='bus' else 3.)
    out=ROOT/'artifacts/living-city'/('tracking-'+str(uuid.uuid4()));out.mkdir(parents=True)
    runtime=Runtime(ROOT);vision=Vision(ROOT,runtime);engine=Engine(ROOT,runtime,vision);engine.configure(m)
    result={'passed':False,'mission':m.model_dump(),'selection_mode':'after-survey' if args.after_survey else 'early','thresholds':{'minimum_fresh_tracking_samples':20,'maximum_median_follow_distance_m':8.,'identity_switches':0,'carrier_contacts':0,'minimum_geometric_visible_coverage':.5 if args.target_class!='person' else .8}}
    wall=time.monotonic();last_state=None;last_log=-1;selected=False;started=False;eval_actor=None;follow_distances=[];fresh_ages=[];tracking_ids=set();last_print=-10;poses_first={};motion={};center_errors=[];telemetry_ages=[];rtfs=[];tracking_samples=0;last_perf=0;processes={};peak_rss=0;cpu_samples=[];final={};drone={};initial_bytes=sum(p.stat().st_size for p in (ROOT/'artifacts/runs').glob('**/*') if p.is_file())
    try:
        engine.command('initialize')
        with (out/'telemetry.jsonl').open('w') as log:
            while time.monotonic()-wall<600:
                engine.tick();now=engine.now();state=engine.snapshot()
                if time.monotonic()-last_perf>2:
                    last_perf=time.monotonic();rss=0;cpu=0
                    for proc in [psutil.Process(),*psutil.Process().children(recursive=True)]:
                        try:
                            if proc.pid not in processes:processes[proc.pid]=proc;proc.cpu_percent()
                            rss+=proc.memory_info().rss;cpu+=processes[proc.pid].cpu_percent()
                        except psutil.Error:pass
                    peak_rss=max(peak_rss,rss);cpu_samples.append(cpu)
                if state['state']=='READY' and state['drones'][0]['ready'] and vision.detector_ready and vision.tag_ready:engine.command('start')
                if args.camera_drop and selected and engine.follow and engine.follow.tracking_started is not None and now-engine.follow.tracking_started>12 and not result.get('camera_fault_injected'):
                    runtime.gz.camera('uav01',False);vision.searching.discard('uav01');result['camera_fault_injected']=now
                rows=[t for t in state['catalogue'] if t['class']==args.target_class or args.target_class=='vehicle' and t['class'] in ('car','truck','bus')]
                eligible=(state['state']=='COMPLETE') if args.after_survey else (state['state']=='DEPLOYING' and state['drones'][0]['state'] in ('TAKEOFF','SEARCHING','OBSERVING','HOVERING','LOITERING','RETURNING'))
                if eligible and rows and not selected:
                    chosen=max(rows,key=lambda t:t['last_seen']);click_wall=time.monotonic();engine.start_tracking(chosen['id']);selected=True;result['selected_id']=chosen['id'];result['selection_age']=chosen['age'];result['track_click_wall_ms']=round((time.monotonic()-click_wall)*1000,2);result['state_at_click']=engine.follow.state;result['follow_started_at_click']=engine.follow.tracking_started;result['clicked_at_sim_time']=now
                if (args.after_survey or args.confirm_candidates) and selected and state['tracking']['candidates']:
                    candidate=state['tracking']['candidates'][0];engine.confirm_target(candidate['id']);result.setdefault('operator_confirmations',[]).append({'time':now,'candidate':candidate})
                signature=(state['state'],state['drones'][0]['state'],state['tracking']['state'])
                if signature!=last_state:
                    last_state=signature;print(json.dumps({'sim_time':now,'mission':signature[0],'uav':signature[1],'tracking':signature[2],'catalogue':len(rows),'vision_error':vision.error}),flush=True)
                    image=vision.annotated.get('uav01')
                    if image:(out/f'{now:.2f}-{signature[1].lower()}.jpg').write_bytes(image)
                if now-last_print>=10:
                    last_print=now
                    image=vision.raw.get('uav01')
                    if image:(out/f'{now:.2f}-raw.jpg').write_bytes(image)
                    print(json.dumps({'sim_time':now,'camera_age':now-vision.object_latest.get('uav01',{}).get('time',now),'pose_source':vision.object_latest.get('uav01',{}).get('pose_source'),'rtf':state['physics']['real_time_factor']}),flush=True)
                if now-last_log>=.5:
                    last_log=now;log.write(json.dumps(state)+'\n');log.flush()
                    for actor in (state.get('city') or {}).get('actors',[]):
                        poses_first.setdefault(actor['id'],actor['position']);motion[actor['id']]=engine.city.actors[actor['id']]['distance']
                    rtfs.append(state['physics']['real_time_factor']);telemetry_ages.append(state['drones'][0]['telemetry_age'] or 0.)
                    if state['tracking']['state'] in ('TRACKING','OCCLUDED','SEARCHING'):tracking_samples+=1
                    if state['tracking']['state']=='TRACKING':
                        target=next((t for t in rows if t['id']==state['tracking']['target_id']),None)
                        if target:
                            tracking_ids.add(target['id']);fresh_ages.append(target['age']);x,y,w,h=target['box'];center_errors.append(math.hypot(x+w/2-320,y+h/2-240))
                            actors=[a for a in state['city']['actors'] if a['kind']==args.target_class or args.target_class=='vehicle' and a['kind'] in ('car','truck','bus')]
                            if eval_actor is None and actors:
                                truth=min(actors,key=lambda a:math.dist(a['position'][:2],target['position'][:2]));eval_actor=truth['id'];result['evaluation_class']=truth['kind'];result['detected_class']=target['class'];result['subclass_correct']=truth['kind']==target['class']
                            actual=next((a for a in actors if a['id']==eval_actor),None)
                            if actual:follow_distances.append(math.dist(state['drones'][0]['position'][:2],actual['position'][:2]))
                if selected and engine.state=='COMPLETE' and engine.follow and engine.follow.state=='DOCKED':break
                if engine.state in ('ERROR','FAULT') or engine.hold:break
                if engine.state=='COMPLETE' and not rows and not selected:break
                time.sleep(.04)
        final=engine.snapshot();drone=final['drones'][0]
        result.update(final=final,wall_seconds=round(time.monotonic()-wall,2),fresh_tracking_samples=len(fresh_ages),maximum_tracking_image_age=max(fresh_ages,default=None),
                      median_follow_distance=statistics.median(follow_distances) if follow_distances else None,tracking_ids=list(tracking_ids),evaluation_actor=eval_actor,actor_travel_m=motion,tracking_fresh_fraction=len(fresh_ages)/max(1,tracking_samples),median_image_center_error_px=statistics.median(center_errors) if center_errors else None,peak_owned_rss_mib=round(peak_rss/1048576,1),median_cpu_percent=statistics.median(cpu_samples) if cpu_samples else None,median_rtf=statistics.median(rtfs) if rtfs else None,maximum_telemetry_age=max(telemetry_ages,default=None),native_storage_growth_bytes=sum(p.stat().st_size for p in (ROOT/'artifacts/runs').glob('**/*') if p.is_file())-initial_bytes)
        result['passed']=selected and final['state']=='COMPLETE' and drone['state']=='DOCKED' and not drone['armed'] and drone['latched'] and len(fresh_ages)>=20 and tracking_ids.issubset({result.get('selected_id'),*[c['candidate']['id'] for c in result.get('operator_confirmations',[])]}) and result['median_follow_distance']<8 and not final['city']['contact_events'] and final['tracking']['outcome']==('lost' if args.camera_drop else args.expected_outcome)
    except Exception as exc:result['error']=str(exc);import traceback;traceback.print_exc()
    finally:
        vision.close();runtime.stop()
        result['native_storage_growth_bytes']=sum(p.stat().st_size for p in (ROOT/'artifacts/runs').glob('**/*') if p.is_file())-initial_bytes
        (out/'result.json').write_text(json.dumps(result,indent=2))
        from evaluate_tracking_evidence import evaluate
        evaluation=evaluate(out);result['evaluation']=evaluation
        if evaluation and result['passed']:
            result['passed']=not evaluation['truth_identity_switches'] and not evaluation['false_reacquisitions'] and (args.camera_drop or evaluation['geometric_visible_tracking_coverage']>=result['thresholds']['minimum_geometric_visible_coverage'])
        if args.expect_ambiguity and evaluation and final:
            closest=float('inf');confirmed=0
            for line in (out/'telemetry.jsonl').open():
                row=json.loads(line);actors=(row.get('city') or {}).get('actors',[])
                if len(actors)>=2:closest=min(closest,math.dist(actors[0]['position'][:2],actors[1]['position'][:2]))
                confirmed=max(confirmed,len(row['catalogue']))
            result['similar_person_closest_separation_m']=closest;result['confirmed_candidates']=confirmed
            result['passed']=selected and final['state']=='COMPLETE' and drone['state']=='DOCKED' and not drone['armed'] and drone['latched'] and closest<2.5 and confirmed>=2 and evaluation['ambiguous_samples']>=2 and not evaluation['truth_identity_switches'] and not evaluation['false_reacquisitions'] and not evaluation['unconfirmed_perception_id_changes'] and not final['city']['contact_events'] and not final['city']['actor_contacts']
            result['gate']='Ambiguity rejection and safe recovery; continuous follow is not required for lookalikes.'
        (out/'result.json').write_text(json.dumps(result,indent=2))
        shutil.copytree(ROOT/'.runtime/logs',out/'runtime-logs',dirs_exist_ok=True);print('EVIDENCE',out,'PASS' if result['passed'] else 'FAIL',flush=True)
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
