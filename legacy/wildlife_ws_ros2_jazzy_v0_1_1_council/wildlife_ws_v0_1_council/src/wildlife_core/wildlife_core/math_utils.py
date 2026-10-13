import math
import rclpy
from rclpy.node import Node

def distance_xy(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)

class CoreHeartbeat(Node):
    def __init__(self):
        super().__init__("wildlife_core_heartbeat")
        self.timer = self.create_timer(5.0, lambda: self.get_logger().info("core online"))

def main():
    rclpy.init()
    n = CoreHeartbeat()
    rclpy.spin(n)
    n.destroy_node()
    rclpy.shutdown()
