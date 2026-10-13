"""Real PX4 camera -> OpenCV blob -> map-frame Detection backend."""
import time

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from px4_msgs.msg import VehicleAttitude
from wildlife_interfaces.msg import Detection, DroneState

from wildlife_perception.camera_geometry import ground_intersection


def orange_blob(frame, min_area):
    """Return (u, v, area) for the largest saturated orange shape, if any."""
    if frame is None or frame.size == 0:
        return None
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0, 80, 80), (35, 255, 255))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)
    if area < min_area:
        return None
    moments = cv2.moments(contour)
    if moments['m00'] <= 0:
        return None
    return moments['m10'] / moments['m00'], moments['m01'] / moments['m00'], area


class OpenCVPX4Detector(Node):
    def __init__(self):
        super().__init__('opencv_px4_detector')
        defaults = {
            'drone_id': 'uav01', 'target_class': 'dummy_animal',
            'min_area': 250.0, 'max_process_hz': 5.0,
            'pose_timeout_s': .5, 'attitude_timeout_s': .5,
            'camera_info_timeout_s': 5.0,
            'mount_x': 0.0, 'mount_y': 0.0, 'mount_z': .10,
            'mount_pitch_rad': 1.5707963267948966,
            'ground_z': 0.0, 'localization_sigma_m': 2.0,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        self.did = str(self.get_parameter('drone_id').value)
        self.bridge = CvBridge()
        self.pose = self.attitude = self.info = None
        self.pose_at = self.attitude_at = self.info_at = 0.
        self.last_process = 0.
        self.sequence = 0
        self.pub = self.create_publisher(Detection, f'/drones/{self.did}/detections', 20)
        self.create_subscription(DroneState, '/drones/state', self.state_cb, 50)
        self.create_subscription(VehicleAttitude,
                                 f'/{self.did}/fmu/out/vehicle_attitude',
                                 self.attitude_cb, qos_profile_sensor_data)
        self.create_subscription(CameraInfo,
                                 f'/drones/{self.did}/camera/camera_info',
                                 self.info_cb, 10)
        self.create_subscription(Image,
                                 f'/drones/{self.did}/camera/image_raw',
                                 self.image_cb, 10)
        self.get_logger().info(f'Real camera OpenCV detector ready for {self.did}')

    def state_cb(self, msg):
        if msg.drone_id == self.did:
            self.pose = msg
            self.pose_at = time.monotonic()

    def attitude_cb(self, msg):
        self.attitude = msg
        self.attitude_at = time.monotonic()

    def info_cb(self, msg):
        self.info = msg
        self.info_at = time.monotonic()

    def image_cb(self, msg):
        now = time.monotonic()
        rate = float(self.get_parameter('max_process_hz').value)
        if rate <= 0 or now - self.last_process < 1. / rate:
            return
        self.last_process = now
        if not self.pose or self.pose.state not in (DroneState.SEARCHING, DroneState.STANDOFF):
            return
        if not self.attitude or not self.info:
            return
        for last, parameter in ((self.pose_at, 'pose_timeout_s'),
                                (self.attitude_at, 'attitude_timeout_s'),
                                (self.info_at, 'camera_info_timeout_s')):
            if now - last > float(self.get_parameter(parameter).value):
                return
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            found = orange_blob(frame, float(self.get_parameter('min_area').value))
            if found is None:
                return
            u, v, area = found
            info = self.info
            position = self.pose.pose.pose.position
            point = ground_intersection(
                (u, v), (info.k[0], info.k[4], info.k[2], info.k[5]),
                (position.x, position.y, position.z), self.attitude.q,
                mount_xyz=tuple(float(self.get_parameter(f'mount_{axis}').value)
                                for axis in 'xyz'),
                mount_pitch=float(self.get_parameter('mount_pitch_rad').value),
                ground_z=float(self.get_parameter('ground_z').value))
        except (ValueError, RuntimeError) as exc:
            self.get_logger().warning(f'{self.did} camera conversion/localization: {exc}')
            return
        if point is None:
            return
        self.sequence += 1
        detection = Detection()
        detection.header.stamp = msg.header.stamp
        detection.header.frame_id = 'map'
        detection.drone_id = self.did
        detection.detection_id = f'{self.did}_cv_{self.sequence:06d}'
        detection.target_class = str(self.get_parameter('target_class').value)
        detection.confidence = min(.99, .5 + area / (20 * float(self.get_parameter('min_area').value)))
        detection.position_world.x = point.x
        detection.position_world.y = point.y
        detection.position_world.z = point.z
        sigma = float(self.get_parameter('localization_sigma_m').value)
        detection.covariance_xx = sigma * sigma
        detection.covariance_yy = sigma * sigma
        detection.distance_from_drone = point.distance
        self.pub.publish(detection)
        if self.sequence == 1 or self.sequence % 20 == 0:
            self.get_logger().info(
                f'{self.did} image detection {detection.detection_id} '
                f'map=({point.x:.1f},{point.y:.1f}) confidence={detection.confidence:.2f}')


def main(args=None):
    rclpy.init(args=args)
    node = OpenCVPX4Detector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
