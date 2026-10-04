"""Own a four/eight-PX4 runtime; the default profile remains stationary."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


count = int(sys.argv[1])
if count not in (4, 8):
    raise ValueError('fleet count must be 4 or 8')
root = Path(os.environ['WILDLIFE_WORKSPACE_DIR'])
deps = Path(os.environ['WILDLIFE_DEPS_DIR'])
run = Path(os.environ.get('WILDLIFE_RUN_DIR', f'/tmp/wildlife-v04-{count}'))
run.mkdir(parents=True, exist_ok=True)
os.environ.pop('GZ_SIM_SERVER_CONFIG_PATH', None)
children = []
streams = []


def start(name, command, cwd=None, env=None):
    stream = open(run / (name + '.log'), 'w')
    streams.append(stream)
    child = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream,
                             stderr=subprocess.STDOUT, start_new_session=True)
    children.append(child)
    return child


def interrupt(signum, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, interrupt)
signal.signal(signal.SIGINT, interrupt)
try:
    agent = start('agent', ['MicroXRCEAgent', 'udp4', '-p', '8888'])
    world = root / 'install/wildlife_simulation/share/wildlife_simulation/worlds/wildlife_px4.sdf'
    if not world.is_file():
        raise RuntimeError('Build wildlife_simulation to install ' + str(world))
    gz = start('gazebo', ['gz', 'sim', '-r', '-s', str(world)])
    if not os.environ.get('HEADLESS'):
        start('gazebo_gui', ['gz', 'sim', '-g'])
    px4_binary = str(deps / 'PX4-Autopilot/build/px4_sitl_default/bin/px4')
    px4 = []
    for index in range(count):
        did = f'uav{index + 1:02d}'
        x, y = (index % 4) * 12 - 18, -18 if index < 4 else 18
        env = dict(os.environ, PX4_SYS_AUTOSTART='4001', PX4_SIM_MODEL='gz_x500',
                   PX4_UXRCE_DDS_NS=did, PX4_GZ_MODEL_POSE=f'{x},{y}',
                   PX4_UXRCE_DDS_PORT='8888', PX4_GZ_WORLD='wildlife_px4',
                   PX4_GZ_STANDALONE='1')
        px4.append(start(did, [px4_binary, '-d', '-i', str(index)],
                         cwd=deps / 'PX4-Autopilot', env=env))
        # Serialize model creation/startup rather than overlapping Gazebo
        # sensor registration for all instances. Never relax PX4 readiness.
        deadline = time.monotonic() + 40.
        vehicle_log = run / (did + '.log')
        while time.monotonic() < deadline:
            if px4[-1].poll() is not None:
                raise RuntimeError(f'{did} exited during startup')
            if 'Startup script returned successfully' in vehicle_log.read_text():
                break
            time.sleep(.25)
        else:
            raise RuntimeError(f'{did} startup timed out; inspect {vehicle_log}')
        time.sleep(1.)
    launch_file = sys.argv[2] if len(sys.argv) > 2 else 'px4_fleet_isolation.launch.py'
    ros = start('ros', ['ros2', 'launch', 'wildlife_bringup',
                        launch_file, f'vehicle_count:={count}', *sys.argv[3:]])
    print(f'{count}-PX4 runtime started ({launch_file}); logs: {run}', flush=True)
    while True:
        for child in (agent, gz, *px4, ros):
            if child.poll() is not None:
                raise RuntimeError('A simulation process exited; inspect ' + str(run))
        time.sleep(.25)
except KeyboardInterrupt:
    pass
finally:
    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
        for child in reversed(children):
            try:
                os.killpg(child.pid, signum)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + (4 if signum != signal.SIGKILL else 1)
        while any(child.poll() is None for child in children) and time.monotonic() < deadline:
            time.sleep(.1)
    for child in children:
        child.wait()
    for stream in streams:
        stream.close()
