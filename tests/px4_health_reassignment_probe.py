"""Two physical PX4 vehicles: health return, safe reassignment or two targets."""
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
from px4_msgs.msg import BatteryStatus, VehicleStatus, VehicleLandDetected, OffboardControlMode
from std_msgs.msg import String
import yaml
from wildlife_interfaces.msg import Detection, DroneCommand, DroneState, OperatorAlert, Target
from wildlife_interfaces.srv import OperatorDecision
from wildlife_simulation.px4_uav_adapter import versioned_topic

parser = argparse.ArgumentParser()
parser.add_argument('--scenario', choices=('low_battery', 'vehicle_unavailable', 'two_targets'), required=True)
parser.add_argument('--config', default='src/wildlife_simulation/config/health_scenarios.yaml')
parser.add_argument('--output', required=True)
args = parser.parse_args()
config = yaml.safe_load(Path(args.config).read_text())[args.scenario]
rclpy.init()
node = Node('px4_health_reassignment_probe')
ids = ('uav01', 'uav02')
states, status, land, alerts = {}, {}, {}, {}
histories = {did: set() for did in ids}
flight = {did: {'offboard': False, 'armed': False, 'gcs': False} for did in ids}
assignments, releases, phases, low_returns, cli_calls = [], [], [], [], []
heartbeats = {did: 0 for did in ids}
minimum_battery = {did: 100. for did in ids}
raw_minimum_battery = {did: 100. for did in ids}
command_pub = node.create_publisher(DroneCommand, '/mission/drone_commands', 20)
detection_pubs = [node.create_publisher(Detection, f'/drones/{did}/detections', 20) for did in ids]
client = node.create_client(OperatorDecision, '/operator/decision')
start = time.monotonic()
injected = paused_at = returned_at = heartbeat_at_fault = None
saved_params = {}
restored = False
held_at = {}
operator_done = set()
pending = None
sequence = 0
last_detection = 0.
result = {'result': 'FAIL', 'failure': ''}


def px4(module, *arguments):
    binary = Path(os.environ['WILDLIFE_DEPS_DIR']) / 'PX4-Autopilot/build/px4_sitl_default/bin' / ('px4-' + module)
    command = [str(binary), '--instance', '0', *map(str, arguments)]
    response = subprocess.run(command, capture_output=True, text=True, timeout=8)
    cli_calls.append({'arguments': command[1:], 'returncode': response.returncode,
                      'stdout': response.stdout.strip(), 'stderr': response.stderr.strip()})
    assert response.returncode == 0, f'PX4 {module} command failed: {response.stderr}'
    return response.stdout.strip()


def state_cb(msg):
    if msg.drone_id in ids:
        states[msg.drone_id] = msg
        histories[msg.drone_id].add(msg.state)
        if msg.battery_percent >= 0:
            minimum_battery[msg.drone_id] = min(minimum_battery[msg.drone_id], msg.battery_percent)


def assignment_cb(msg):
    item = {'target': msg.target_id, 'drone': msg.assigned_drone_id,
            'elapsed_s': round(time.monotonic() - start, 2)}
    if not any(a['target'] == item['target'] and a['drone'] == item['drone'] for a in assignments):
        assignments.append(item)


def phase_cb(msg):
    phase = msg.data.split('Phase=')[-1].split()[0]
    if not phases or phase != phases[-1]:
        phases.append(phase)


node.create_subscription(DroneState, '/drones/state', state_cb, 100)
node.create_subscription(Target, '/targets/assigned', assignment_cb, 20)
node.create_subscription(Target, '/targets/released', lambda m: releases.append({'target': m.target_id, 'drone': m.assigned_drone_id}), 20)
node.create_subscription(OperatorAlert, '/operator/alerts', lambda m: alerts.update({m.drone_id: m}), 20)
node.create_subscription(String, '/mission/status', phase_cb, 20)
node.create_subscription(DroneCommand, '/mission/drone_commands',
                         lambda m: low_returns.append(m.drone_id) if m.command == DroneCommand.RETURN_HOME else None, 20)
for did in ids:
    def status_cb(msg, did=did):
        status[did] = msg
        flight[did]['offboard'] |= msg.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD
        flight[did]['armed'] |= msg.arming_state == VehicleStatus.ARMING_STATE_ARMED
        flight[did]['gcs'] |= not msg.gcs_connection_lost
    node.create_subscription(VehicleStatus, versioned_topic('/' + did, 'out', 'vehicle_status', VehicleStatus), status_cb, qos_profile_sensor_data)
    node.create_subscription(VehicleLandDetected, versioned_topic('/' + did, 'out', 'vehicle_land_detected', VehicleLandDetected), lambda m, did=did: land.update({did: m}), qos_profile_sensor_data)
    node.create_subscription(BatteryStatus, versioned_topic('/' + did, 'out', 'battery_status', BatteryStatus),
                             lambda m, did=did: raw_minimum_battery.update({did: min(raw_minimum_battery[did], m.remaining * 100.)}) if math.isfinite(m.remaining) and m.remaining >= 0 else None, qos_profile_sensor_data)
    node.create_subscription(OffboardControlMode, versioned_topic('/' + did, 'in', 'offboard_control_mode', OffboardControlMode),
                             lambda m, did=did: heartbeats.update({did: heartbeats[did] + 1}), qos_profile_sensor_data)

