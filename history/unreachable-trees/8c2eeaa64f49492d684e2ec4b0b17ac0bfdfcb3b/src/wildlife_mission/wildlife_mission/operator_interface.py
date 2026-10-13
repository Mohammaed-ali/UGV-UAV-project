import threading, datetime
import rclpy
from rclpy.node import Node
from wildlife_interfaces.msg import Target, OperatorAlert
from wildlife_interfaces.srv import OperatorDecision
class OperatorInterface(Node):
    def __init__(self):
        super().__init__('operator_interface'); self.declare_parameter('input_enabled',True); self.pending={}; self.pub=self.create_publisher(Target,'/targets/operator_decision',20); self.create_service(OperatorDecision,'/operator/decision',self.service_cb); self.create_subscription(OperatorAlert,'/operator/alerts',self.alert_cb,20)
        if bool(self.get_parameter('input_enabled').value): threading.Thread(target=self.keyboard_loop,daemon=True).start()
        self.get_logger().info('Operator interface ready: r <drone_id> = RETURN; h <drone_id> = CONTINUE HOLD')
    def alert_cb(self,a):
        if a.severity!=OperatorAlert.ACTION_REQUIRED: return
        self.pending[a.drone_id]=a
        print(
            f"\n[OPERATOR ACTION] drone={a.drone_id} target={a.target_id} "
            f"class={a.target_class} confidence={a.confidence:.0%} "
            f"position=({a.target_position.x:.1f},{a.target_position.y:.1f})\n"
            f"  r {a.drone_id} -> RETURN\n"
            f"  h {a.drone_id} -> CONTINUE HOLD\n"
        )
    def keyboard_loop(self):
        while rclpy.ok():
            try: parts=input().strip().split()
            except EOFError: return
            if len(parts)==2 and parts[0].lower() in ('r','h'): self.apply(parts[1],OperatorDecision.Request.RETURN if parts[0].lower()=='r' else OperatorDecision.Request.CONTINUE_HOLD)
    def service_cb(self,req,res):
        ok=self.apply(req.assigned_drone_id,req.decision,req.target_id); res.accepted=ok; res.message='Decision applied' if ok else 'No pending alert for drone/target'; res.timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(); return res
    def apply(self,drone_id,decision,target_id=''):
        if decision not in (OperatorDecision.Request.RETURN, OperatorDecision.Request.CONTINUE_HOLD):
            return False
        a=self.pending.get(drone_id)
        if a is None or (target_id and a.target_id!=target_id): self.get_logger().warning(f'No pending alert for {drone_id} target={target_id}'); return False
        t=Target(); t.header.stamp=self.get_clock().now().to_msg(); t.target_id=a.target_id; t.assigned_drone_id=drone_id; t.operator_notified=True; t.status=Target.CLEARED if decision==OperatorDecision.Request.RETURN else Target.STANDOFF_HOLD; self.pub.publish(t); self.pending.pop(drone_id,None) if decision == OperatorDecision.Request.RETURN else None; self.get_logger().info(f'Operator decision {drone_id}: {"RETURN" if t.status==Target.CLEARED else "CONTINUE HOLD"}'); return True
def main(args=None):
    rclpy.init(args=args); n=OperatorInterface(); rclpy.spin(n); n.destroy_node(); rclpy.shutdown()
