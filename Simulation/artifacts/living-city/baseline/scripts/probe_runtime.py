"""Short physical integration probe; owns and cleans up only its own child processes."""
import time,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.config import Mission,Stop
from backend.runtime import Runtime

root=Path(__file__).resolve().parents[1]
r=Runtime(root);m=Mission(stops=[Stop(id='probe',label='Probe',x=-24,y=-22,drones=['uav01'])])
try:
 r.initialize(m);start=time.monotonic();last=''
 while r.state=='starting' and time.monotonic()-start<120:
  if r.progress!=last:print(r.progress,flush=True);last=r.progress
  time.sleep(.5)
 print(json.dumps(r.health()),flush=True)
 if r.gz:
  print('POSES',json.dumps({k:v for k,v in r.gz.poses.items() if k in ['carrier','uav01']}),flush=True)
  print('JOINTS',r.gz.joints,flush=True);print('LATCHES',r.gz.latches,flush=True)
 if r.fleet:
  deadline=time.monotonic()+50
  while time.monotonic()<deadline and not r.fleet.status('uav01')['ready']:time.sleep(.5)
  print('PX4',r.fleet.status('uav01'),flush=True)
 if r.state=='running':
  startpos=r.gz.poses['carrier']['position'].copy();r.gz.camera('uav01');r.gz.tray('uav01',1.65)
  for _ in range(60):r.gz.drive(.4,0);r.gz.tray('uav01',1.65);time.sleep(.1)
  r.gz.drive(0,0)
  print('AFTER_DRIVE',r.gz.poses['carrier']['position'],'START',startpos,flush=True)
  for _ in range(50):r.gz.tray('uav01',1.65);time.sleep(.1)
  print('TRAY',r.gz.joints.get('tray_uav01_joint'),'CAMERAS',r.gz.image_counts,flush=True)
  (root/'artifacts/physics-probe.json').write_text(json.dumps({'health':r.health(),'carrier_initial':startpos,'carrier_final':r.gz.poses['carrier']['position'],'tray_extension':r.gz.joints.get('tray_uav01_joint'),'cameras':r.gz.image_counts,'px4':r.fleet.status('uav01') if r.fleet else None},indent=2))
finally:r.stop()
