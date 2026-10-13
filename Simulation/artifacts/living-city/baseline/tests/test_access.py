from starlette.requests import Request
from backend.access import Access,COOKIE,SESSION_SECONDS


def request(host='127.0.0.1:8765',origin=None,cookie=None,forwarded=False):
    headers=[(b'host',host.encode())]
    if origin:headers.append((b'origin',origin.encode()))
    if cookie:headers.append((b'cookie',f'{COOKIE}={cookie}'.encode()))
    if forwarded:headers.append((b'cf-connecting-ip',b'198.51.100.20'))
    return Request({'type':'http','scheme':'http','method':'GET','path':'/api/state',
                    'query_string':b'','headers':headers,'client':('127.0.0.1',20000),'server':('127.0.0.1',8765)})


def test_remote_requests_require_authentication_and_exact_host(tmp_path):
    access=Access(tmp_path)
    (tmp_path/'.runtime/public-url.txt').write_text('https://example.trycloudflare.com')
    assert access.authorized(request())
    remote=request('example.trycloudflare.com',forwarded=True)
    assert access.host_allowed(remote) and not access.authorized(remote)
    assert not access.host_allowed(request('attacker.example'))
    # The tunnel's loopback connection and a forged local Host must not bypass login.
    forged=request(forwarded=True)
    assert not access.local(forged) and not access.host_allowed(forged)
    authenticated=request('example.trycloudflare.com',cookie=access.session(),forwarded=True)
    assert access.authorized(authenticated)


def test_signed_session_expiry_tampering_and_key_rotation(tmp_path):
    access=Access(tmp_path);session=access.session(now=10000)
    assert access.session_valid(session,now=10001)
    assert not access.session_valid(session,now=9999)
    assert not access.session_valid(session,now=10000+SESSION_SECONDS+1)
    assert not access.session_valid(session+'x',now=10001)
    assert not access.session_valid('invalid',now=10001)
    other=Access(tmp_path/'other')
    assert not other.session_valid(session,now=10001)
    assert access.key_valid(access.key) and not access.key_valid('wrong')


def test_remote_mutations_and_websockets_require_same_origin(tmp_path):
    access=Access(tmp_path)
    (tmp_path/'.runtime/public-url.txt').write_text('https://example.trycloudflare.com')
    assert access.origin_allowed(request('example.trycloudflare.com',origin='https://example.trycloudflare.com'),required=True)
    assert not access.origin_allowed(request('example.trycloudflare.com',origin='https://other.trycloudflare.com'),required=True)
    assert not access.origin_allowed(request('example.trycloudflare.com'),required=True)
    assert access.origin_allowed(request(origin='http://127.0.0.1:8765'),required=True)


def test_http_gateway_blocks_state_and_commands_until_login(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from backend.access import install_access
    access=Access(tmp_path)
    public='https://example.trycloudflare.com'
    (tmp_path/'.runtime/public-url.txt').write_text(public)
    app=FastAPI();install_access(app,access)
    @app.get('/api/state')
    def state():return {'state':'READY'}
    @app.post('/api/command')
    def command():return {'accepted':True}
    with TestClient(app,base_url=public) as client:
        assert client.get('/api/state').status_code==401
        assert client.post('/api/command',headers={'Origin':public}).status_code==401
        assert client.post('/api/session',json={'key':access.key},headers={'Origin':'https://attacker.example'}).status_code==403
        assert client.post('/api/session',json={'key':'incorrect'},headers={'Origin':public}).status_code==401
        login=client.post('/api/session',json={'key':access.key},headers={'Origin':public})
        assert login.status_code==200
        assert 'Secure' in login.headers['set-cookie'] and 'HttpOnly' in login.headers['set-cookie']
        assert client.get('/api/state').json()=={'state':'READY'}
        assert client.post('/api/command',headers={'Origin':'https://attacker.example'}).status_code==403
        assert client.post('/api/command',headers={'Origin':public}).status_code==200
