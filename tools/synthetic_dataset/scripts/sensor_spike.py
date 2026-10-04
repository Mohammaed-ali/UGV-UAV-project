import os, subprocess, time, signal, json
from pathlib import Path
os.environ['GZ_PARTITION']='wildlife-v05-phase0'; os.environ['GZ_IP']='127.0.0.1'; os.environ['GZ_HOMEDIR']='/tmp/wildlife-v05-gz'
from gz.transport13 import Node
from gz.msgs10.image_pb2 import Image
from gz.msgs10.annotated_axis_aligned_2d_box_v_pb2 import AnnotatedAxisAligned2DBox_V
from gz.msgs10.annotated_oriented_3d_box_v_pb2 import AnnotatedOriented3DBox_V
from gz.msgs10.pose_v_pb2 import Pose_V
import numpy as np, cv2
base='<horizontal_fov>1.74</horizontal_fov><image><width>640</width><height>480</height></image><clip><near>0.1</near><far>100</far></clip>'
sensors=''
for name,typ,option in [('rgb','camera',''),('visible','boundingbox_camera','<box_type>visible_2d</box_type>'),('full','boundingbox_camera','<box_type>full_2d</box_type>'),('three','boundingbox_camera','<box_type>3d</box_type>'),('semantic','segmentation','<segmentation_type>semantic</segmentation_type>'),('instance','segmentation','<segmentation_type>instance</segmentation_type>')]:
 sensors+=f'<sensor name="{name}" type="{typ}"><topic>/{name}</topic><camera>{base}{option}</camera><always_on>true</always_on><update_rate>10</update_rate></sensor>'
models=''
for i,(dims,label) in enumerate([('0.5 0.5 1.8',10),('4.5 1.8 1.5',20),('6 2.4 2.8',30),('11 2.5 3.2',40)]):
 h=float(dims.split()[-1]); x=(i-1.5)*6
 models+=f'<model name="target_{label}"><static>true</static><pose>{x} 0 {h/2} 0 0 0</pose><link name="link"><visual name="shape"><geometry><box><size>{dims}</size></box></geometry><material><ambient>0.8 0.2 0.1 1</ambient><diffuse>0.8 0.2 0.1 1</diffuse></material></visual></link><plugin filename="gz-sim-label-system" name="gz::sim::systems::Label"><label>{label}</label></plugin></model>'
sdf=f'<sdf version="1.9"><world name="dataset_spike"><plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/><plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/><plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/><plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin><scene><ambient>0.5 0.5 0.5 1</ambient></scene><light name="sun" type="directional"><cast_shadows>true</cast_shadows><direction>-0.3 0.2 -1</direction><diffuse>0.8 0.8 0.8 1</diffuse></light><physics name="p" type="ignored"><max_step_size>0.01</max_step_size><real_time_factor>1</real_time_factor></physics><model name="ground"><static>true</static><link name="link"><visual name="ground"><geometry><plane><normal>0 0 1</normal><size>200 200</size></plane></geometry></visual></link></model>{models}<model name="rig"><static>true</static><pose>0 0 20 0 1.5707963267948966 0</pose><link name="link">{sensors}</link></model></world></sdf>'
Path('/tmp/v05_sensor_spike.sdf').write_text(sdf)
node=Node(); data={}; counts={}; callbacks=[]
for topic,cls in [('/rgb',Image),('/visible',AnnotatedAxisAligned2DBox_V),('/full',AnnotatedAxisAligned2DBox_V),('/three',AnnotatedOriented3DBox_V),('/semantic/labels_map',Image),('/instance/labels_map',Image),('/world/dataset_spike/pose/info',Pose_V)]:
 def cb(msg,t=topic): data[t]=msg; counts[t]=counts.get(t,0)+1
 callbacks.append(cb); node.subscribe(cls,topic,cb)
log=open('/tmp/v05_sensor_spike.log','w'); proc=subprocess.Popen(['gz','sim','-s','-r','--headless-rendering','-v','3','/tmp/v05_sensor_spike.sdf'],stdout=log,stderr=log,start_new_session=True)
try:
 deadline=time.monotonic()+25
 while time.monotonic()<deadline and proc.poll() is None:
  if all(t in data for t in ('/rgb','/visible','/full','/three','/semantic/labels_map','/instance/labels_map')): break
  time.sleep(.1)
 result={'counts':counts,'returncode':proc.poll(),'topics':node.topic_list()}
 for t,msg in data.items():
  if isinstance(msg, Image):
   a=np.frombuffer(msg.data,np.uint8).reshape(msg.height,msg.width,-1); result[t]={'width':msg.width,'height':msg.height,'format':msg.pixel_format_type,'unique':np.unique(a.reshape(-1,a.shape[-1]),axis=0).tolist()[:15] if t!='/rgb' else None}
   if t=='/rgb': cv2.imwrite('/tmp/v05_sensor_spike.png', cv2.cvtColor(a,cv2.COLOR_RGB2BGR))
   else: np.save('/tmp/v05'+t.replace('/','_')+'.npy',a)
  else: result[t]=str(msg)[:5000]
 Path('/tmp/v05_sensor_spike.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
finally:
 os.killpg(proc.pid,signal.SIGINT)
 try: proc.wait(5)
 except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL); proc.wait()
 log.close()
