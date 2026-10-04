import rclpy
from rclpy.node import Node
from wildlife_interfaces.msg import Target
class TargetManager(Node):
    def __init__(self):
        super().__init__('target_manager'); self.declare_parameter('report_period',5.0); self.db={}; self.registry_pub=self.create_publisher(Target,'/targets/registry',20); self.unassigned_pub=self.create_publisher(Target,'/targets/unassigned',20); self.create_subscription(Target,'/targets/tracked',self.tracked_cb,30); self.create_subscription(Target,'/targets/assigned',self.assigned_cb,20); self.create_subscription(Target,'/targets/released',self.released_cb,20); self.create_subscription(Target,'/targets/operator_decision',self.decision_cb,20); self.create_timer(float(self.get_parameter('report_period').value),self.report)
    def tracked_cb(self,t):
        old=self.db.get(t.target_id)
        if old and t.status != Target.LOST:
            t.status=old.status; t.assigned_drone_id=old.assigned_drone_id; t.operator_notified=old.operator_notified
        self.db[t.target_id]=t; self.publish(t)
    def assigned_cb(self,t):
        cur=self.db.get(t.target_id,t); cur.assigned_drone_id=t.assigned_drone_id; cur.status=Target.ASSIGNED; self.db[t.target_id]=cur; self.publish(cur)
    def released_cb(self,t):
        cur=self.db.get(t.target_id)
        if (not cur or cur.assigned_drone_id!=t.assigned_drone_id or
                cur.status in (Target.CLEARED,Target.LOST)):
            return
        cur.assigned_drone_id=''; cur.status=Target.UNASSIGNED; cur.operator_notified=False
        self.publish(cur)
    def decision_cb(self,t):
        if t.target_id not in self.db: return
        cur=self.db[t.target_id]; cur.status=t.status; cur.assigned_drone_id=t.assigned_drone_id or cur.assigned_drone_id; cur.operator_notified=True; self.db[t.target_id]=cur; self.publish(cur)
    def publish(self,t):
        self.registry_pub.publish(t)
        if t.status==Target.UNASSIGNED: self.unassigned_pub.publish(t)
    def report(self):
        counts={}
        for t in self.db.values(): counts[t.status]=counts.get(t.status,0)+1
        self.get_logger().info(f'Target registry: {len(self.db)} targets | {counts}')
def main(args=None):
    rclpy.init(args=args); n=TargetManager(); rclpy.spin(n); n.destroy_node(); rclpy.shutdown()
