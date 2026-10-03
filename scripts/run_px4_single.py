"""Own and stop only the Gazebo/agent/PX4/ROS process groups started here."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

root = Path(os.environ['WILDLIFE_WORKSPACE_DIR'])
deps = Path(os.environ['WILDLIFE_DEPS_DIR'])
run = Path(os.environ.get('WILDLIFE_RUN_DIR', '/tmp/wildlife-v03-run'))
run.mkdir(parents=True, exist_ok=True)
# This world declares its sensor systems; omit the optional upstream camera streaming plugin.
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
    env = dict(os.environ, PX4_SYS_AUTOSTART='4001', PX4_SIM_MODEL='gz_x500',
               PX4_UXRCE_DDS_NS='uav01', PX4_GZ_MODEL_POSE='0,0',
               PX4_UXRCE_DDS_PORT='8888', PX4_GZ_WORLD='wildlife_px4', PX4_GZ_STANDALONE='1')
    px4 = start('px4', [str(deps / 'PX4-Autopilot/build/px4_sitl_default/bin/px4'), '-d', '-i', '0'],
                cwd=deps / 'PX4-Autopilot', env=env)
    ros = start('ros', ['ros2', 'launch', 'wildlife_bringup', 'px4_single.launch.py',
                      'sitl_enabled:=true', 'vehicle_count:=1', *sys.argv[1:]])
    print('Single-UAV simulation started; logs:', run, flush=True)
    while True:
        for child in (agent, gz, px4, ros):
            if child.poll() is not None:
                raise RuntimeError('A simulation process exited; inspect ' + str(run))
        time.sleep(.25)
except KeyboardInterrupt:
    pass
finally:
    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
        for child in reversed(children):
            # A group can outlive its leader, so signal the group even after poll().
            try: os.killpg(child.pid, signum)
            except ProcessLookupError: pass
        deadline = time.monotonic() + (4 if signum != signal.SIGKILL else 1)
        while any(child.poll() is None for child in children) and time.monotonic() < deadline:
            time.sleep(.1)
    for child in children: child.wait()
    for stream in streams: stream.close()
