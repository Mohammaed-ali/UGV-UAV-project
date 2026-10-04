"""Live two-PX4 target mission with one assignment and operator HOLD/RETURN."""
import argparse
import json
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from px4_msgs.msg import VehicleLandDetected, VehicleStatus
from std_msgs.msg import Bool, String
from wildlife_interfaces.msg import Detection, DroneState, OperatorAlert, Target
from wildlife_interfaces.srv import OperatorDecision
from wildlife_simulation.px4_uav_adapter import versioned_topic


parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
parser.add_argument('--two-camera', action='store_true')
args = parser.parse_args()
ids = ('uav01', 'uav02')
rclpy.init()
node = Node('px4_two_mission_probe')
states = {}
histories = {did: set() for did in ids}
status = {}
land = {}
ready = {did: False for did in ids}
flight = {did: {'offboard': False, 'armed': False, 'gcs': False} for did in ids}
detections = {did: 0 for did in ids}
detection_samples = []
assignments = {}
track_witnesses = {}
alerts = {}
phases = []
second_searched_during_assignment = False
held = False
returned = False
hold_at = None
pending = None


def state_cb(msg):
    global second_searched_during_assignment
    if msg.drone_id in ids:
        states[msg.drone_id] = msg
        histories[msg.drone_id].add(msg.state)
        if msg.drone_id == 'uav02' and msg.state == DroneState.SEARCHING and assignments:
            second_searched_during_assignment = True


def assignment_cb(msg):
    global second_searched_during_assignment
    assignments.setdefault(msg.target_id, set()).add(msg.assigned_drone_id)
    other = 'uav02' if msg.assigned_drone_id == 'uav01' else 'uav01'
    if states.get(other) and states[other].state == DroneState.SEARCHING:
        second_searched_during_assignment = True


def phase_cb(msg):
    if 'Phase=' in msg.data:
        phase = msg.data.split('Phase=')[1].split()[0]
        if not phases or phase != phases[-1]:
            phases.append(phase)


node.create_subscription(DroneState, '/drones/state', state_cb, 50)
node.create_subscription(Target, '/targets/assigned', assignment_cb, 20)
node.create_subscription(Target, '/targets/tracked', lambda m: track_witnesses.setdefault(m.target_id, set()).update(m.detecting_drones), 30)
node.create_subscription(OperatorAlert, '/operator/alerts',
                         lambda msg: alerts.update({msg.drone_id: msg}), 20)
node.create_subscription(String, '/mission/status', phase_cb, 10)
def detection_cb(msg):
    detections[msg.drone_id] = detections.get(msg.drone_id, 0) + 1
    if len(detection_samples) < 200:
        detection_samples.append({'drone': msg.drone_id, 'x': msg.position_world.x, 'y': msg.position_world.y})

node.create_subscription(Detection, '/detections/all', detection_cb, 20)
for did in ids:
    prefix = '/' + did

    def status_cb(msg, did=did):
        status[did] = msg
        flight[did]['gcs'] |= not msg.gcs_connection_lost
        flight[did]['offboard'] |= msg.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD
        flight[did]['armed'] |= msg.arming_state == VehicleStatus.ARMING_STATE_ARMED

    node.create_subscription(VehicleStatus,
                             versioned_topic(prefix, 'out', 'vehicle_status', VehicleStatus),
                             status_cb, qos_profile_sensor_data)
    node.create_subscription(VehicleLandDetected,
                             versioned_topic(prefix, 'out', 'vehicle_land_detected', VehicleLandDetected),
                             lambda msg, did=did: land.update({did: msg}), qos_profile_sensor_data)
    node.create_subscription(Bool, f'/drones/{did}/ready',
                             lambda msg, did=did: ready.update({did: ready[did] or msg.data}), 10)