try:
    while time.monotonic() - start < config['deadline_s']:
        rclpy.spin_once(node, timeout_sec=.05)
        now = time.monotonic()
        if pending and pending.done():
            response = pending.result()
            assert response.accepted, response.message
            pending = None
        if len(states) == 2 and all(DroneState.SEARCHING in histories[did] for did in ids) and now - last_detection > .5:
            sequence += 1
            for index, position in enumerate(config['target_positions_m']):
                detection = Detection(drone_id=ids[index], detection_id=f'health_{index}_{sequence}',
                                      target_class='dummy_animal', confidence=.95,
                                      covariance_xx=.04, covariance_yy=.04)
                detection.header.stamp = node.get_clock().now().to_msg()
                detection.header.frame_id = 'map'
                detection.position_world.x, detection.position_world.y = position
                detection_pubs[index].publish(detection)
            last_detection = now
        if args.scenario != 'two_targets' and injected is None and states.get('uav01') and states['uav01'].state == DroneState.STANDOFF:
            assert assignments and assignments[0]['drone'] == 'uav01', 'first assignment must select uav01'
            injected = now
            if config['injection'] == 'battery_drain':
                for name in ('SIM_BAT_DRAIN', 'SIM_BAT_MIN_PCT'):
                    saved_params[name] = float(px4('param', 'show', '-q', name))
                px4('param', 'set', 'SIM_BAT_MIN_PCT', config['battery_floor_percent'])
                px4('param', 'set', 'SIM_BAT_DRAIN', config['battery_drain_s'])
            else:
                px4('commander', 'mode', 'auto:loiter')
        if args.scenario == 'vehicle_unavailable' and injected and states['uav01'].state == DroneState.PAUSED:
            if paused_at is None:
                paused_at = now
                heartbeat_at_fault = heartbeats['uav01']
            if now - paused_at > 3 and returned_at is None:
                assert heartbeats['uav01'] - heartbeat_at_fault <= 2, 'adapter continued Offboard heartbeat after fault'
                assert not releases, 'target released during pause before confirmed return'
                command_pub.publish(DroneCommand(drone_id='uav01', command=DroneCommand.RETURN_HOME))
                returned_at = now
        for did in ids:
            if args.scenario != 'two_targets' and did == 'uav01':
                continue
            alert = alerts.get(did)
            if not pending and alert and states.get(did) and states[did].state == DroneState.AWAITING_OPERATOR:
                if did not in held_at:
                    held_at[did] = now
                    decision = OperatorDecision.Request.CONTINUE_HOLD
                elif now - held_at[did] >= 3 and did not in operator_done:
                    operator_done.add(did)
                    decision = OperatorDecision.Request.RETURN
                else:
                    continue
                pending = client.call_async(OperatorDecision.Request(target_id=alert.target_id,
                    assigned_drone_id=did, decision=decision, operator_notes='V0.4 health acceptance'))
        if len(states) == 2 and all(states[did].state == DroneState.DOCKED for did in ids) and phases[-1:] == ['COMPLETE']:
            break
        if now - getattr(node, 'printed', 0) > 15:
            node.printed = now
            print('progress', {did: msg.state for did, msg in states.items()}, assignments, minimum_battery, flush=True)
    assert all(states.get(did) and states[did].state == DroneState.DOCKED for did in ids), 'vehicles did not dock'
    assert phases[-1:] == ['COMPLETE'], 'mission not COMPLETE'
    assert all(land.get(did) and land[did].landed for did in ids), 'landing not measured'
    assert all(status.get(did) and status[did].arming_state == VehicleStatus.ARMING_STATE_DISARMED for did in ids), 'disarm not measured'
    assert all(all(flight[did].values()) for did in ids), 'flight/GCS states missing'
    assert len(node.get_publishers_info_by_topic('/drones/state')) == 2, 'authoritative DroneState count changed'
    if args.scenario == 'two_targets':
        assert len(assignments) == 2 and len({a['target'] for a in assignments}) == 2, 'two targets not distinct'
        assert {a['drone'] for a in assignments} == set(ids), 'one UAV assigned twice'
        assert operator_done == set(ids), 'both operator workflows missing'
    else:
        assert len(assignments) == 2 and len({a['target'] for a in assignments}) == 1, 'reassignment changed target identity'
        assert [a['drone'] for a in assignments] == list(ids), 'target did not reassign from uav01 to uav02'
        assert len(releases) == 1, 'assignment release missing/duplicated'
        assert operator_done == {'uav02'}, 'reassigned observer HOLD/RETURN missing'
        if args.scenario == 'low_battery':
            assert raw_minimum_battery['uav01'] < 20 and minimum_battery['uav01'] < 20, 'real low battery not observed'
            assert low_returns.count('uav01') == 1 and 'uav02' not in low_returns, 'low battery RTL not isolated and one-shot'
        else:
            assert paused_at is not None and returned_at is not None, 'fault/recovery not observed'
    result['result'] = 'PASS'
except (AssertionError, RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
    result['failure'] = str(exc)
finally:
    try:
        for name, value in saved_params.items():
            px4('param', 'set', name, value)
        restored = True
    except Exception as exc:
        result['result'] = 'FAIL'
        result['failure'] += '; parameter restoration: ' + str(exc)
    result.update(scenario=args.scenario, elapsed_s=round(time.monotonic() - start, 1),
        assignments=assignments, releases=releases, phases=phases,
        state_histories={did: sorted(histories[did]) for did in ids}, flight=flight,
        landed={did: bool(land.get(did) and land[did].landed) for did in ids},
        disarmed={did: bool(status.get(did) and status[did].arming_state == VehicleStatus.ARMING_STATE_DISARMED) for did in ids},
        minimum_battery_percent=minimum_battery, raw_minimum_battery_percent=raw_minimum_battery,
        mission_return_commands=low_returns, paused_fault_observed=paused_at is not None,
        saved_parameters=saved_params, parameters_restored=restored, px4_cli=cli_calls,
        operator_completed=sorted(operator_done))
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)
    node.destroy_node()
    rclpy.shutdown()
raise SystemExit(0 if result['result'] == 'PASS' else 1)
