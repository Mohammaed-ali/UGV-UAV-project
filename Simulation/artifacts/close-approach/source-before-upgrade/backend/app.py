from pathlib import Path
import asyncio,json,uuid,time,os
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI,WebSocket,WebSocketDisconnect,HTTPException,Request
from fastapi.responses import Response,FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field,ConfigDict
from .config import Mission,scene
from .runtime import Runtime
from .vision import Vision
from .mission import Engine
from .access import Access,install_access

ROOT=Path(__file__).resolve().parents[1]
access=Access(ROOT)
runtime=Runtime(ROOT);vision=Vision(ROOT,runtime);engine=Engine(ROOT,runtime,vision)
saved=ROOT/'missions/current.json'
if saved.is_file():
    try:engine.configure(Mission.model_validate_json(saved.read_text()))
    except ValueError as e:engine.event(f'Saved mission could not be loaded: {e}','warning')

async def tick():
    while True:
        try:engine.tick()
        except Exception as e:
            engine.state='FAULT';engine.event(f'Controller error: {e}','error')
            import traceback;traceback.print_exc()
        await asyncio.sleep(.05)

@asynccontextmanager
async def lifespan(app):
    (ROOT/'.runtime/server.pid').write_text(str(os.getpid()))
    loop=asyncio.create_task(tick())
    yield
    loop.cancel();vision.close();await asyncio.to_thread(runtime.stop)
    pidfile=ROOT/'.runtime/server.pid'
    if pidfile.is_file() and pidfile.read_text().strip()==str(os.getpid()):pidfile.unlink()

app=FastAPI(title='Fieldlab',lifespan=lifespan)
install_access(app,access)

@app.get('/api/config')
def config():return {'mission':engine.config.model_dump(),'scene':scene(engine.config),'assets':{**(json.loads((ROOT/'assets/manifest.json').read_text()) if (ROOT/'assets/manifest.json').is_file() else {}),**{'city_'+key:value for key,value in (json.loads((ROOT/'assets/city-manifest.json').read_text()) if (ROOT/'assets/city-manifest.json').is_file() else {}).items()}}}

@app.put('/api/config')
def save_config(mission:Mission):
    try:engine.configure(mission)
    except ValueError as e:raise HTTPException(409,str(e))
    saved.parent.mkdir(parents=True,exist_ok=True)
    temp=saved.with_suffix('.tmp');temp.write_text(mission.model_dump_json(indent=2));temp.replace(saved)
    return config()

