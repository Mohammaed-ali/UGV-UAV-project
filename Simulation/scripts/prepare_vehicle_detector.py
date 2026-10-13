"""Fetch a pinned supplemental aerial model; YOLOX remains the primary."""
from pathlib import Path
import hashlib,urllib.request,json
root=Path(__file__).resolve().parents[1]/'assets/detector'
metadata=json.loads((root/'aerial-source.json').read_text());path=root/'aerial-vehicles.onnx'
if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=metadata['sha256']:
 url=metadata['source']+'/resolve/'+metadata['revision']+'/'+metadata['file']
 req=urllib.request.Request(url,headers={'User-Agent':'Fieldlab-detector-setup/1.0'})
 with urllib.request.urlopen(req,timeout=90) as response:data=response.read(110000000)
 if hashlib.sha256(data).hexdigest()!=metadata['sha256']:raise RuntimeError('Aerial vehicle model checksum mismatch.')
 path.write_bytes(data)
print('Verified supplemental aerial model. Vehicle subclasses remain provisional.')
