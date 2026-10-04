"""Own the two-PX4 isolation runtime and stop only processes started here."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


root = Path(os.environ['WILDLIFE_WORKSPACE_DIR'])
deps = Path(os.environ['WILDLIFE_DEPS_DIR'])
run = Path(os.environ.get('WILDLIFE_RUN_DIR', '/tmp/wildlife-v04-two'))
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
    model = os.environ.get('WILDLIFE_PX4_MODEL', 'gz_x500')
    second_pose = os.environ.get('WILDLIFE_UAV02_GZ_POSE', '0,-35')
    px4 = []
    for index in range(2):
        did = f'uav{index + 1:02d}'
        env = dict(os.environ,
                   PX4_SYS_AUTOSTART=os.environ.get('WILDLIFE_PX4_AUTOSTART', '4001'),
                   PX4_SIM_MODEL=model,
                   PX4_UXRCE_DDS_NS=did,
                   PX4_GZ_MODEL_POSE='0,0' if index == 0 else second_pose,
                   PX4_UXRCE_DDS_PORT='8888', PX4_GZ_WORLD='wildlife_px4',
                   PX4_GZ_STANDALONE='1')
        px4.append(start(did, [px4_binary, '-d', '-i', str(index)],
                         cwd=deps / 'PX4-Autopilot', env=env))
    bridge_child = None
    if model == 'gz_x500_mono_cam_down':
        bridge = root / 'install/wildlife_simulation/share/wildlife_simulation/config/px4_two_camera_bridge.yaml'
        if not bridge.is_file():
            raise RuntimeError('Build wildlife_simulation to install ' + str(bridge))
        bridge_child = start('camera_bridge', ['ros2', 'run', 'ros_gz_bridge', 'parameter_bridge',
                                               '--ros-args', '-p', 'config_file:=' + str(bridge)])
    launch_file = sys.argv[1] if len(sys.argv) > 1 else 'px4_isolation.launch.py'
    ros = start('ros', ['ros2', 'launch', 'wildlife_bringup', launch_file,
                        *sys.argv[2:]])
    print('Two-PX4 simulation started; logs:', run, flush=True)
    while True:
        for child in (agent, gz, *px4, ros, bridge_child):
            if child is None:
                continue
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
