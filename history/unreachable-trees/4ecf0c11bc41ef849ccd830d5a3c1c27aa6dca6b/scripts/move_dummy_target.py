"""Move the Gazebo visual dummy along a YAML-configured waypoint loop."""
import argparse
import json
import signal
import subprocess
import time

import yaml

from wildlife_simulation.target_motion import waypoint_position


parser = argparse.ArgumentParser()
parser.add_argument('--scenario', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
with open(args.scenario) as stream:
    scenario = yaml.safe_load(stream)
world = scenario['world']
model = scenario['model']
height = float(scenario['height_m'])
speed = float(scenario['speed_mps'])
rate = float(scenario['update_hz'])
waypoints = scenario['waypoints_m']
if rate <= 0:
    raise ValueError('update_hz must be positive')


def interrupt(signum, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, interrupt)
signal.signal(signal.SIGTERM, interrupt)
start = time.monotonic()
accepted = 0
failures = 0
samples = []
try:
    while True:
        elapsed = time.monotonic() - start
        x, y = waypoint_position(waypoints, speed, elapsed)
        request = (f'name: "{model}", position: {{x: {x:.4f}, y: {y:.4f}, '
                   f'z: {height:.4f}}}, orientation: {{w: 1}}')
        response = subprocess.run(
            ['gz', 'service', '-s', f'/world/{world}/set_pose',
             '--reqtype', 'gz.msgs.Pose', '--reptype', 'gz.msgs.Boolean',
             '--timeout', '1000', '--req', request],
            capture_output=True, text=True, timeout=3, check=False)
        if response.returncode == 0 and 'data: true' in response.stdout:
            accepted += 1
            if len(samples) < 100:
                samples.append([round(elapsed, 2), round(x, 3), round(y, 3)])
        else:
            failures += 1
            if failures >= 20 and accepted == 0:
                raise RuntimeError('Gazebo set_pose never accepted target motion')
        time.sleep(max(0., 1. / rate - (time.monotonic() - start - elapsed)))
except KeyboardInterrupt:
    pass
finally:
    result = {'result': 'PASS' if accepted > 2 else 'FAIL',
              'scenario': args.scenario, 'model': model,
              'accepted_updates': accepted, 'failed_updates': failures,
              'samples': samples}
    with open(args.output, 'w') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2), flush=True)
