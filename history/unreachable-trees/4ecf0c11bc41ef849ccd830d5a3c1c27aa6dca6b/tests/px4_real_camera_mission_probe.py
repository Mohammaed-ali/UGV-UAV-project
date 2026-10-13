"""One real PX4 camera/OpenCV/map Detection -> standoff -> operator acceptance."""
import argparse
import json
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from px4_msgs.msg import VehicleLandDetected, VehicleStatus
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, String
from wildlife_interfaces.msg import Detection, DroneState, OperatorAlert, Target
from wildlife_interfaces.srv import OperatorDecision
from wildlife_simulation.px4_uav_adapter import versioned_topic


parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
parser.add_argument('--moving', action='store_true')
args = parser.parse_args()
rclpy.init()
node = Node('px4_real_camera_mission_probe')
states = {}
stages = set()
raw = {}
ready = False
images = 0
detections = []
assignments = {}
tracked_ids = set()
track_speeds = []
alerts = {}
phases = []
flight = {'gcs': False, 'offboard': False, 'armed': False}


def state_cb(msg):
    states[msg.drone_id] = msg
    if msg.drone_id == 'uav01':
        stages.add(msg.state)


def status_cb(msg):
    raw['status'] = msg
    flight['gcs'] |= not msg.gcs_connection_lost
    flight['offboard'] |= msg.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD
    flight['armed'] |= msg.arming_state == VehicleStatus.ARMING_STATE_ARMED


def detection_cb(msg):
    if len(detections) < 100:
        detections.append({'id': msg.detection_id, 'drone_id': msg.drone_id,
                           'x': msg.position_world.x, 'y': msg.position_world.y,
                           'confidence': msg.confidence,
                           'frame_id': msg.header.frame_id,
                           'stamp_ns': msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec})


def target_cb(msg):
    assignments.setdefault(msg.target_id, set()).add(msg.assigned_drone_id)


def tracked_cb(msg):
    tracked_ids.add(msg.target_id)
    track_speeds.append(math.hypot(msg.velocity_estimate.linear.x,
                                   msg.velocity_estimate.linear.y))


def phase_cb(msg):
    if 'Phase=' in msg.data:
        phase = msg.data.split('Phase=')[1].split()[0]
        if not phases or phase != phases[-1]:
            phases.append(phase)


def ready_cb(msg):
    global ready
    ready |= msg.data


def image_cb(msg):
    global images
    images += 1


node.create_subscription(DroneState, '/drones/state', state_cb, 50)
node.create_subscription(Detection, '/detections/all', detection_cb, 30)
node.create_subscription(Target, '/targets/assigned', target_cb, 20)
node.create_subscription(Target, '/targets/tracked', tracked_cb, 30)
node.create_subscription(OperatorAlert, '/operator/alerts',
                         lambda msg: alerts.update({msg.drone_id: msg}), 20)
node.create_subscription(String, '/mission/status', phase_cb, 10)
node.create_subscription(Bool, '/drones/uav01/ready', ready_cb, 10)
node.create_subscription(Image, '/drones/uav01/camera/image_raw', image_cb, 10)
node.create_subscription(VehicleStatus,
                         versioned_topic('/uav01', 'out', 'vehicle_status', VehicleStatus),
                         status_cb, qos_profile_sensor_data)
node.create_subscription(VehicleLandDetected,
                         versioned_topic('/uav01', 'out', 'vehicle_land_detected', VehicleLandDetected),
                         lambda msg: raw.update(land=msg), qos_profile_sensor_data)
