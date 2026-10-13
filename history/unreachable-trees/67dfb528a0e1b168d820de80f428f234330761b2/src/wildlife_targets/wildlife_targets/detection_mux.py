import rclpy
from rclpy.node import Node
from wildlife_interfaces.msg import Detection
class DetectionMux(Node):
    def __init__(self):
        super().__init__('detection_mux'); self.declare_parameter('queue_depth',50); q=int(self.get_parameter('queue_depth').value); self.pub=self.create_publisher(Detection,'/detections/all',q); self.subs=[]
        for i in range(1,9): self.subs.append(self.create_subscription(Detection,f'/drones/uav{i:02d}/detections',self.cb,q))
    def cb(self,m): self.pub.publish(m)
def main(args=None):
    rclpy.init(args=args); n=DetectionMux(); rclpy.spin(n); n.destroy_node(); rclpy.shutdown()
