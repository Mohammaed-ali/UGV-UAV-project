import sys,numpy as np,cv2
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tools/synthetic_dataset/scripts'))
from common import load_config,write_json
from sampling import Sampler
from gazebo_backend import Gazebo
c=load_config('tools/synthetic_dataset/configs/synthetic_dataset.yaml');s=Sampler(c,200,12345);results=[]
with Gazebo(c,'/tmp/v05_light_probe2') as g:
 print('SUN ID',g.entity_ids.get('sun'),flush=True)
 scene=s.scene(4)
 for family in ('morning','noon','evening','shadow'):
  scene['lighting']['family']=family;scene['lighting']['color']=c['lighting'][family]['color'];scene['lighting']['intensity']=sum(c['lighting'][family]['intensity'])/2
  image,label,meta=g.capture(scene)
  cv2.imwrite('/tmp/v05_light_probe2/'+family+'.png',image)
  result={'family':family,'mean_bgr':image.mean(axis=(0,1)).tolist(),'requested_light':scene['lighting'],'entity_id':g.entity_ids.get('sun')};results.append(result)
  print(result,flush=True)
 write_json('/tmp/v05_light_probe2/results.json',results)
