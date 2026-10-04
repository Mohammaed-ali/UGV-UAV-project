"""Mirror the logical UGV pose into Gazebo for examiner visualization.

This proxy has no collision geometry or navigation authority. Deployment
continues to use the established logical UGV waypoint events.
"""
import subprocess
import time

import rclpy
from rclpy.node import Node
from wildlife_interfaces.msg import UGVState


class UGVVisualProxy(Node):
    def __init__(self):
        super().__init__('ugv_visual_proxy')
        self.declare_parameter('world', 'wildlife_px4')
        self.declare_parameter('model', 'ugv_visual_proxy')
        self.declare_parameter('update_hz', 2.0)
        self.state = None
        self.received = 0.
        self.accepted = 0
        self.warned = False
        self.create_subscription(UGVState, '/ugv/state', self.state_cb, 10)
        self.create_timer(1. / float(self.get_parameter('update_hz').value), self.tick)

    def state_cb(self, msg):
        self.state, self.received = msg, time.monotonic()

    def tick(self):
        if self.state is None or time.monotonic() - self.received > 2.:
            return
        p = self.state.pose.pose.position
        model = self.get_parameter('model').value
        request = f'name: "{model}", position: {{x: {p.x}, y: {p.y}, z: 0.5}}, orientation: {{w: 1}}'
        try:
            response = subprocess.run(['gz', 'service', '-s',
                f'/world/{self.get_parameter("world").value}/set_pose',
                '--reqtype', 'gz.msgs.Pose', '--reptype', 'gz.msgs.Boolean',
                '--timeout', '200', '--req', request], capture_output=True, text=True, timeout=1)
            if response.returncode == 0 and 'data: true' in response.stdout:
                self.accepted += 1
                if self.accepted == 1:
                    self.get_logger().info('Gazebo UGV visual proxy follows logical ROS pose; no physical docking claim')
            elif not self.warned:
                self.get_logger().warning('Gazebo UGV visual proxy pose update unavailable')
                self.warned = True
        except subprocess.TimeoutExpired:
            if not self.warned:
                self.get_logger().warning('Gazebo UGV visual proxy service timeout')
                self.warned = True


def main(args=None):
    rclpy.init(args=args)
    node = UGVVisualProxy()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
