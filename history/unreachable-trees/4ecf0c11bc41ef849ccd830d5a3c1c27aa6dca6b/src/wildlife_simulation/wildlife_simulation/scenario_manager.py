import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class ScenarioManager(Node):
    def __init__(self):
        super().__init__('scenario_manager')
        self.pub=self.create_publisher(String,'/simulation/scenario',10)
        self.declare_parameter('scenario','search_demo')
        self.create_timer(2.0,self.tick)
    def tick(self):
        m=String(); m.data=self.get_parameter('scenario').value; self.pub.publish(m)

def main():
    rclpy.init(); n=ScenarioManager(); rclpy.spin(n); n.destroy_node(); rclpy.shutdown()
