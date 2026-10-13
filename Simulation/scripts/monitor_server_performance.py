"""Measure only the standalone server process and its owned descendants."""
from pathlib import Path
import sys,json,time,statistics,urllib.request,psutil
ROOT=Path(__file__).resolve().parents[1];pid=int((ROOT/'.runtime/server.pid').read_text());process=psutil.Process(pid)
assert Path(process.cwd()).resolve()==ROOT and 'backend.app:app' in ' '.join(process.cmdline())
def state():return json.load(urllib.request.urlopen('http://127.0.0.1:8765/api/state',timeout=15))
first=state();run=first['run_id'];folder=ROOT/'artifacts'/('gateway-validation-'+run);folder.mkdir(parents=True,exist_ok=True);rows=[];seen={};start=time.monotonic()
try:
 while time.monotonic()-start<3000:
  s=state()
  if s['run_id']!=run or s['runtime']['state']=='offline':break
  rss=0;cpu=0
  for p in [process,*process.children(recursive=True)]:
   try:
    if p.pid not in seen:seen[p.pid]=p;p.cpu_percent()
    rss+=p.memory_info().rss;cpu+=seen[p.pid].cpu_percent()
   except psutil.Error:pass
  rows.append({'sim_time':s['sim_time'],'rss_mib':rss/1048576,'cpu_percent':cpu,'rtf':s['physics']['real_time_factor']})
  time.sleep(2)
finally:
 result={'run_id':run,'samples':len(rows),'sample_seconds':2,'peak_owned_rss_mib':max((r['rss_mib'] for r in rows),default=0),'median_cpu_percent':statistics.median(r['cpu_percent'] for r in rows) if rows else None,'median_rtf':statistics.median(r['rtf'] for r in rows) if rows else None,'first_sim_time':rows[0]['sim_time'] if rows else None,'last_sim_time':rows[-1]['sim_time'] if rows else None,'gpu_measurement':'Unavailable: nvidia-smi driver communication failed; no GPU utilization claim.'}
 (folder/'performance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
