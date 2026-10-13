"""Stationary four/eight-PX4 telemetry, identity and namespace scale gate."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from px4_msgs.msg import VehicleCommand, VehicleLocalPosition, VehicleStatus
from std_msgs.msg import Bool
from wildlife_interfaces.msg import DroneState
from wildlife_simulation.px4_uav_adapter import versioned_topic


parser = argparse.ArgumentParser()
parser.add_argument('--count', type=int, choices=(4, 8), required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
ids = [f'uav{i:02d}' for i in range(1, args.count + 1)]
origins = {did: ((i % 4) * 12 - 18, -18 if i < 4 else 18)
           for i, did in enumerate(ids)}
rclpy.init()
node = Node(f'px4_{args.count}_fleet_probe')
status = {}
local = {}
states = {}
commands = {did: 0 for did in ids}
ready = {did: False for did in ids}
gcs = {did: False for did in ids}


def state_cb(msg):
    if msg.drone_id in ids:
        states[msg.drone_id] = msg


node.create_subscription(DroneState, '/drones/state', state_cb, 100)
for did in ids:
    prefix = '/' + did

    def status_cb(msg, did=did):
        status[did] = msg
        gcs[did] |= not msg.gcs_connection_lost

    node.create_subscription(VehicleStatus,
                             versioned_topic(prefix, 'out', 'vehicle_status', VehicleStatus),
                             status_cb, qos_profile_sensor_data)
    node.create_subscription(VehicleLocalPosition,
                             versioned_topic(prefix, 'out', 'vehicle_local_position', VehicleLocalPosition),
                             lambda msg, did=did: local.update({did: msg}), qos_profile_sensor_data)
    node.create_subscription(VehicleCommand,
                             versioned_topic(prefix, 'in', 'vehicle_command', VehicleCommand),
                             lambda msg, did=did: commands.update({did: commands[did] + 1}), qos_profile_sensor_data)
    node.create_subscription(Bool, f'/drones/{did}/ready',
                             lambda msg, did=did: ready.update({did: ready[did] or msg.data}), 10)

start = time.monotonic()
result = {'result': 'FAIL', 'failure': ''}
try:
    deadline = start + (160 if args.count == 8 else 100)
    while time.monotonic() < deadline and not (
            all(ready.values()) and set(status) == set(ids)
            and set(local) == set(ids) and set(states) == set(ids)):
        rclpy.spin_once(node, timeout_sec=.1)
        if int(time.monotonic() - start) % 20 == 0 and time.monotonic() - getattr(node, 'printed', -100) > 1:
            print('ready', sum(ready.values()), '/', args.count, 'telemetry', len(status), flush=True)
            node.printed = time.monotonic()
    assert all(ready.values()), 'not all PX4 vehicles reached ready/preflight state'
    assert set(status) == set(ids) and set(local) == set(ids) and set(states) == set(ids), 'missing telemetry or DroneState'
    assert all(gcs.values()), 'QGC/GCS link missing for one or more PX4 vehicles'
    assert all(status[did].system_id == i + 1 for i, did in enumerate(ids)), 'MAV system ID crossover'
    assert all(status[did].arming_state == VehicleStatus.ARMING_STATE_DISARMED for did in ids), 'unexpected armed vehicle'
    assert all(states[did].state == DroneState.STORED for did in ids), 'unexpected deployment'
    assert all(count == 0 for count in commands.values()), 'PX4 command sent without deployment'
    assert len(node.get_publishers_info_by_topic('/drones/state')) == args.count, 'DroneState publisher count'
    for did in ids:
        ox, oy = origins[did]
        p = states[did].pose.pose.position
        measured = local[did]
        assert measured.xy_valid and measured.z_valid, f'{did} invalid PX4 position'
        assert math.hypot(p.x - ox, p.y - oy) < 3., f'{did} wrong map origin'
        assert math.hypot(p.x - (measured.y + ox), p.y - (measured.x + oy)) < 3., f'{did} map/local mismatch'
        topic = versioned_topic('/' + did, 'out', 'vehicle_status', VehicleStatus)
        assert len(node.get_publishers_info_by_topic(topic)) == 1, f'{did} telemetry publisher count'
        log = Path(os.environ['WILDLIFE_RUN_DIR']) / f'{did}.log'
        assert f'model: x500_{int(did[-2:]) - 1}' in log.read_text(), f'{did} Gazebo entity missing'
    result['result'] = 'PASS'
except AssertionError as exc:
    result['failure'] = str(exc)
finally:
    cpu = subprocess.run(['ps', '-C', 'px4', '-o', 'pid=,%cpu=,rss='],
                         capture_output=True, text=True, check=False)
    result.update(count=args.count, elapsed_s=round(time.monotonic() - start, 1),
                  ready=ready, gcs=gcs,
                  system_ids={did: status[did].system_id if did in status else None for did in ids},
                  drone_states={did: states[did].state if did in states else None for did in ids},
                  local_valid={did: bool(did in local and local[did].xy_valid and local[did].z_valid) for did in ids},
                  command_counts=commands,
                  px4_process_sample=cpu.stdout.strip().splitlines())
    with open(args.output, 'w') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2), flush=True)
    node.destroy_node()
    rclpy.shutdown()
raise SystemExit(0 if result['result'] == 'PASS' else 1)
