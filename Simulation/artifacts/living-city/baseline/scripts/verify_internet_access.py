"""Verify the existing private internet link without issuing flight commands."""
import asyncio,json,time
from pathlib import Path
import httpx,websockets

ROOT=Path(__file__).resolve().parents[1]

async def live(url,cookie,run):
    async with websockets.connect(url.replace('https://','wss://')+'/api/live',origin=url,
                                  additional_headers={'Cookie':cookie},open_timeout=20) as ws:
        data=json.loads(await asyncio.wait_for(ws.recv(),10))
        return data['run_id']==run

def main():
    url=(ROOT/'.runtime/public-url.txt').read_text().strip()
    key=(ROOT/'.runtime/access-key').read_text().strip()
    report={'checked_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'public_url':url}
    try:
        with httpx.Client(base_url=url,timeout=20) as client:
            report['anonymous_state']=client.get('/api/state').status_code
            login=client.post('/api/session',json={'key':key},headers={'Origin':url})
            report['login']=login.status_code
            report['secure_cookie']=all(x in login.headers.get('set-cookie','') for x in ('Secure','HttpOnly'))
            response=client.get('/api/state');report['authenticated_state']=response.status_code
            response.raise_for_status();state=response.json();report['run_id']=state['run_id']
            report['cross_origin_command']=client.post('/api/command',json={'name':'camera','drone_id':None,
                'run_id':state['run_id'],'request_id':'access-validation'},headers={'Origin':'https://example.invalid'}).status_code
            cookie='; '.join(f'{k}={v}' for k,v in client.cookies.items())
            report['live_websocket']=asyncio.run(live(url,cookie,state['run_id']))
        report['passed']=report['anonymous_state']==401 and report['login']==200 and report['secure_cookie'] and report['authenticated_state']==200 and report['cross_origin_command']==403 and report['live_websocket']
    except Exception as error:
        report.update(passed=False,error=f'{type(error).__name__}: {error}')
    (ROOT/'artifacts/carousel-upgrade/internet-access-current.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
