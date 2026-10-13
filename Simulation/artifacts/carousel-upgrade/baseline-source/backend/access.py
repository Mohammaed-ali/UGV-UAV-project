"""Capability-key login for the explicitly shared simulation gateway."""
import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import Request,HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel,ConfigDict,Field

COOKIE = 'fieldlab_session'
SESSION_SECONDS = 12 * 60 * 60


class Access:
    def __init__(self, root: Path):
        self.root = root
        directory = root / '.runtime'
        directory.mkdir(parents=True, exist_ok=True)
        key_path = directory / 'access-key'
        try:
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, 'w') as stream:
                stream.write(secrets.token_urlsafe(32))
        key_path.chmod(0o600)
        self.key = key_path.read_text().strip()
        if len(self.key) < 32:
            raise RuntimeError('The remote access key must contain at least 32 characters.')

    def public_url(self):
        path = self.root / '.runtime/public-url.txt'
        return path.read_text().strip().rstrip('/') if path.exists() else ''

    def local(self, connection):
        host = urlsplit('http://' + connection.headers.get('host', '')).hostname
        peer = connection.client.host if connection.client else ''
        forwarded = ('cf-ray', 'cf-connecting-ip', 'x-forwarded-for', 'x-forwarded-host', 'forwarded')
        return (host in ('127.0.0.1', 'localhost', '::1')
                and peer in ('127.0.0.1', '::1', 'testclient')
                and not any(name in connection.headers for name in forwarded))

    def host_allowed(self, connection):
        if self.local(connection):
            return True
        public = urlsplit(self.public_url())
        return bool(public.netloc and connection.headers.get('host', '').lower() == public.netloc.lower())

    def origin_allowed(self, connection, required=False):
        origin = connection.headers.get('origin')
        if not origin:
            return not required
        expected = (f'http://{connection.headers.get("host")}'
                    if self.local(connection) else self.public_url())
        return origin.rstrip('/').lower() == expected.lower()

    def session(self, now=None):
        stamp = int(time.time() if now is None else now)
        message = f'{stamp}.{secrets.token_hex(16)}'
        signature = hmac.new(self.key.encode(), message.encode(), hashlib.sha256).hexdigest()
        return f'{message}.{signature}'

    def session_valid(self, value, now=None):
        if not value:
            return False
        try:
            stamp, nonce, signature = value.split('.')
            age = int(time.time() if now is None else now) - int(stamp)
        except (ValueError, TypeError):
            return False
        expected = hmac.new(self.key.encode(), f'{stamp}.{nonce}'.encode(), hashlib.sha256).hexdigest()
        return 0 <= age <= SESSION_SECONDS and hmac.compare_digest(signature, expected)

    def authorized(self, connection):
        return self.local(connection) or self.session_valid(connection.cookies.get(COOKIE))

    def key_valid(self, value):
        return hmac.compare_digest(value, self.key)


class Login(BaseModel):
    model_config=ConfigDict(extra='forbid')
    key:str=Field(min_length=1,max_length=128)


def install_access(app,access):
    @app.middleware('http')
    async def operator_access(request,call_next):
        if not access.host_allowed(request):return JSONResponse({'detail':'This address is not an active simulation link.'},status_code=403)
        if request.method in ('POST','PUT','DELETE','PATCH'):
            if not access.origin_allowed(request,required=not access.local(request)):
                return JSONResponse({'detail':'Use this simulation page to submit commands.'},status_code=403)
        protected=request.url.path.startswith(('/api/','/assets-sim')) and request.url.path!='/api/session'
        if protected and not access.authorized(request):return JSONResponse({'detail':'Enter the simulation access key to connect.'},status_code=401)
        response=await call_next(request)
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['X-Content-Type-Options']='nosniff'
        if request.url.path.startswith('/api/'):response.headers['Cache-Control']='no-store'
        return response

    @app.get('/api/session')
    def session_status(request:Request):return {'authorized':access.authorized(request),'local':access.local(request),'gateway_version':1}

    @app.post('/api/session')
    def login(body:Login,request:Request):
        if not access.key_valid(body.key):raise HTTPException(401,'That access key is incorrect.')
        response=JSONResponse({'authorized':True})
        response.set_cookie(COOKIE,access.session(),max_age=SESSION_SECONDS,httponly=True,secure=not access.local(request),samesite='strict')
        return response

    @app.delete('/api/session')
    def logout():
        response=JSONResponse({'authorized':False});response.delete_cookie(COOKIE);return response
