#!/usr/bin/env python3
"""Primary CLI. One headless Gazebo process, no PX4/ROS mission graph or detector."""
import argparse
from collections import Counter
import fcntl
import json
import os
from pathlib import Path
import platform
import resource
import signal
import subprocess
import time
import yaml
from common import (TOOL, ROOT, load_config, canonical, digest, file_hash,
                    git_revision, atomic_write, write_json, utc_now, acceptance_config_hash)
from sampling import Sampler
from storage import complete, commit_sample, summarize


def code_hash():
    return digest(canonical({str(p.relative_to(TOOL)):file_hash(p) for p in sorted((TOOL/'scripts').glob('*.py'))}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default=str(TOOL/'configs/synthetic_dataset.yaml'))
    parser.add_argument('--count',type=int);parser.add_argument('--seed',type=int);parser.add_argument('--output')
    parser.add_argument('--headless',action='store_true');parser.add_argument('--resume',action='store_true')
    parser.add_argument('--validate-only',action='store_true')
    args=parser.parse_args();cfg=load_config(args.config)
    count=cfg['count'] if args.count is None else args.count;seed=cfg['master_seed'] if args.seed is None else args.seed
    if count<=0: parser.error('count must be positive')
    root=Path(args.output or cfg['output']).resolve()
    if args.validate_only:
        from validate_dataset import validate
        result=validate(root);print(json.dumps(result,indent=2));return 0 if result['status']=='PASSED' else 1
    cfg['count']=count;cfg['master_seed']=seed
    # User must finish actual Phase-0/alignment proof before generating a dataset.
    gate_path=ROOT/'docs/dataset/evidence/feasibility.json'
    if not gate_path.exists(): raise RuntimeError('Phase-0/alignment gates have not been recorded')
    gates=json.loads(gate_path.read_text())
    if gates.get('status')!='PASSED' or gates.get('camera_sha256')!=cfg['camera']['source_sha256'] or gates.get('asset_manifest_sha256')!=file_hash(TOOL/'assets/manifests/assets.json'):
        raise RuntimeError('Phase-0/alignment evidence is missing, failed or stale')
    # Pilot/full stages require previous real generation and validated QA evidence.
    for required,threshold in [('smoke',200),('pilot',2000),('audit',2000)]:
        if count<=threshold: continue
        p=ROOT/f'docs/dataset/evidence/{required}_gate.json'
        prior=json.loads(p.read_text()) if p.exists() else {}
        if prior.get('status')!='PASSED' or prior.get('acceptance_configuration_sha256')!=acceptance_config_hash(cfg):
            raise RuntimeError(f'{required} acceptance gate must pass before count={count}')
    occupied=root.exists() and any(p.name!='.lock' for p in root.iterdir())
    if occupied and not args.resume: raise RuntimeError('Output already contains files; use --resume with its original config/count/seed')
    root.mkdir(parents=True,exist_ok=True)
    with (root/'.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        identity={'expected_count':count,'seed':seed,'configuration_sha256':digest(canonical(cfg)),
                  'generator_code_sha256':code_hash(),'generator_git_commit':git_revision(),
                  'asset_manifest_sha256':file_hash(TOOL/'assets/manifests/assets.json')}
        run_path=root/'.run.json'
        if args.resume:
            run=json.loads(run_path.read_text())
            if any(run.get(k)!=v for k,v in identity.items()): raise RuntimeError('Resume identity mismatch: config/count/seed/code/revision/assets changed')
        else:
            run=dict(identity,dataset_name=cfg['dataset_name'],dataset_version=cfg['dataset_version'],
                     source_project_release='v0.4-final',source_release_commit=git_revision('v0.4-final^{commit}'),
                     camera_configuration_sha256=cfg['camera']['source_sha256'],master_seed=seed,
                     gazebo_version=subprocess.check_output(['gz','sim','--versions'],text=True).strip(),
                     class_mapping=cfg['classes'],generation_start=utc_now(),attempted_samples=0,rejected_samples=0,
                     rejection_reasons={},asset_licenses=sorted(set(a['license'] for a in cfg['assets'])),
                     known_limitations=['synthetic mesh/PBR imagery; no real-world accuracy claim','person variants share one template; no heldout person model',
                                        'geometry cross-check is a full silhouette, native labels are visible boxes','pixel visibility fraction is not measured'],
                     host={'platform':platform.platform(),'cpu_count':os.cpu_count(),'python':platform.python_version()})
            write_json(run_path,run)
            atomic_write(root/'manifests/generation_config.yaml',yaml.safe_dump(cfg,sort_keys=False))
            atomic_write(root/'manifests/class_mapping.yaml',yaml.safe_dump({'classes':cfg['classes']},sort_keys=False))
            atomic_write(root/'manifests/visdrone_class_map.yaml',(TOOL/'configs/visdrone_class_map.yaml').read_bytes())
            for name in ('assets.json','assets.csv'): atomic_write(root/'manifests'/name,(TOOL/'assets/manifests'/name).read_bytes())
        for p in root.rglob('*.tmp'): p.unlink()
        sampler=Sampler(cfg,count,seed);skipped=0;generated=0;started=time.monotonic()
        counters=Counter(run['rejection_reasons']);cpu_start=resource.getrusage(resource.RUSAGE_SELF)
        def stop(signum,frame): raise KeyboardInterrupt
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        from gazebo_backend import Gazebo
        try:
            with Gazebo(cfg,root/'runtime'/('run_'+str(time.time_ns())),headless=args.headless) as gazebo:
                for index in range(count):
                    scene=sampler.scene(index)
                    if args.resume and complete(root,scene): skipped+=1;continue
                    for attempt in range(cfg['capture']['max_retries']):
                        run['attempted_samples']+=1;write_json(run_path,run)
                        try: image,label,metadata=gazebo.capture(scene);break
                        except (TimeoutError,RuntimeError) as error:
                            reason=str(error);counters[reason]+=1;run['rejected_samples']+=1;run['rejection_reasons']=dict(counters);write_json(run_path,run)
                            print(f'Rejected {scene["frame_id"]}: {reason}',flush=True)
                            if attempt+1==cfg['capture']['max_retries']: raise
                    commit_sample(root,scene,image,label,metadata);generated+=1
                    if generated%25==0: print(f'Accepted {skipped+generated}/{count}, new {generated}, {generated/max(.001,time.monotonic()-started)*60:.1f} frames/min',flush=True)
            run['rejection_reasons']=dict(counters)
            elapsed=time.monotonic()-started
            run['last_run_performance']={'elapsed_s':elapsed,'generated_samples':generated,'skipped_samples':skipped,
                                         'accepted_per_minute':generated/max(elapsed,.001)*60,
                                         'python_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                         'python_cpu_seconds':resource.getrusage(resource.RUSAGE_SELF).ru_utime-cpu_start.ru_utime}
            write_json(run_path,run);manifest=summarize(root,cfg,run)
            from validate_dataset import validate
            result=validate(root);write_json(root/'qa/validation.json',result)
            print(json.dumps({'accepted':manifest['accepted_samples'],'output':str(root),'validation':result['status'],'errors':result['errors']},indent=2))
            return 0 if result['status']=='PASSED' else 1
        except BaseException:
            run['rejection_reasons']=dict(counters);write_json(run_path,run)
            summarize(root,cfg,run)
            raise


if __name__=='__main__': raise SystemExit(main())