class Speeds(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    run_id:str
    ugv_speed:float|None=Field(default=None,ge=.2,le=10.)
    walking_speed:float|None=Field(default=None,ge=.3,le=5.)
    traffic_speed:float|None=Field(default=None,ge=.3,le=20.)

@app.patch('/api/speeds')
def speeds(request:Speeds):
    if request.run_id!=engine.run_id:raise HTTPException(409,'Speed change belongs to a previous run.')
    changes=request.model_dump(exclude_none=True,exclude={'run_id'})
    old=engine.config;engine.config=old.model_copy(update=changes)
    if engine.city:
        engine.city.mission=engine.config
        for actor in engine.city.actors.values():
            field='walking_speed' if actor['kind']=='person' else 'traffic_speed'
            if field in changes:actor['desired_speed']*=changes[field]/getattr(old,field)
    temp=saved.with_suffix('.tmp');temp.write_text(engine.config.model_dump_json(indent=2));temp.replace(saved)
    return {'accepted':True,'speeds':{k:getattr(engine.config,k) for k in ('ugv_speed','walking_speed','traffic_speed')}}

class PlacementPreview(BaseModel):
    mission:Mission

@app.post('/api/placement/preview')
def placement_preview(request:PlacementPreview):
    return {'mission':request.mission.model_dump(),'scene':scene(request.mission)}

placement_lock=asyncio.Lock()

class LivePlacement(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    x:float=Field(ge=-108,le=108)
    y:float=Field(ge=-108,le=108)
    yaw:float=Field(default=0.,ge=-3.141593,le=3.141593)
    run_id:str

@app.post('/api/actor/{name}/position')
async def actor_position(name:str,request:LivePlacement):
    if request.run_id!=engine.run_id:raise HTTPException(409,'Placement belongs to a previous run. Refresh the current scene.')
    if not engine.city or runtime.state!='running':raise HTTPException(409,'Initialize the living city before moving a live actor.')
    try:
        async with placement_lock:result=await asyncio.to_thread(engine.city.relocate,name,request.x,request.y,request.yaw)
    except ValueError as error:raise HTTPException(409,str(error))
    engine.event(f'Operator placed {name} at {request.x:.1f}, {request.y:.1f} m')
    return result

@app.get('/api/state')
def state():return engine.snapshot()

class Command(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:Literal['initialize','start','hold','resume','recall','recall_all','abort','pause_world','reset','camera','target_select','track_start','track_stop','target_confirm']
    request_id:str=Field(min_length=1,max_length=80)
    run_id:str
    drone_id:str|None=None
    target_id:str|None=Field(default=None,max_length=64,pattern=r'^[a-zA-Z0-9_-]+$')

@app.post('/api/command')
async def command(cmd:Command):
    if cmd.run_id!=engine.run_id:raise HTTPException(409,'This command belongs to a previous mission. Refresh the current state.')
    key=(cmd.run_id,cmd.request_id)
    if key in engine.seen_commands:return engine.seen_commands[key]
    try:
        if cmd.name=='reset':
            await asyncio.to_thread(runtime.stop);engine.configure(engine.config);vision.clear()
        elif cmd.name=='camera':
            if cmd.drone_id is not None and cmd.drone_id not in engine.drones:raise ValueError('Unknown drone.')
            if runtime.gz:runtime.gz.preview(cmd.drone_id)
        elif cmd.name=='target_select':engine.select_target(cmd.target_id)
        elif cmd.name=='track_start':engine.start_tracking(cmd.target_id)
        elif cmd.name=='track_stop':
            if not engine.follow or engine.state!='TRACKING':raise ValueError('No active tracking flight.')
            engine.follow.finish(engine,'Operator stopped tracking','stopped')
        elif cmd.name=='target_confirm':engine.confirm_target(cmd.target_id)
        else:engine.command(cmd.name,cmd.drone_id)
    except ValueError as e:raise HTTPException(409,str(e))
    result={'accepted':True,'request_id':cmd.request_id,'run_id':engine.run_id,'state':engine.state};engine.seen_commands[key]=result
    if len(engine.seen_commands)>500:engine.seen_commands.pop(next(iter(engine.seen_commands)))
    return result

@app.get('/api/camera/{did}')
def camera(did:str,raw:bool=False):
    image=(vision.raw if raw else vision.annotated).get(did)
    if image is None:return Response(status_code=204)
    return Response(image,media_type='image/jpeg',headers={'Cache-Control':'no-store'})

@app.get('/api/export')
def export():return {'mission':engine.config.model_dump(),'state':engine.snapshot(),'scene':scene(engine.config)}

@app.get('/api/target/{key}/thumbnail')
def target_thumbnail(key:str):
    image=vision.registry.thumbnail(key)
    if image is None:return Response(status_code=204)
    return Response(image,media_type='image/jpeg',headers={'Cache-Control':'no-store'})

@app.websocket('/api/live')
async def live(ws:WebSocket):
    if not (access.host_allowed(ws) and access.origin_allowed(ws,required=True) and access.authorized(ws)):
        await ws.close(code=1008);return
    await ws.accept()
    try:
        while True:await ws.send_json(engine.snapshot());await asyncio.sleep(.1)
    except (WebSocketDisconnect,RuntimeError):pass

if (ROOT/'assets').is_dir():app.mount('/assets-sim',StaticFiles(directory=ROOT/'assets'),name='assets-sim')
if (ROOT/'dist').is_dir():app.mount('/',StaticFiles(directory=ROOT/'dist',html=True),name='frontend')
