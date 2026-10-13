"""Scheduler stress test using captured pixels, not a physical-flight acceptance test."""
import json,sys,time,threading,urllib.request
from pathlib import Path
from types import SimpleNamespace
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.vision import Vision

def main():
    root=Path(__file__).resolve().parents[1]
    out=root/'artifacts/landing-vision-replay';out.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen('http://127.0.0.1:8765/api/state') as response:captured=json.load(response)
    frames={};poses={}
    for did in ('uav01','uav02','uav03'):
        with urllib.request.urlopen(f'http://127.0.0.1:8765/api/camera/{did}?raw=true') as response:data=response.read()
        if not data:raise RuntimeError(f'No captured camera image for {did}.')
        (out/f'{did}-captured.jpg').write_bytes(data)
        frames[did]=cv2.imdecode(np.frombuffer(data,dtype=np.uint8),cv2.IMREAD_COLOR)
        d=next(d for d in captured['drones'] if d['id']==did)
        poses[did]={'position':d['position'],'quaternion':d['quaternion']}
    gz=SimpleNamespace(lock=threading.RLock(),camera_packets={},sim_time=0.)
    runtime=SimpleNamespace(gz=gz);vision=Vision(root,runtime);vision.landing.add('uav01')
    ages=[];latencies=[];seen=set();matches=set();start=time.monotonic();next_image=0.;samples=[]
    try:
        while time.monotonic()-start<15:
            elapsed=time.monotonic()-start;gz.sim_time=elapsed
            if elapsed>=next_image:
                next_image=elapsed+.1
                with gz.lock:
                    for did,frame in frames.items():
                        gz.camera_packets[did]={'image':frame,'pose':poses[did],'time':elapsed,'sync_error':0.,'received':time.monotonic()}
            obs=vision.tag_latest.get('uav01')
            if obs and elapsed>3:
                age=gz.sim_time-obs['time'];ages.append(age);latencies.append(obs['latency_ms']);seen.add(obs['time'])
                if any(t['id']==1 for t in obs['tags']):matches.add(obs['time'])
                samples.append({'elapsed':round(elapsed,4),'landing_image_age':round(age,4),'tag_ids':[t['id'] for t in obs['tags']]})
            time.sleep(.01)
        report={'scheduling_only':True,'live_flight_validation':False,'source_run':captured['run_id'],
                'source':'Captured Gazebo camera JPEGs; pixels and recorded poses reused at controlled 10 Hz timestamps.',
                'camera_count':3,'duration_seconds':15,'samples':len(ages),'unique_landing_frames':len(seen),'assigned_tag_frames':len(matches),
                'age_max_seconds':round(max(ages),4) if ages else None,'age_p99_seconds':round(float(np.percentile(ages,99)),4) if ages else None,
                'tag_inference_p99_ms':round(float(np.percentile(latencies,99)),2) if latencies else None,
                'stale_samples':sum(age>=.5 for age in ages),'object_inference_ms':{did:obs.get('latency_ms') for did,obs in vision.object_latest.items()},
                'error':vision.error,'passed':len(seen)>50 and len(matches)>50 and bool(ages) and max(ages)<.5 and not vision.error}
        (out/'result.json').write_text(json.dumps(report,indent=2));(out/'samples.jsonl').write_text(''.join(json.dumps(s)+'\n' for s in samples))
        if vision.annotated.get('uav01'):(out/'uav01-tags.jpg').write_bytes(vision.annotated['uav01'])
        print(json.dumps(report,indent=2),flush=True)
        return 0 if report['passed'] else 1
    finally:vision.close()

if __name__=='__main__':raise SystemExit(main())
