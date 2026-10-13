"""Simulation-only runner; requires scripts/environment.sh and QGC already connected."""
import os, signal, subprocess, sys, time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
mode=sys.argv[1]
env=dict(os.environ,ROS_DOMAIN_ID='83',ROS_LOG_DIR='/tmp/wildlife-v03-acceptance-logs',WILDLIFE_RUN_DIR='/tmp/wildlife-v03-'+mode)
output=root/'docs/validation'/('px4_'+mode.replace('-','_')+'.json')
probe=subprocess.Popen(['python3',str(root/'tests/px4_acceptance_probe.py'),'--mode',mode,'--output',str(output)],env=env)
runtime=None
try:
    time.sleep(3)
    args=['bash',str(root/'scripts/start_px4_single.sh'),'show_rviz:=true']
    if mode=='no-target':args += ['detection_probability:=0.0','search_timeout:=10.0','loiter_duration:=3.0']
    runtime=subprocess.Popen(args,env=env)
    deadline=time.monotonic()+235
    while probe.poll() is None:
        if runtime.poll() is not None:
            raise RuntimeError('Simulation exited before acceptance; inspect '+env['WILDLIFE_RUN_DIR'])
        if time.monotonic()>deadline:raise TimeoutError('Acceptance deadline')
        time.sleep(.25)
    rc=probe.returncode
finally:
    if probe.poll() is None:probe.terminate();probe.wait(timeout=5)
    if runtime and runtime.poll() is None:
        runtime.send_signal(signal.SIGINT)
        runtime.wait(timeout=20)
raise SystemExit(rc)
