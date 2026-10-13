#!/usr/bin/env python3
"""SIGKILL an actual generation run and resume its original dataset identity."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from common import TOOL, write_json, file_hash
from validate_dataset import validate


def cleanup_owned(output):
    for p in (output/'runtime').glob('*/owned_processes.json'):
        d=json.loads(p.read_text())
        try: os.killpg(d['gazebo_pgid'],signal.SIGINT)
        except ProcessLookupError: pass
        # These PIDs are recorded by this run; never pkill unrelated simulations.


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--report',required=True)
    p.add_argument('--config',default=str(TOOL/'configs/synthetic_dataset.yaml'));p.add_argument('--count',type=int,default=200);p.add_argument('--seed',type=int,default=76543)
    args=p.parse_args();out=Path(args.output).resolve()
    if out.exists() and any(out.iterdir()): raise RuntimeError('Crash test needs a new empty output')
    out.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,str(TOOL/'scripts/generate_dataset.py'),'--config',args.config,'--count',str(args.count),'--seed',str(args.seed),'--output',str(out),'--headless']
    with (out/'crash_attempt.log').open('w') as log:
        # Put diagnostic log outside the output before generator occupation check.
        diagnostic=out.parent/(out.name+'_crash_attempt.log');log.close();(out/'crash_attempt.log').unlink()
        with diagnostic.open('w') as stream: proc=subprocess.Popen(command,stdout=stream,stderr=stream,start_new_session=True)
    deadline=time.monotonic()+120;before={}
    try:
        while time.monotonic()<deadline:
            states=list((out/'.state').glob('*.json'))
            if len(states)>=30:
                before={p.name:file_hash(p) for p in states}
                os.killpg(proc.pid,signal.SIGKILL);proc.wait();break
            if proc.poll() is not None: raise RuntimeError('Generation ended before forced interruption; inspect '+str(diagnostic))
            time.sleep(.05)
        else: raise TimeoutError('No committed crash-test samples')
    finally: cleanup_owned(out)
    # Reap orphan Gazebo shutdown before resuming. Its isolated partition prevents overlap.
    time.sleep(1)
    with (out.parent/(out.name+'_resume.log')).open('w') as stream:
        result=subprocess.run(command+['--resume'],stdout=stream,stderr=stream)
    validation=validate(out)
    preserved=all(file_hash(out/'.state'/name)==h for name,h in before.items())
    report={'status':'PASSED' if result.returncode==0 and validation['status']=='PASSED' and preserved else 'FAIL',
            'signal':'SIGKILL','committed_before_kill':len(before),'completed_samples_unchanged':preserved,
            'expected_count':args.count,'resume_exit_code':result.returncode,'validator':validation,
            'remaining_temporary_files':[str(p.relative_to(out)) for p in out.rglob('*.tmp')]}
    if report['remaining_temporary_files']: report['status']='FAIL'
    write_json(args.report,report);print(json.dumps(report,indent=2));return 0 if report['status']=='PASSED' else 1


if __name__=='__main__': raise SystemExit(main())
