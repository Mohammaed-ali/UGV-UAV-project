"""Eight-PX4 SPLIT deployment, measured separation, timeout/RTL and completion."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import time
import yaml

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from px4_msgs.msg import VehicleCommand, VehicleCommandAck, VehicleStatus, VehicleLandDetected
from std_msgs.msg import Bool, String
from wildlife_interfaces.msg import DeploymentRequest, DroneCommand, DroneState
from wildlife_simulation.px4_uav_adapter import versioned_topic

parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
args = parser.parse_args()
profile = yaml.safe_load(Path('src/wildlife_simulation/config/fleet_flight.yaml').read_text())['validation']
performance_samples = []
ids = [f'uav{i:02d}' for i in range(1, 9)]
rclpy.init()
node = Node('px4_fleet_flight_probe')
states, received, status, land = {}, {}, {}, {}
ready = {did: False for did in ids}
flight = {did: {'gcs': False, 'armed': False, 'offboard': False} for did in ids}
histories = {did: set() for did in ids}
commands = {did: [] for did in ids}
raw_received = {}
raw_intervals = {}
acks = {did: [] for did in ids}
launches, deployment_events, phases = [], [], []
min_horizontal = min_3d = math.inf
min_pair = None
separation_samples = 0
max_simultaneous_search = 0
premature_complete = False
start = time.monotonic()
last_sample = 0.
result = {'result': 'FAIL', 'failure': ''}


def raw_record(did, stream):
    key = did + '/' + stream
    now = time.monotonic()
    if key in raw_received:
        raw_intervals.setdefault(key, []).append(now - raw_received[key])
    raw_received[key] = now


def land_cb(msg, did):
    land[did] = msg
    raw_record(did, 'land')


def state_cb(msg):
    if msg.drone_id in ids:
        states[msg.drone_id] = msg
        received[msg.drone_id] = time.monotonic()
        histories[msg.drone_id].add(msg.state)


def phase_cb(msg):
    global premature_complete
    if 'Phase=' not in msg.data:
        return
    phase = msg.data.split('Phase=')[1].split()[0]
    if not phases or phase != phases[-1]:
        phases.append(phase)
    if phase == 'COMPLETE' and not (len(states) == 8 and all(m.state == DroneState.DOCKED for m in states.values())):
        premature_complete = True


node.create_subscription(DroneState, '/drones/state', state_cb, 200)
node.create_subscription(String, '/mission/status', phase_cb, 20)
node.create_subscription(DeploymentRequest, '/ugv/deployment_request',
    lambda m: deployment_events.append({'waypoint': m.waypoint_index, 'mode': m.deployment_mode}),
    __import__('wildlife_vehicles.deployment_node', fromlist=['DEPLOYMENT_QOS']).DEPLOYMENT_QOS)
node.create_subscription(DroneCommand, '/deployment/commands',
    lambda m: launches.append(m.drone_id) if m.command == DroneCommand.LAUNCH else None,
    __import__('wildlife_vehicles.deployment_node', fromlist=['DEPLOYMENT_QOS']).DEPLOYMENT_QOS)
for did in ids:
    def status_cb(msg, did=did):
        status[did] = msg
        raw_record(did, 'status')
        flight[did]['gcs'] |= not msg.gcs_connection_lost
        flight[did]['armed'] |= msg.arming_state == VehicleStatus.ARMING_STATE_ARMED
        flight[did]['offboard'] |= msg.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD
    node.create_subscription(VehicleStatus, versioned_topic('/' + did, 'out', 'vehicle_status', VehicleStatus), status_cb, qos_profile_sensor_data)
    node.create_subscription(VehicleLandDetected, versioned_topic('/' + did, 'out', 'vehicle_land_detected', VehicleLandDetected), lambda m, did=did: land_cb(m, did), qos_profile_sensor_data)
    node.create_subscription(Bool, f'/drones/{did}/ready', lambda m, did=did: ready.update({did: ready[did] or m.data}), 10)
    node.create_subscription(VehicleCommand, versioned_topic('/' + did, 'in', 'vehicle_command', VehicleCommand),
        lambda m, did=did: commands[did].append({'command': m.command, 'system': m.target_system}), qos_profile_sensor_data)
    node.create_subscription(VehicleCommandAck, versioned_topic('/' + did, 'out', 'vehicle_command_ack', VehicleCommandAck),
        lambda m, did=did: acks[did].append({'command': m.command, 'result': m.result}) if m.target_system == 255 and m.target_component == 1 else None, qos_profile_sensor_data)
try:
    while time.monotonic() - start < profile['deadline_s']:
        rclpy.spin_once(node, timeout_sec=.02)
        now = time.monotonic()
        if now - last_sample > .2 and len(states) == 8 and all(now - received.get(did, 0) < profile['state_max_receipt_age_s'] for did in ids):
            last_sample = now
            searching = sum(m.state == DroneState.SEARCHING for m in states.values())
            if searching > max_simultaneous_search and searching >= 4:
                ps = subprocess.run(['ps','-C','px4','-o','pid=,%cpu=,rss='], capture_output=True, text=True)
                performance_samples.append({'elapsed_s': round(now-start,1), 'searching': searching, 'px4_cpu_rss': ps.stdout.strip().splitlines()})
            max_simultaneous_search = max(max_simultaneous_search, searching)
            if any(status.get(did) and status[did].arming_state == VehicleStatus.ARMING_STATE_ARMED for did in ids):
                separation_samples += 1
                for i, did in enumerate(ids):
                    p = states[did].pose.pose.position
                    for other in ids[i+1:]:
                        q = states[other].pose.pose.position
                        horizontal = math.hypot(p.x - q.x, p.y - q.y)
                        distance = math.hypot(horizontal, p.z - q.z)
                        min_horizontal = min(min_horizontal, horizontal)
                        if distance < min_3d:
                            min_3d, min_pair = distance, [did, other]
        if len(states) == 8 and all(states[did].state == DroneState.DOCKED for did in ids) and phases[-1:] == ['COMPLETE']:
            break
        if now - getattr(node, 'printed', 0) > 15:
            node.printed = now
            print('progress', sum(ready.values()), {did: m.state for did, m in states.items()}, 'search', max_simultaneous_search, flush=True)
    assert len(states) == 8 and all(states[did].state == DroneState.DOCKED for did in ids), 'fleet not docked'
    assert phases[-1:] == ['COMPLETE'] and not premature_complete, 'incorrect mission COMPLETE semantics'
    assert all(ready.values()), 'fleet readiness missing'
    assert launches == ids, 'missing, duplicated or out-of-order launch command'
    assert deployment_events == [{'waypoint': 0, 'mode': 'SPLIT'}, {'waypoint': 1, 'mode': 'SPLIT'}], 'split deployment events incorrect'
    assert all(all(flight[did].values()) for did in ids), 'fleet arming/Offboard/GCS missing'
    assert all(status[did].system_id == i+1 for i,did in enumerate(ids)), 'system ID crossover'
    assert all(land.get(did) and land[did].landed and status[did].arming_state == VehicleStatus.ARMING_STATE_DISARMED for did in ids), 'fleet landing/disarm missing'
    assert max_simultaneous_search >= 4, 'no substantial simultaneous physical search'
    assert not any(DroneState.PAUSED in histories[did] for did in ids), 'vehicle fault occurred during fleet acceptance'
    assert separation_samples >= 20 and min_horizontal >= profile['minimum_horizontal_separation_m'], 'search/return separation below configured 3 m validation threshold'
    assert len(node.get_publishers_info_by_topic('/drones/state')) == 8, 'authoritative DroneState publisher count'
    for i, did in enumerate(ids):
        assert commands[did] and all(c['system'] == i+1 for c in commands[did]), f'{did} command crossover'
        assert any(a['result'] == VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED for a in acks[did]), f'{did} correlated ACK missing'
        assert {DroneState.TAKEOFF, DroneState.SEARCHING, DroneState.RETURNING, DroneState.DOCKED} <= histories[did], f'{did} missing states'
    result['result'] = 'PASS'
except (AssertionError, KeyboardInterrupt) as exc:
    result['failure'] = str(exc) or 'Validation interrupted'
finally:
    sample = subprocess.run(['ps','-C','px4','-o','pid=,%cpu=,rss='], capture_output=True, text=True)
    result.update(raw_telemetry_intervals={key: {'count': len(values), 'maximum_s': round(max(values),3), 'median_s': round(sorted(values)[len(values)//2],3)} for key, values in raw_intervals.items()}, performance_samples=performance_samples, validation_profile=profile, elapsed_s=round(time.monotonic()-start,1), readiness=ready, flight=flight,
        states={did: states[did].state if did in states else None for did in ids},
        state_histories={did: sorted(histories[did]) for did in ids}, launches=launches,
        deployment_events=deployment_events, phases=phases, premature_complete=premature_complete,
        max_simultaneous_search=max_simultaneous_search, separation_samples=separation_samples,
        minimum_horizontal_separation_m=round(min_horizontal,2) if math.isfinite(min_horizontal) else None,
        minimum_3d_separation_m=round(min_3d,2) if math.isfinite(min_3d) else None, minimum_pair=min_pair,
        landed={did: bool(land.get(did) and land[did].landed) for did in ids},
        disarmed={did: bool(status.get(did) and status[did].arming_state == VehicleStatus.ARMING_STATE_DISARMED) for did in ids},
        commands=commands, acknowledgements=acks, px4_process_sample=sample.stdout.strip().splitlines())
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
    node.destroy_node(); rclpy.shutdown()
raise SystemExit(0 if result['result']=='PASS' else 1)
