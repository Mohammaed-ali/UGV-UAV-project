"""Review/remove obsolete generated files after validation, never source/dependencies.

Default is a dry run. --apply requires idle physics and validation processes.
Compact trace summaries and existing result/diagnosis reports are retained.
"""
from pathlib import Path
import argparse,json,time,math,hashlib,shutil,os
ROOT=Path(__file__).resolve().parents[1]

def summarize_trace(path):
 rows=0;first=None;last=None;events={};drone_states={};motion={};previous={};contacts={'ugv_actor':0,'actor_actor':0};max_ages={};broken=0
 with path.open() as trace:
  for line in trace:
   try:s=json.loads(line)
   except (ValueError,UnicodeDecodeError):broken+=1;continue
   if not isinstance(s,dict):continue
   rows+=1;first=s if first is None else first;last=s
   for e in s.get('events',[]):
    if isinstance(e,dict):events[(e.get('id'),e.get('time'))]=e
   for d in s.get('drones',[]):
    if not isinstance(d,dict) or 'id' not in d:continue
    name=d['id'];phase=d.get('state');timeline=drone_states.setdefault(name,[])
    if not timeline or timeline[-1]['state']!=phase:timeline.append({'time':s.get('sim_time'),'state':phase,'armed':d.get('armed'),'latched':d.get('latched')})
    p=d.get('position')
    if p is not None:
     if name in previous:motion[name]=motion.get(name,0)+math.dist(p,previous[name])
     previous[name]=p
    if d.get('telemetry_age') is not None:max_ages[name]=max(max_ages.get(name,0),d['telemetry_age'])
   city=s.get('city') or {};contacts['ugv_actor']=max(contacts['ugv_actor'],len(city.get('contact_events',[])));contacts['actor_actor']=max(contacts['actor_actor'],len(city.get('actor_contacts',[])))
 summary={'source':str(path.relative_to(ROOT)),'source_bytes':path.stat().st_size,'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),'samples':rows,'invalid_lines':broken,'first_sim_time':(first or {}).get('sim_time'),'last_sim_time':(last or {}).get('sim_time'),'last_state':last,'events':list(events.values()),'aircraft_state_timeline':drone_states,'measured_aircraft_travel_m':motion,'maximum_telemetry_ages':max_ages,'maximum_contacts':contacts,'raw_trace_removed':True,'reason':'Operator requested junk cleanup after build; compact acceptance and failure evidence retained.'}
 target=path.with_suffix('.trace-summary.json');target.write_text(json.dumps(summary,indent=2));return target

def candidates():
 result=[];manifest=json.loads((ROOT/'assets/city-manifest.json').read_text());used={part['file'] for parts in manifest.values() for part in parts}
 for p in ROOT.rglob('*'):
  if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(ROOT):continue
  rel=p.relative_to(ROOT);parts=rel.parts;reason=None
  if rel==Path('.runtime/continue-release-validation.py'):reason='Superseded temporary validation launcher'
  elif rel==Path('tsconfig.tsbuildinfo'):reason='Regenerable TypeScript build cache'
  elif parts[0]=='artifacts' and p.suffix in ('.ulg','.bson','.jsonl'):reason='Obsolete raw native/mission/validation log'
  elif any(x in parts for x in ('__pycache__','.pytest_cache','.vite','.vite-temp')) or parts[:2]==('.runtime','pycache'):reason='Regenerable cache'
  elif parts[:2]==('.runtime','city-build') and len(parts)>2 and p.suffix!='.so':reason='Native build intermediate; required plugin retained'
  elif parts[:2]==('assets','city') and len(parts)>2 and parts[2] in ('car_mesh_0','car_mesh_1') and '/assets-sim/'+str(rel.relative_to('assets')) not in used:reason='Superseded generated car visual'
  if reason:result.append((p,reason))
 return result

def check_idle():
 import httpx,psutil
 try:
  r=httpx.get('http://127.0.0.1:8765/api/state',timeout=5);r.raise_for_status()
  if r.json()['runtime']['state']!='offline':raise RuntimeError('Reset the physical runtime before cleanup.')
 except httpx.ConnectError:pass
 owner=ROOT/'.runtime/runtime-owner.json'
 if owner.exists():raise RuntimeError('A physical runtime ownership file is present; complete/reset it first.')
 pidfile=ROOT/'.runtime/validation.pid'
 if pidfile.exists():
  try:
   p=psutil.Process(int(pidfile.read_text()))
   if p.status()!=psutil.STATUS_ZOMBIE and 'validate_' in ' '.join(p.cmdline()):raise RuntimeError('A validation recorder is active; wait for completion.')
  except psutil.NoSuchProcess:pass

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args();assert ROOT.name=='Simulation' and (ROOT/'AGENTS.md').is_file()
 if args.apply:check_idle()
 items=candidates();before=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file() and not p.is_symlink());removed=[];summaries=[];by_reason={}
 for p,reason in items:
  size=p.stat().st_size;by_reason[reason]=by_reason.get(reason,0)+size
  if args.apply:
   if p.suffix=='.jsonl':summaries.append(str(summarize_trace(p).relative_to(ROOT)))
   removed.append({'path':str(p.relative_to(ROOT)),'bytes':size,'reason':reason});p.unlink()
 # Remove only now-empty generated directories, without following links.
 if args.apply:
  for base in (ROOT/'artifacts',ROOT/'.pytest_cache',ROOT/'.runtime/pycache',ROOT/'assets/city',ROOT/'node_modules/.vite',ROOT/'node_modules/.vite-temp'):
   if not base.exists():continue
   for folder in sorted((p for p in base.rglob('*') if p.is_dir() and not p.is_symlink()),key=lambda p:len(p.parts),reverse=True):
    try:folder.rmdir()
    except OSError:pass
  after=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file() and not p.is_symlink());report={'checked_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'project':str(ROOT),'bytes_before':before,'bytes_after':after,'net_bytes_freed':before-after,'removed':removed,'compact_trace_summaries':summaries,'categories':by_reason,'folder_review':{'backend, web, native, scripts, tests':'Application source and reproducible verification retained','assets, public':'Required models, textures, detector weights and licenses retained; only superseded unused visuals removed','missions':'Saved operator mission and reproducible scenarios retained','dist':'Compiled browser application retained','node_modules, .venv':'Runtime and build dependencies retained; only regenerable caches removed','.runtime':'Required native plugin, access keys, tunnel client and ownership/service records retained; caches and temporary launcher removed','artifacts':'Compact passes, failures, diagnoses, camera evidence and trace summaries retained; raw obsolete logs removed','docs and top-level files':'Architecture, validation, startup documentation and dependency/build configuration retained'},'retained':'Source, tests, documentation, scenarios, compiled application, installed city plugin, all required model/texture/detector assets and licenses, Python/frontend dependencies, access keys and internet service metadata, compact acceptance/failure reports and camera evidence.'}
  (ROOT/'artifacts/junk-cleanup.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:report[k] for k in ('bytes_before','bytes_after','net_bytes_freed','categories')},indent=2))
 else:print(json.dumps({'dry_run':True,'files':len(items),'candidate_bytes':sum(p.stat().st_size for p,_ in items),'categories':by_reason},indent=2))
if __name__=='__main__':main()
