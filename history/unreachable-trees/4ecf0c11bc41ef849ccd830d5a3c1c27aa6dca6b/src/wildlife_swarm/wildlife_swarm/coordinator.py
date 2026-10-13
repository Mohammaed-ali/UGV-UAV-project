import math
import time
import rclpy
from rclpy.node import Node
from wildlife_interfaces.msg import Target, DroneState
class Coordinator(Node):
    def __init__(self):
        super().__init__('swarm_coordinator'); self.declare_parameter('assignment_period',1.0); self.declare_parameter('max_assignment_distance',50.0); self.declare_parameter('distance_weight',1.0); self.declare_parameter('target_confidence_weight',0.0)
        self.declare_parameter('minimum_battery_percent',25.0); self.declare_parameter('state_timeout_s',3.0)
        self.drones={}; self.last_seen={}; self.assigned=set(); self.assigned_targets=set(); self.pub=self.create_publisher(Target,'/targets/assigned',20); self.create_subscription(Target,'/targets/unassigned',self.target_cb,20); self.create_subscription(DroneState,'/drones/state',self.drone_cb,50); self.create_timer(float(self.get_parameter('assignment_period').value),self.report)
    def drone_cb(self,m):
        self.drones[m.drone_id]=m
        self.last_seen[m.drone_id]=time.monotonic()
        if m.state in (DroneState.RETURNING,DroneState.DOCKING,DroneState.DOCKED,DroneState.PAUSED): self.assigned.discard(m.drone_id)
    def eligible(self,d):
        if d.state!=DroneState.SEARCHING or d.drone_id in self.assigned:
            return False
        if time.monotonic()-self.last_seen.get(d.drone_id,-math.inf)>float(self.get_parameter('state_timeout_s').value):
            return False
        battery=float(d.battery_percent)
        return battery<0 or battery>=float(self.get_parameter('minimum_battery_percent').value)
    def target_cb(self,t):
        if t.status!=Target.UNASSIGNED or t.assigned_drone_id or t.target_id in self.assigned_targets: return
        cands=[d for d in self.drones.values() if self.eligible(d)]
        if not cands: return
        dw=float(self.get_parameter('distance_weight').value); cw=float(self.get_parameter('target_confidence_weight').value); maxd=float(self.get_parameter('max_assignment_distance').value)
        def cost(d):
            dist=math.hypot(d.pose.pose.position.x-t.pose.pose.position.x,d.pose.pose.position.y-t.pose.pose.position.y); return dw*dist+cw*(1.-t.confidence)
        best=min(cands,key=cost); dist=math.hypot(best.pose.pose.position.x-t.pose.pose.position.x,best.pose.pose.position.y-t.pose.pose.position.y)
        if dist>maxd: return
        t.assigned_drone_id=best.drone_id; t.status=Target.ASSIGNED; self.assigned.add(best.drone_id); self.assigned_targets.add(t.target_id); self.pub.publish(t); self.get_logger().info(f'Assigned {t.target_id} -> {best.drone_id} cost={cost(best):.2f}')
    def report(self): self.get_logger().debug(f'Coordinator: {sum(d.state==DroneState.SEARCHING for d in self.drones.values())} searching | {len(self.assigned)} assigned')
def main(args=None):
    rclpy.init(args=args); n=Coordinator(); rclpy.spin(n); n.destroy_node(); rclpy.shutdown()
