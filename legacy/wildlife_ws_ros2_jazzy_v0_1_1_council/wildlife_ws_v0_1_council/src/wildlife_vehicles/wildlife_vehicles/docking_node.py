import rclpy
from rclpy.node import Node
from wildlife_interfaces.msg import DroneState, TraySlot
TRAY={1:('uav01','uav02'),2:('uav03','uav04'),3:('uav05','uav06'),4:('uav07','uav08')}
class DockingNode(Node):
    def __init__(self):
        super().__init__('docking_manager'); self.declare_parameter('report_period',5.0); self.docked=set(); self.states={}
        self.pub=self.create_publisher(TraySlot,'/docking/status',10); self.create_subscription(DroneState,'/drones/state',self.cb,50); self.create_timer(float(self.get_parameter('report_period').value),self.report)
    def cb(self,m): self.states[m.drone_id]=m; self.docked.add(m.drone_id) if m.state==DroneState.DOCKED else None
    def report(self):
        for slot,(u,l) in TRAY.items():
            m=TraySlot(); m.slot_id=slot; m.upper_drone=u; m.lower_drone=l; m.upper_docked=u in self.docked; m.lower_docked=l in self.docked; self.pub.publish(m)
        self.get_logger().info(f'Docked total: {len(self.docked)}/8')
def main(args=None):
    rclpy.init(args=args); n=DockingNode(); rclpy.spin(n); n.destroy_node(); rclpy.shutdown()
