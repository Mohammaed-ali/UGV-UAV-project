"""Run one authenticated internet tunnel without opening incoming router ports."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'.runtime'
VERSION='2026.10.0'
DOWNLOAD=f'https://github.com/cloudflare/cloudflared/releases/download/{VERSION}/cloudflared-linux-amd64'
SHA256='d33ff2d14475178d2012c2c56beba87389ac5ded27649519f198a7d3134a99db'

def main():
    RUNTIME.mkdir(parents=True,exist_ok=True)
    lock=open(RUNTIME/'share.lock','w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit('An internet link is already running. See .runtime/share-link.txt.')
    port=int(os.environ.get('FIELDLAB_PORT','8765'))
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/state',timeout=5) as response:
            status=json.load(response)
    except Exception as exc:raise SystemExit(f'Start ./scripts/start.sh first. {exc}')
    binary=RUNTIME/'bin/cloudflared';binary.parent.mkdir(parents=True,exist_ok=True)
    if not binary.exists():
        print(f'Downloading official Cloudflare tunnel client {VERSION}…',flush=True)
        temp=binary.with_suffix('.download')
        with urllib.request.urlopen(DOWNLOAD,timeout=60) as source,open(temp,'wb') as target:
            import shutil;shutil.copyfileobj(source,target)
        if hashlib.sha256(temp.read_bytes()).hexdigest()!=SHA256:
            temp.unlink();raise SystemExit('The tunnel client checksum did not match its official release.')
        temp.chmod(0o755);temp.replace(binary)
    elif hashlib.sha256(binary.read_bytes()).hexdigest()!=SHA256:
        raise SystemExit('The installed tunnel client checksum does not match. Reinstall the pinned binary.')
    gateway_port=int(os.environ.get('FIELDLAB_GATEWAY_PORT',str(port+1)))
    gateway_log=open(RUNTIME/'gateway.log','w')
    gateway=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-m','uvicorn','backend.gateway:app','--host','127.0.0.1','--port',str(gateway_port),'--no-access-log','--no-proxy-headers'],cwd=ROOT,stdout=gateway_log,stderr=subprocess.STDOUT)
    deadline=time.monotonic()+15
    while True:
        if gateway.poll() is not None:raise SystemExit('Sharing gateway exited. See .runtime/gateway.log.')
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{gateway_port}/api/session',timeout=1) as response:
                if json.load(response).get('gateway_version')==1:break
        except OSError:pass
        if time.monotonic()>deadline:gateway.terminate();raise SystemExit('Sharing gateway timed out. See .runtime/gateway.log.')
        time.sleep(.15)
    child=subprocess.Popen([str(binary),'tunnel','--no-autoupdate','--url',f'http://127.0.0.1:{gateway_port}','--protocol','http2'],
                           cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    def stop(*_):
        if child.poll() is None:child.terminate()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    url=''
    try:
        with open(RUNTIME/'cloudflared.log','w') as log:
            for line in child.stdout:
                log.write(line);log.flush()
                match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',line)
                if match and not url:
                    url=match.group()
                    (RUNTIME/'public-url.txt').write_text(url)
                    key=(RUNTIME/'access-key').read_text().strip()
                    link=f'{url}/#key={key}'
                    private=RUNTIME/'share-link.txt';private.write_text(link+'\n');private.chmod(0o600)
                    print(f'Internet simulation: {link}',flush=True)
                    print('This private link grants mission controls. Keep this terminal and the simulation server running.',flush=True)
                if 'Registered tunnel connection' in line:print('Internet tunnel connected.',flush=True)
                if 'ERR' in line:print(line.strip(),file=sys.stderr,flush=True)
        code=child.wait()
        if code and not url:raise SystemExit(f'Tunnel failed. See {RUNTIME}/cloudflared.log')
    finally:
        stop()
        try:child.wait(timeout=10)
        except subprocess.TimeoutExpired:child.kill();child.wait()
        public=RUNTIME/'public-url.txt'
        if public.exists() and public.read_text().strip()==url:public.unlink()
        gateway.terminate()
        try:gateway.wait(timeout=10)
        except subprocess.TimeoutExpired:gateway.kill();gateway.wait()
        gateway_log.close()

if __name__=='__main__':main()