client = node.create_client(OperatorDecision, '/operator/decision')
start = time.monotonic()
result = {'result': 'FAIL', 'failure': ''}
try:
    while time.monotonic() - start < 260:
        rclpy.spin_once(node, timeout_sec=.1)
        if pending:
            if not pending.done():
                continue
            response = pending.result()
            if not response.accepted:
                raise AssertionError(response.message)
            pending = None
        observer = next(iter(next(iter(assignments.values()))), 'uav01') if assignments and args.two_camera else 'uav01'
        alert = alerts.get(observer)
        if alert and states.get(observer) and states[observer].state == DroneState.AWAITING_OPERATOR:
            if not held or (not returned and time.monotonic() - hold_at >= 3):
                decision = (OperatorDecision.Request.RETURN if held
                            else OperatorDecision.Request.CONTINUE_HOLD)
                pending = client.call_async(OperatorDecision.Request(
                    target_id=alert.target_id, assigned_drone_id=observer,
                    decision=decision, operator_notes='V0.4 two-PX4 acceptance'))
                if held:
                    returned = True
                else:
                    held = True
                    hold_at = time.monotonic()
        if len(states) == 2 and all(states[did].state == DroneState.DOCKED for did in ids) and phases[-1:] == ['COMPLETE']:
            break
        if int(time.monotonic() - start) % 20 == 0 and time.monotonic() - getattr(node, 'printed', -100) > 1:
            print('progress', {did: states[did].state for did in states}, phases[-1:], flush=True)
            node.printed = time.monotonic()
    assert set(states) == set(ids), 'missing DroneState'
    assert all(states[did].state == DroneState.DOCKED for did in ids), 'both vehicles not docked'
    assert phases[-1:] == ['COMPLETE'], 'mission not COMPLETE'
    assert all(ready.values()), 'both vehicles not ready'
    assert all(land.get(did) and land[did].landed for did in ids), 'PX4 landing not measured'
    assert all(status.get(did) and status[did].arming_state == VehicleStatus.ARMING_STATE_DISARMED for did in ids), 'PX4 disarm not measured'
    assert all(all(flight[did].values()) for did in ids), 'flight state missing'
    assert all(DroneState.SEARCHING in histories[did] for did in ids), 'both did not search'
    assert len(assignments) == 1 and len(next(iter(assignments.values()))) == 1, 'assignment not unique'
    if not args.two_camera:
        assert list(assignments.values()) == [{'uav01'}], 'synthetic assignment not unique to uav01'
    assert second_searched_during_assignment, 'uav02 not searching during assignment'
    assert detections['uav01'] > 0, 'no target detection'
    assert held and returned, 'operator HOLD/RETURN not exercised'
    if args.two_camera:
        assert all(detections[did] > 0 for did in ids), 'both real camera sources did not detect'
        assert len(track_witnesses) == 1 and list(track_witnesses.values()) == [set(ids)], 'real camera observations did not fuse into one target'
    assert len(node.get_publishers_info_by_topic('/drones/state')) == 2, 'DroneState publisher count'
    result['result'] = 'PASS'
except (AssertionError, TimeoutError) as exc:
    result['failure'] = str(exc)
finally:
    result.update(two_camera=args.two_camera, detection_samples=detection_samples, track_witnesses={tid: sorted(dids) for tid, dids in track_witnesses.items()}, elapsed_s=round(time.monotonic() - start, 1),
                  states={did: states[did].state if did in states else None for did in ids},
                  state_histories={did: sorted(histories[did]) for did in ids},
                  ready=ready, flight=flight,
                  landed={did: bool(land.get(did) and land[did].landed) for did in ids},
                  disarmed={did: bool(status.get(did) and status[did].arming_state == VehicleStatus.ARMING_STATE_DISARMED) for did in ids},
                  detections=detections,
                  assignments={tid: sorted(dids) for tid, dids in assignments.items()},
                  second_searched_during_assignment=second_searched_during_assignment,
                  held=held, returned=returned, phases=phases)
    with open(args.output, 'w') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2), flush=True)
    node.destroy_node()
    rclpy.shutdown()
raise SystemExit(0 if result['result'] == 'PASS' else 1)
