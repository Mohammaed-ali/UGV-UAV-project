"""Two real PX4 cameras -> one persistent Target with both witnesses."""
import argparse
import json
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from px4_msgs.msg import VehicleLandDetected, VehicleStatus
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import Bool
from wildlife_interfaces.msg import Detection, DroneCommand, DroneState, Target
from wildlife_simulation.px4_uav_adapter import versioned_topic


parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
args = parser.parse_args()
ids = ('uav01', 'uav02')
rclpy.init()
node = Node('px4_two_camera_fusion_probe')
states = {}
histories = {did: set() for did in ids}
ready = {did: False for did in ids}
status = {}
land = {}
flight = {did: {'gcs': False, 'offboard': False, 'armed': False} for did in ids}
info_counts = {did: 0 for did in ids}
detections = {did: [] for did in ids}
tracks = {}
track_ids = set()


def state_cb(msg):
    if msg.drone_id in ids:
        states[msg.drone_id] = msg
        histories[msg.drone_id].add(msg.state)


def detection_cb(msg):
    if msg.drone_id in ids and len(detections[msg.drone_id]) < 100:
        detections[msg.drone_id].append({
            'id': msg.detection_id, 'x': msg.position_world.x,
            'y': msg.position_world.y, 'confidence': msg.confidence,
            'stamp_ns': msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec,
        })


def track_cb(msg):
    track_ids.add(msg.target_id)
    tracks[msg.target_id] = msg


node.create_subscription(DroneState, '/drones/state', state_cb, 50)
node.create_subscription(Detection, '/detections/all', detection_cb, 50)
node.create_subscription(Target, '/targets/tracked', track_cb, 50)
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
    node.create_subscription(CameraInfo, f'/drones/{did}/camera/camera_info',
                             lambda msg, did=did: info_counts.update({did: info_counts[did] + 1}), 10)

deploy = node.create_publisher(DroneCommand, '/deployment/commands',
                               QoSProfile(depth=32, durability=DurabilityPolicy.TRANSIENT_LOCAL))
mission = node.create_publisher(DroneCommand, '/mission/drone_commands', 20)


def wait_for(label, condition, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.1)
        if condition():
            print('PASS', label, flush=True)
            return
    raise TimeoutError(label)


def send(pub, did, command):
    pub.publish(DroneCommand(drone_id=did, command=command))


start = time.monotonic()
result = {'result': 'FAIL', 'failure': ''}
try:
    wait_for('both camera vehicles ready',
             lambda: all(ready.values()) and all(did in states for did in ids)
             and all(info_counts[did] > 0 for did in ids), 90)
    for did in ids:
        send(deploy, did, DroneCommand.LAUNCH)
    wait_for('both camera vehicles searching',
             lambda: all(states[did].state == DroneState.SEARCHING for did in ids), 110)
    wait_for('one target with two real-camera witnesses',
             lambda: any(set(track.detecting_drones) == set(ids) for track in tracks.values()), 120)
    for did in ids:
        send(mission, did, DroneCommand.RETURN_HOME)
    wait_for('both returned and docked',
             lambda: all(states[did].state == DroneState.DOCKED for did in ids), 130)
    assert len(track_ids) == 1, 'same visual dummy created duplicate target identities'
    assert all(detections[did] for did in ids), 'one camera did not detect the target'
    for index, did in enumerate(ids, 1):
        assert status[did].system_id == index, f'{did} wrong system ID'
        assert all(flight[did].values()), f'{did} incomplete flight state'
        assert land[did].landed, f'{did} not landed'
        assert status[did].arming_state == VehicleStatus.ARMING_STATE_DISARMED, f'{did} not disarmed'
        assert min(math.hypot(d['x'] - 15., d['y'] - 8.) for d in detections[did]) < 5., f'{did} no plausible map localization'
        assert len(node.get_publishers_info_by_topic(f'/drones/{did}/camera/image_raw')) == 1, f'{did} missing bridged image'
    assert len(node.get_publishers_info_by_topic('/drones/state')) == 2, 'DroneState publisher count'
    result['result'] = 'PASS'
except (AssertionError, TimeoutError) as exc:
    result['failure'] = str(exc)
finally:
    result.update(elapsed_s=round(time.monotonic() - start, 1),
                  ready=ready, info_counts=info_counts,
                  states={did: states[did].state if did in states else None for did in ids},
                  state_histories={did: sorted(histories[did]) for did in ids},
                  flight=flight,
                  detection_counts={did: len(detections[did]) for did in ids},
                  minimum_target_error_m={did: round(min((math.hypot(d['x'] - 15., d['y'] - 8.) for d in detections[did])), 2) if detections[did] else None for did in ids},
                  track_ids=sorted(track_ids),
                  witnesses={tid: sorted(track.detecting_drones) for tid, track in tracks.items()},
                  landed={did: bool(land.get(did) and land[did].landed) for did in ids},
                  disarmed={did: bool(status.get(did) and status[did].arming_state == VehicleStatus.ARMING_STATE_DISARMED) for did in ids})
    with open(args.output, 'w') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2), flush=True)
    node.destroy_node()
    rclpy.shutdown()
raise SystemExit(0 if result['result'] == 'PASS' else 1)
