"""Separate sharing gateway: restarting a tunnel never interrupts a flight."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
import httpx
import websockets
from fastapi import FastAPI,Request,WebSocket,WebSocketDisconnect
from fastapi.responses import Response,JSONResponse,StreamingResponse
from starlette.background import BackgroundTask
from .access import Access,install_access

ROOT=Path(__file__).resolve().parents[1]
PORT=int(os.environ.get('FIELDLAB_PORT','8765'))
LOCAL=f'http://127.0.0.1:{PORT}'
access=Access(ROOT)

@asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient(base_url=LOCAL,timeout=60) as client:
        app.state.client=client
        yield

app=FastAPI(title='Fieldlab internet gateway',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
install_access(app,access)

@app.websocket('/api/live')
async def live(ws:WebSocket):
    if not (access.host_allowed(ws) and access.origin_allowed(ws,required=True) and access.authorized(ws)):
        await ws.close(code=1008);return
    await ws.accept()
    try:
        async with websockets.connect(f'ws://127.0.0.1:{PORT}/api/live',origin=LOCAL,max_size=4*1024*1024) as upstream:
            async for message in upstream:
                await ws.send_text(message)
    except (WebSocketDisconnect,RuntimeError,websockets.exceptions.ConnectionClosed):pass

@app.api_route('/{path:path}',methods=['GET','POST','PUT','DELETE','PATCH','HEAD'])
async def proxy(path:str,request:Request):
    # Only these headers are forwarded. Remote identities, cookies and Host must
    # never be mistaken for direct local operator access by the physics service.
    headers={name:request.headers[name] for name in ('content-type','accept','range') if name in request.headers}
    if request.method in ('POST','PUT','DELETE','PATCH'):headers['Origin']=LOCAL
    url=f'/{path}'+(f'?{request.url.query}' if request.url.query else '')
    try:
        req=request.app.state.client.build_request(request.method,url,content=await request.body(),headers=headers)
        response=await request.app.state.client.send(req,stream=True)
    except httpx.RequestError:
        return JSONResponse({'detail':'The host simulation server is offline. Start scripts/start.sh on the host PC.'},status_code=503)
    copied={name:response.headers[name] for name in ('content-type','cache-control','etag','content-range','accept-ranges') if name in response.headers}
    return StreamingResponse(response.aiter_bytes(),status_code=response.status_code,headers=copied,background=BackgroundTask(response.aclose))
