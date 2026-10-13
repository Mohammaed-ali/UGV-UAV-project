import time
import rclpy
from rclpy.node import Node
from wildlife_interfaces.msg import DroneCommand, UGVState, DeploymentRequest, TraySlot

TRAY={1:('uav01','uav02'),2:('uav03','uav04'),3:('uav05','uav06'),4:('uav07','uav08')}

class DeploymentNode(Node):
    def __init__(self):
        super().__init__('deployment_manager')
        self.declare_parameter('inter_drone_delay',3.0); self.declare_parameter('deployment_mode','SINGLE')
        self.delay=float(self.get_parameter('inter_drone_delay').value); self.default_mode=str(self.get_parameter('deployment_mode').value)
        self.cmd_pub=self.create_publisher(DroneCommand,'/deployment/commands',20); self.status_pub=self.create_publisher(TraySlot,'/deployment/status',20)
        self.create_subscription(DeploymentRequest,'/ugv/deployment_request',self.request_cb,10)
        self.sent=set(); self.pending=[]; self.last_send=0.0; self.active_slots=set(); self.create_timer(0.1,self.tick)
    def request_cb(self,msg):
        mode=msg.deployment_mode or self.default_mode; wp=int(msg.waypoint_index)
        if mode=='SINGLE' and wp==0: slots=[1,2,3,4]
        elif mode=='SPLIT' and wp==0: slots=[1,2]
        elif mode=='SPLIT' and wp==1: slots=[3,4]
        else: slots=[]
        for slot in slots:
            u,l=TRAY[slot]
            for did,upper in ((u,True),(l,False)):
                if did not in self.sent and did not in self.pending: self.pending.append((did,slot,upper))
        self.get_logger().info(f'Deployment request WP{wp} mode={mode}: {slots}')
    def tick(self):
        if not self.pending or time.monotonic()-self.last_send < self.delay: return
        did,slot,upper=self.pending.pop(0)
        if did in self.sent: return
        cmd=DroneCommand(); cmd.drone_id=did; cmd.command=DroneCommand.LAUNCH; self.cmd_pub.publish(cmd); self.sent.add(did); self.active_slots.add(slot); self.last_send=time.monotonic()
        self.publish_slot(slot); self.get_logger().info(f'Launch command: {did} slot={slot} {"UPPER" if upper else "LOWER"}')
    def publish_slot(self,slot):
        u,l=TRAY[slot]; m=TraySlot(); m.slot_id=slot; m.upper_drone=u; m.lower_drone=l; m.upper_launched=u in self.sent; m.lower_launched=l in self.sent; self.status_pub.publish(m)

def main(args=None):
    rclpy.init(args=args); n=DeploymentNode(); rclpy.spin(n); n.destroy_node(); rclpy.shutdown()
