"""Fetch the official OpenCV Zoo model, pin source revision, verify the LFS checksum."""
from pathlib import Path
import urllib.request,json,hashlib,re
root=Path(__file__).resolve().parents[1]/'assets/detector';root.mkdir(parents=True,exist_ok=True)
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Fieldlab-simulation-setup/0.1'})
    with urllib.request.urlopen(req,timeout=90) as r:return r.read()
pin=root/'source.json'
revision=json.loads(pin.read_text())['revision'] if pin.is_file() else json.loads(fetch('https://api.github.com/repos/opencv/opencv_zoo/commits/main'))['sha']
sub='models/object_detection_yolox';name='object_detection_yolox_2022nov.onnx'
pointer=fetch(f'https://raw.githubusercontent.com/opencv/opencv_zoo/{revision}/{sub}/{name}').decode()
match=re.search(r'oid sha256:([0-9a-f]{64})',pointer)
if not match:raise RuntimeError('The official model pointer did not provide a SHA256 digest.')
expected=match.group(1);path=root/'yolox.onnx'
if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
    data=fetch(f'https://media.githubusercontent.com/media/opencv/opencv_zoo/{revision}/{sub}/{name}')
    if hashlib.sha256(data).hexdigest()!=expected:raise RuntimeError('Model checksum mismatch.')
    path.write_bytes(data)
(root/'LICENSE').write_bytes(fetch(f'https://raw.githubusercontent.com/opencv/opencv_zoo/{revision}/{sub}/LICENSE'))
pin.write_text(json.dumps({'source':'https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_yolox','revision':revision,'file':name,'sha256':expected,'license':'Apache-2.0','classes':['person','car','bus','truck']},indent=2))
print('Verified official YOLOX model:',expected)
