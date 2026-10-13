"""Live two-PX4 command, telemetry, ACK and map-origin isolation gate."""
import argparse
import json
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from px4_msgs.msg import (VehicleCommand, VehicleCommandAck, VehicleLandDetected,
                          VehicleLocalPosition, VehicleStatus)
from wildlife_interfaces.msg import DroneCommand, DroneState
from wildlife_simulation.px4_uav_adapter import versioned_topic


parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
args = parser.parse_args()
ids = ('uav01', 'uav02')
origins = {'uav01': (0., 0.), 'uav02': (0., -35.)}
rclpy.init()
node = Node('px4_two_isolation_probe')
states = {}
seen_states = {did: set() for did in ids}
raw = {did: {} for did in ids}
commands = {did: [] for did in ids}
acks = {did: [] for did in ids}
ready = {did: False for did in ids}
flight = {did: {'offboard': False, 'armed': False, 'gcs': False,
                'min_x': math.inf, 'max_x': -math.inf} for did in ids}
failures = []


def state_cb(msg):
    if msg.drone_id not in ids:
        failures.append(f'unexpected DroneState identity {msg.drone_id}')
        return
    did = msg.drone_id
    states[did] = msg
    seen_states[did].add(msg.state)
    x = msg.pose.pose.position.x
    flight[did]['min_x'] = min(flight[did]['min_x'], x)
    flight[did]['max_x'] = max(flight[did]['max_x'], x)
    local = raw[did].get('local')
    if local and local.xy_valid and local.z_valid:
        ox, oy = origins[did]
        if math.hypot(x - (local.y + ox), msg.pose.pose.position.y - (local.x + oy)) > 3.0:
            failures.append(f'{did} DroneState does not match its own PX4 local position')


node.create_subscription(DroneState, '/drones/state', state_cb, 50)
for did in ids:
    prefix = '/' + did

    def status_cb(msg, did=did):
        raw[did]['status'] = msg
        flight[did]['gcs'] |= not msg.gcs_connection_lost
        flight[did]['offboard'] |= msg.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD
        flight[did]['armed'] |= msg.arming_state == VehicleStatus.ARMING_STATE_ARMED

    node.create_subscription(VehicleStatus,
                             versioned_topic(prefix, 'out', 'vehicle_status', VehicleStatus),
                             status_cb, qos_profile_sensor_data)
    node.create_subscription(VehicleLocalPosition,
                             versioned_topic(prefix, 'out', 'vehicle_local_position', VehicleLocalPosition),
                             lambda msg, did=did: raw[did].update(local=msg), qos_profile_sensor_data)
    node.create_subscription(VehicleLandDetected,
                             versioned_topic(prefix, 'out', 'vehicle_land_detected', VehicleLandDetected),
                             lambda msg, did=did: raw[did].update(land=msg), qos_profile_sensor_data)
    node.create_subscription(VehicleCommand,
                             versioned_topic(prefix, 'in', 'vehicle_command', VehicleCommand),
                             lambda msg, did=did: commands[did].append(msg), qos_profile_sensor_data)
    node.create_subscription(VehicleCommandAck,
                             versioned_topic(prefix, 'out', 'vehicle_command_ack', VehicleCommandAck),
                             lambda msg, did=did: acks[did].append(msg), qos_profile_sensor_data)
    from std_msgs.msg import Bool
    node.create_subscription(Bool, f'/drones/{did}/ready',
                             lambda msg, did=did: ready.update({did: ready[did] or msg.data}), 10)

deploy_qos = QoSProfile(depth=32, durability=DurabilityPolicy.TRANSIENT_LOCAL)
deploy = node.create_publisher(DroneCommand, '/deployment/commands', deploy_qos)
mission = node.create_publisher(DroneCommand, '/mission/drone_commands', 20)


def wait_for(label, condition, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.1)
        if failures:
            raise AssertionError(failures[0])
        if condition():
            print('PASS', label, flush=True)
            return
    raise TimeoutError(label)


def send(pub, did, command):
    pub.publish(DroneCommand(drone_id=did, command=command))


