"""Observe actual bridged PX4 Gazebo camera frames and cv_bridge conversion."""
import argparse
import json
import time

from cv_bridge import CvBridge
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image


parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
args = parser.parse_args()
rclpy.init()
node = Node('px4_camera_probe')
bridge = CvBridge()
frames = []
camera_info = []
errors = []


def image_cb(msg):
    try:
        frame = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        if frame.shape != (msg.height, msg.width, 3):
            raise ValueError(f'converted shape {frame.shape}')
        frames.append({
            'stamp_ns': msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec,
            'received_s': time.monotonic(),
            'frame_id': msg.header.frame_id,
            'width': msg.width, 'height': msg.height,
            'encoding': msg.encoding, 'step': msg.step,
            'bytes': len(msg.data),
            'brightness_mean': round(float(np.mean(frame)), 2),
            'brightness_std': round(float(np.std(frame)), 2),
        })
    except Exception as exc:
        errors.append(str(exc))


node.create_subscription(Image, '/drones/uav01/camera/image_raw', image_cb, 10)
node.create_subscription(CameraInfo, '/drones/uav01/camera/camera_info',
                         lambda msg: camera_info.append(msg), 10)
start = time.monotonic()
while time.monotonic() - start < 65 and len(frames) < 15 and not errors:
    rclpy.spin_once(node, timeout_sec=.2)
result = {'result': 'FAIL', 'failure': ''}
try:
    assert not errors, f'cv_bridge: {errors[0]}'
    assert len(frames) >= 15, 'fewer than 15 actual image messages'
    assert camera_info, 'no CameraInfo message'
    assert all(f['width'] == 1280 and f['height'] == 960 for f in frames), 'wrong image resolution'
    assert all(f['stamp_ns'] > 0 and f['frame_id'] for f in frames), 'missing image stamp or frame ID'
    assert all(frames[i]['stamp_ns'] < frames[i + 1]['stamp_ns'] for i in range(len(frames) - 1)), 'image stamps not increasing'
    assert camera_info[-1].width == 1280 and camera_info[-1].height == 960, 'CameraInfo resolution mismatch'
    assert camera_info[-1].k[0] > 0 and camera_info[-1].k[4] > 0, 'CameraInfo focal lengths missing'
    result['result'] = 'PASS'
except AssertionError as exc:
    result['failure'] = str(exc)
finally:
    duration = frames[-1]['received_s'] - frames[0]['received_s'] if len(frames) > 1 else 0
    result.update(elapsed_s=round(time.monotonic() - start, 1),
                  frame_count=len(frames),
                  observed_fps=round((len(frames) - 1) / duration, 2) if duration > 0 else 0,
                  image=frames[-1] if frames else None,
                  camera_info={'width': camera_info[-1].width,
                               'height': camera_info[-1].height,
                               'frame_id': camera_info[-1].header.frame_id,
                               'fx': camera_info[-1].k[0],
                               'fy': camera_info[-1].k[4],
                               'cx': camera_info[-1].k[2],
                               'cy': camera_info[-1].k[5]} if camera_info else None,
                  conversion_errors=errors)
    with open(args.output, 'w') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2), flush=True)
    node.destroy_node()
    rclpy.shutdown()
raise SystemExit(0 if result['result'] == 'PASS' else 1)
