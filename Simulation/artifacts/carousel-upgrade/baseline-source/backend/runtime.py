import os,signal,subprocess,time,threading,tempfile,shutil,json
from pathlib import Path
from .world import make_world
from .transport import GazeboBridge
from .px4 import Fleet

class Runtime:
    def __init__(self,root):
        self.root=root;self.processes=[];self.streams=[];self.gz=None;self.fleet=None;self.state='offline';self.progress='Ready to initialize';self.error=None;self.cancel=threading.Event();self.px4_root=None
    def start_process(self,name,command,cwd=None,env=None):
        logs=self.root/'.runtime/logs';logs.mkdir(parents=True,exist_ok=True);log=open(logs/f'{name}.log','w');self.streams.append(log)
        child=subprocess.Popen(command,cwd=cwd or self.root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);self.processes.append((name,child));return child
    def initialize(self,mission):
        if self.state!='offline':raise ValueError('Reset the current simulation before initializing another world.')
        self.state='starting';self.error=None;self.cancel.clear()
        self.thread=threading.Thread(target=self._start,args=(mission,),daemon=True);self.thread.start()
    def _start(self,mission):
        try:
            for folder in ('fuel','gazebo-logs','ros-logs'):(self.root/'.runtime'/folder).mkdir(parents=True,exist_ok=True)
            self.progress='Generating physical world and rack';world=make_world(self.root,mission)
            self.gz=GazeboBridge();self.progress='Starting Gazebo physics'
            gazebo=self.start_process('gazebo',['gz','sim','-s','-r','--headless-rendering',str(world)])
            deadline=time.monotonic()+60
            while 'carrier' not in self.gz.poses:
                if self.cancel.is_set():return
                if gazebo.poll() is not None:raise RuntimeError('Gazebo exited. See .runtime/logs/gazebo.log.')
                if time.monotonic()>deadline:raise RuntimeError('Gazebo did not publish physical poses within 60 seconds.')
                time.sleep(.2)
            ids=sorted({d for s in mission.stops for d in s.drones})
            if ids:
                self.start_process('xrce-agent',['MicroXRCEAgent','udp4','-p','8889'])
                self.fleet=Fleet(ids,self.gz)
            deps=Path(os.environ['FIELDLAB_DEPS']);build=deps/'PX4-Autopilot/build/px4_sitl_default'
            # Pinned PX4 rc scripts split paths containing spaces. Keep transient rootfs in
            # an owned, space-free temp directory and archive native logs back into the project.
            self.px4_root=Path(tempfile.mkdtemp(prefix='fieldlab-sitl-'))
            (self.root/'.runtime/runtime-info.json').write_text(json.dumps({'temporary_px4_root':str(self.px4_root),'reason':'PX4 startup scripts require a space-free rootfs path'}))
            for index,did in enumerate(ids):
                if self.cancel.is_set():return
                self.progress=f'Starting {did} · {index+1} / {len(ids)}'
                wd=self.px4_root/did;wd.mkdir(exist_ok=True)
                startup=wd/'rc.fieldlab'
                startup.write_text(f'. {build}/etc/init.d-posix/rcS\n'
                    f'param set MPC_XY_VEL_MAX {mission.flight_speed}\nparam set MPC_XY_CRUISE {mission.flight_speed}\n'
                    'param set MPC_ACC_HOR 2.0\nparam set MPC_ACC_HOR_MAX 2.0\n'
                    'param set MPC_Z_VEL_MAX_UP 1.5\nparam set MPC_Z_VEL_MAX_DN 0.7\n')
                env=dict(os.environ,PX4_SYS_AUTOSTART='4001',PX4_SIM_MODEL='gz_x500',PX4_GZ_MODEL_NAME=did,PX4_GZ_WORLD='fieldlab',PX4_GZ_STANDALONE='1',PX4_UXRCE_DDS_NS=did,PX4_UXRCE_DDS_PORT='8889')
                p=self.start_process(did,[str(build/'bin/px4'),'-d','-i',str(int(did[-2:])-1),'-w',str(wd),'-s',str(startup),str(build/'etc')],cwd=wd,env=env)
                deadline=time.monotonic()+50
                while not self.fleet.status(did)['fresh']:
                    if self.cancel.is_set():return
                    if p.poll() is not None:raise RuntimeError(f'{did} exited. See .runtime/logs/{did}.log.')
                    if time.monotonic()>deadline:raise RuntimeError(f'{did} telemetry timed out. See .runtime/logs/{did}.log.')
                    time.sleep(.2)
            self.state='running';self.progress='Physics online · waiting for mission start'
        except Exception as e:
            self.error=str(e);self.state='error';self.progress=str(e)
    def stop(self):
        # Stop mission ticks before telemetry transports are closed.
        self.state='stopping'
        self.cancel.set()
        if hasattr(self,'thread') and self.thread is not threading.current_thread():self.thread.join(timeout=3)
        if self.fleet:self.fleet.close();self.fleet=None
        if self.gz:self.gz.close();self.gz=None
        for _,p in reversed(self.processes):
            try:os.killpg(p.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        for _,p in self.processes:
            try:p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:os.killpg(p.pid,signal.SIGKILL)
                except ProcessLookupError:pass
        self.processes=[]
        for stream in self.streams:stream.close()
        if self.px4_root and self.px4_root.exists():
            archive=self.root/'artifacts/runs'/self.px4_root.name;archive.mkdir(parents=True,exist_ok=True)
            for did in self.px4_root.iterdir():
                if not did.is_dir():continue
                for p in did.rglob('*'):
                    if p.is_file() and not p.is_symlink() and p.suffix in ('.ulg','.bson'):
                        dst=archive/p.relative_to(self.px4_root);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
            shutil.rmtree(self.px4_root);self.px4_root=None
        self.streams=[];self.state='offline';self.progress='Ready to initialize'
    def health(self):
        return {'state':self.state,'progress':self.progress,'error':self.error,'processes':{name:('running' if p.poll() is None else 'exited') for name,p in self.processes}}