client = node.create_client(OperatorDecision, '/operator/decision')
held = returned = False
hold_at = None
pending = None
start = time.monotonic()
result = {'result': 'FAIL', 'failure': ''}
try:
    while time.monotonic() - start < 220:
        rclpy.spin_once(node, timeout_sec=.1)
        if pending:
            if not pending.done():
                continue
            response = pending.result()
            if not response.accepted:
                raise AssertionError(response.message)
            pending = None
        alert = alerts.get('uav01')
        if alert and states.get('uav01') and states['uav01'].state == DroneState.AWAITING_OPERATOR:
            if not held or (not returned and time.monotonic() - hold_at >= 3):
                decision = (OperatorDecision.Request.RETURN if held
                            else OperatorDecision.Request.CONTINUE_HOLD)
                pending = client.call_async(OperatorDecision.Request(
                    target_id=alert.target_id, assigned_drone_id='uav01',
                    decision=decision, operator_notes='V0.4 real-camera acceptance'))
                if held:
                    returned = True
                else:
                    held = True
                    hold_at = time.monotonic()
        if states.get('uav01') and states['uav01'].state == DroneState.DOCKED and phases[-1:] == ['COMPLETE']:
            break
        if int(time.monotonic() - start) % 20 == 0 and time.monotonic() - getattr(node, 'printed', -100) > 1:
            print('progress', states.get('uav01').state if states.get('uav01') else None,
                  'images', images, 'detections', len(detections), phases[-1:], flush=True)
            node.printed = time.monotonic()
    assert set(states) == {'uav01'}, 'unexpected DroneState identities'
    assert states['uav01'].state == DroneState.DOCKED, 'vehicle not docked'
    assert raw.get('land') and raw['land'].landed, 'PX4 landing not measured'
    assert raw.get('status') and raw['status'].arming_state == VehicleStatus.ARMING_STATE_DISARMED, 'PX4 disarm not measured'
    assert phases[-1:] == ['COMPLETE'], 'mission not COMPLETE'
    assert ready and all(flight.values()), 'readiness/flight state missing'
    assert images >= 15, 'camera images missing'
    assert detections, 'no OpenCV Detection from real image'
    assert all(d['id'].startswith('uav01_cv_') and d['drone_id'] == 'uav01' and
               d['frame_id'] == 'map' and d['stamp_ns'] > 0 for d in detections), 'Detection identity/frame/stamp incorrect'
    errors = [math.hypot(d['x'] - 15., d['y'] - 8.) for d in detections]
    assert min(errors) < 5., 'camera geolocation never approached visual target'
    assert len(assignments) == 1 and list(assignments.values()) == [{'uav01'}], 'target assignment not unique'
    if args.moving:
        assert len(tracked_ids) == 1, 'moving target identity was not persistent'
        assert track_speeds and max(track_speeds) > .1, 'moving target velocity estimate missing'
    assert DroneState.STANDOFF in stages and DroneState.AWAITING_OPERATOR in stages, 'standoff/operator states missing'
    assert held and returned, 'HOLD/RETURN operator workflow missing'
    assert len(node.get_publishers_info_by_topic('/drones/state')) == 1, 'DroneState publisher count'
    result['result'] = 'PASS'
except AssertionError as exc:
    result['failure'] = str(exc)
finally:
    result.update(elapsed_s=round(time.monotonic() - start, 1),
                  state=states['uav01'].state if 'uav01' in states else None,
                  stages=sorted(stages), phases=phases, ready=ready, flight=flight,
                  landed=bool(raw.get('land') and raw['land'].landed),
                  disarmed=bool(raw.get('status') and raw['status'].arming_state == VehicleStatus.ARMING_STATE_DISARMED),
                  image_count=images, detection_count=len(detections),
                  detection_samples=detections[:10],
                  minimum_target_error_m=round(min((math.hypot(d['x'] - 15., d['y'] - 8.) for d in detections)), 2) if detections else None,
                  assignments={tid: sorted(dids) for tid, dids in assignments.items()},
                  moving_scenario=args.moving,
                  tracked_ids=sorted(tracked_ids),
                  maximum_track_speed_mps=round(max(track_speeds), 3) if track_speeds else None,
                  held=held, returned=returned)
    with open(args.output, 'w') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2), flush=True)
    node.destroy_node()
    rclpy.shutdown()
raise SystemExit(0 if result['result'] == 'PASS' else 1)
