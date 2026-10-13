"""Follow the logical UGV's next waypoint using measured Gazebo odometry.

The logical mission remains V0.2's authority for waypoint/deployment timing;
this adapter is a visual follower, not a physical arrival feedback loop.
"""
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from wildlife_interfaces.msg import UGVState


def heading_command(x, y, yaw, tx, ty, speed, gain, limit, tolerance):
    distance = math.hypot(tx - x, ty - y)
    if distance <= tolerance:
        return 0.0, 0.0
    bearing = math.atan2(ty - y, tx - x)
    error = math.atan2(math.sin(bearing - yaw), math.cos(bearing - yaw))
    angular = max(-limit, min(limit, gain * error))
    linear = min(speed, distance) * max(0.0, math.cos(error))
    return linear, angular


class UGVGazeboAdapter(Node):
    def __init__(self):
        super().__init__('ugv_gazebo_adapter')
        defaults = {'waypoints': [0., 0., 20., 0., 20., 20.],
                    'linear_speed': 1.2, 'yaw_gain': 1.8,
                    'max_yaw_rate': 1.5, 'arrival_tolerance': 0.5,
                    'telemetry_timeout': 1.0}
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        values = {key: self.get_parameter(key).value for key in defaults}
        flat = values['waypoints']
        self.wps = list(zip(flat[::2], flat[1::2]))
        self.speed = values['linear_speed']
        self.gain = values['yaw_gain']
        self.limit = values['max_yaw_rate']
        self.tolerance = values['arrival_tolerance']
        self.timeout = values['telemetry_timeout']
        self.state = self.odom = None
        self.state_time = self.odom_time = 0.0
        self.pub = self.create_publisher(Twist, '/ugv/cmd_vel', 10)
        self.create_subscription(UGVState, '/ugv/state', self.cb, 10)
        self.create_subscription(Odometry, '/ugv/odom', self.odom_cb, qos_profile_sensor_data)
        self.create_timer(0.05, self.tick)

    def cb(self, msg):
        self.state = msg
        self.state_time = time.monotonic()

    def odom_cb(self, msg):
        self.odom = msg
        self.odom_time = time.monotonic()

    def tick(self):
        command = Twist()
        now = time.monotonic()
        if (self.state is None or self.odom is None
                or now - self.state_time > self.timeout
                or now - self.odom_time > self.timeout
                or self.state.state != UGVState.MOVING):
            self.pub.publish(command)
            return
        # current_waypoint_index is the last completed waypoint, not the target.
        next_index = int(self.state.current_waypoint_index) + 1
        if next_index < len(self.wps):
            pose = self.odom.pose.pose
            q = pose.orientation
            yaw = math.atan2(2 * (q.w*q.z + q.x*q.y), 1 - 2 * (q.y*q.y + q.z*q.z))
            tx, ty = self.wps[next_index]
            command.linear.x, command.angular.z = heading_command(
                pose.position.x, pose.position.y, yaw, tx, ty,
                self.speed, self.gain, self.limit, self.tolerance)
        self.pub.publish(command)


def main():
    rclpy.init()
    node = UGVGazeboAdapter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.pub.publish(Twist())
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
