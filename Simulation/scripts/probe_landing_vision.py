"""Read-only live image/pose probe; never publishes aircraft or carrier commands."""
import argparse,json,time,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.transport import GazeboBridge
from backend.vision import Vision

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=float,default=15);parser.add_argument('--cameras',type=int,default=3)
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    gz=GazeboBridge();runtime=SimpleNamespace(gz=gz);vision=Vision(root,runtime)
    vision.landing.add('uav01')
    for i in range(1,args.cameras+1):gz.camera(f'uav{i:02d}')
    ages=[];latencies=[];stamps=set();matching=set();start=time.monotonic();samples=[]
    try:
        while time.monotonic()-start<args.seconds:
            obs=vision.tag_latest.get('uav01')
            if obs and time.monotonic()-start>3:
                age=gz.sim_time-obs['time'];ids=[t['id'] for t in obs['tags']]
                ages.append(age);latencies.append(obs['latency_ms']);stamps.add(obs['time'])
                if 1 in ids:matching.add(obs['time'])
                samples.append({'sim_time':gz.sim_time,'image_time':obs['time'],'age_seconds':round(age,4),'tag_ids':ids,'sync_error':obs['sync_error']})
            time.sleep(.025)
        report={'read_only':True,'camera_count':args.cameras,'duration_wall_seconds':args.seconds,'samples':len(samples),
                'unique_landing_frames':len(stamps),'assigned_tag_frames':len(matching),
                'tag_age_max_seconds':round(max(ages),4) if ages else None,'tag_age_p99_seconds':round(float(np.percentile(ages,99)),4) if ages else None,
                'tag_inference_p99_ms':round(float(np.percentile(latencies,99)),2) if latencies else None,
                'stale_samples':sum(age>=.5 for age in ages),'image_counts':gz.image_counts,'error':vision.error,
                'passed':len(stamps)>50 and len(matching)>50 and bool(ages) and max(ages)<.5 and not vision.error}
        out=root/'artifacts/landing-vision-probe';out.mkdir(parents=True,exist_ok=True)
        (out/'result.json').write_text(json.dumps(report,indent=2));(out/'samples.jsonl').write_text(''.join(json.dumps(s)+'\n' for s in samples))
        if 'uav01' in vision.annotated:(out/'uav01-live-tags.jpg').write_bytes(vision.annotated['uav01'])
        print(json.dumps(report,indent=2),flush=True)
        return 0 if report['passed'] else 1
    finally:vision.close();gz.close()

if __name__=='__main__':raise SystemExit(main())