start = time.monotonic()
result = {'result': 'FAIL', 'stages': [], 'failures': failures}
try:
    wait_for('both vehicles ready', lambda: all(ready.values()) and
             all('local' in raw[did] and 'status' in raw[did] for did in ids) and
             all(did in states for did in ids), 90)
    for did in ids:
        p = states[did].pose.pose.position
        ox, oy = origins[did]
        assert math.hypot(p.x - ox, p.y - oy) < 3.0, f'{did} map origin at rest'
        assert states[did].state == DroneState.STORED, f'{did} unexpectedly launched'
    assert not any(commands.values()), 'PX4 command before typed deployment'
    send(deploy, 'uav01', DroneCommand.LAUNCH)
    wait_for('uav01 searching while uav02 stored',
             lambda: states['uav01'].state == DroneState.SEARCHING and
             states['uav02'].state == DroneState.STORED, 100)
    assert not commands['uav02'], 'uav01 launch sent a PX4 command to uav02'
    send(deploy, 'uav02', DroneCommand.LAUNCH)
    wait_for('both searching', lambda: all(states[did].state == DroneState.SEARCHING for did in ids), 100)
    wait_for('both physically searching',
             lambda: all(flight[did]['max_x'] - flight[did]['min_x'] > 4. for did in ids), 45)
    send(mission, 'uav01', DroneCommand.HOLD_POSITION)
    wait_for('uav01 hold leaves uav02 searching',
             lambda: states['uav01'].state == DroneState.PAUSED and
             states['uav02'].state == DroneState.SEARCHING, 15)
    send(mission, 'uav01', DroneCommand.RESUME)
    wait_for('uav01 resume leaves uav02 searching',
             lambda: all(states[did].state == DroneState.SEARCHING for did in ids), 15)
    send(mission, 'uav01', DroneCommand.RETURN_HOME)
    wait_for('uav01 RTL leaves uav02 searching',
             lambda: states['uav01'].state in (DroneState.RETURNING, DroneState.DOCKED) and
             states['uav02'].state == DroneState.SEARCHING, 15)
    send(mission, 'uav02', DroneCommand.RETURN_HOME)
    wait_for('both measured docked', lambda: all(states[did].state == DroneState.DOCKED for did in ids), 130)
    for index, did in enumerate(ids, 1):
        status = raw[did]['status']
        assert raw[did]['land'].landed, f'{did} not landed'
        assert status.arming_state == VehicleStatus.ARMING_STATE_DISARMED, f'{did} not disarmed'
        assert all(c.target_system == index for c in commands[did]), f'{did} wrong command system ID'
        assert any(c.command == VehicleCommand.VEHICLE_CMD_NAV_RETURN_TO_LAUNCH for c in commands[did]), f'{did} no RTL command'
        assert any(a.target_system == 255 and a.target_component == 1 and
                   a.result == VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED for a in acks[did]), f'{did} no correlated accepted ACK'
        assert all(flight[did][key] for key in ('gcs', 'offboard', 'armed')), f'{did} incomplete flight state'
        assert flight[did]['max_x'] - flight[did]['min_x'] > 4., f'{did} did not search physically'
        assert len(node.get_publishers_info_by_topic(versioned_topic('/' + did, 'out', 'vehicle_status', VehicleStatus))) == 1, f'{did} raw telemetry publisher count'
    assert len(node.get_publishers_info_by_topic('/drones/state')) == 2, 'DroneState publisher count'
    result['result'] = 'PASS'
except (AssertionError, TimeoutError) as exc:
    failures.append(str(exc))
finally:
    result.update(elapsed_s=round(time.monotonic() - start, 1),
                  ready=ready,
                  states={did: states[did].state if did in states else None for did in ids},
                  state_histories={did: sorted(seen_states[did]) for did in ids},
                  flight=flight,
                  command_counts={did: len(commands[did]) for did in ids},
                  ack_counts={did: len(acks[did]) for did in ids},
                  raw_topics={did: [versioned_topic('/' + did, 'out', name, msg)
                                    for name, msg in [('vehicle_status', VehicleStatus),
                                                      ('vehicle_local_position', VehicleLocalPosition),
                                                      ('vehicle_command_ack', VehicleCommandAck)]] for did in ids})
    with open(args.output, 'w') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2), flush=True)
    node.destroy_node()
    rclpy.shutdown()
raise SystemExit(0 if result['result'] == 'PASS' else 1)
