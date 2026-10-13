"""Run authorized physical acceptance gates sequentially; stop at the first failure.

This runner requires an idle standalone server. It preserves every gate's
separate evidence, restores the saved mission through the gateway validator,
and never starts the primary ROS workspace.
"""
from pathlib import Path
import sys,subprocess,time,json,urllib.request,argparse
ROOT=Path(__file__).resolve().parents[1]

def state():return json.load(urllib.request.urlopen('http://127.0.0.1:8765/api/state',timeout=10))

def run():
 if (ROOT/'.runtime/runtime-owner.json').exists() or state()['runtime']['state']!='offline':raise SystemExit('Finish/reset the existing physical runtime first.')
 stages=[
  ('city-extended','validate_city.py',['--seconds','600','--wheels','6']),
  ('obstacle','validate_city.py',['--fault','--wheels','6']),
  ('person','validate_tracking.py',['--after-survey','--duration','45']),
  ('car','validate_tracking.py',['--class','car','--duration','45']),
  ('camera-loss','validate_tracking.py',['--camera-drop','--duration','45']),
  ('lookalikes','validate_tracking.py',['--scenario','similar-people','--expect-ambiguity']),
  ('loaded-carousel','validate_loaded_carousel.py',[]),
  ('fleet-six','validate_gateway_mission.py',['--city','--target','--drones','8','--wheels','6','--timeout','2600']),
  ('fleet-four-split','validate_gateway_mission.py',['--city','--target','--drones','8','--wheels','4','--split','--timeout','2600']),
  ('stopping-car','validate_tracking.py',['--class','car','--scenario','stopping-vehicle','--duration','90']),
  ('building-occlusion','validate_tracking.py',['--scenario','building-occlusion','--duration','90','--confirm-candidates']),
  ('boundary-exit','validate_tracking.py',['--scenario','leaving-area','--duration','120','--expected-outcome','left-area'])]
 parser=argparse.ArgumentParser();parser.add_argument('--start-at',choices=[s[0] for s in stages],default='city-extended');args=parser.parse_args();stages=stages[[s[0] for s in stages].index(args.start_at):]
 journal={'started':time.time(),'stages':[],'passed':False};path=ROOT/'.runtime/release-validation.json'
 for name,script,args in stages:
  row={'name':name,'started':time.time(),'status':'running'};journal['stages'].append(row);path.write_text(json.dumps(journal,indent=2));print('START',name,flush=True)
  log=ROOT/'.runtime'/f'release-{name}.log'
  with log.open('w') as output:
   child=subprocess.Popen(['bash','-c','source "$1"; shift; exec "$@"','fieldlab-validation',str(ROOT/'scripts/environment.sh'),sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
   (ROOT/'.runtime/validation.pid').write_text(str(child.pid));monitor=None
   while child.poll() is None:
    if script=='validate_gateway_mission.py' and monitor is None:
     try:
      if state()['runtime']['state']!='offline':
       perf=(ROOT/'.runtime'/f'release-{name}-performance.log').open('w');monitor=subprocess.Popen([sys.executable,str(ROOT/'scripts/monitor_server_performance.py')],cwd=ROOT,stdout=perf,stderr=subprocess.STDOUT)
     except OSError:pass
    time.sleep(1)
   row.update(finished=time.time(),exit_code=child.returncode,status='passed' if child.returncode==0 else 'failed',console=str(log.relative_to(ROOT)));path.write_text(json.dumps(journal,indent=2));print('END',name,row['status'],flush=True)
   if monitor is not None:monitor.wait(timeout=30)
   if child.returncode:return child.returncode
 journal.update(passed=True,finished=time.time());path.write_text(json.dumps(journal,indent=2));return 0
if __name__=='__main__':raise SystemExit(run())
