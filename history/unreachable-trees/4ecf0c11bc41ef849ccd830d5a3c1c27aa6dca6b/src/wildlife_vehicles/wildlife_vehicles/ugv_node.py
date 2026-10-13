import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy

# Retain one-shot deployment events for nodes joining during launch.
DEPLOYMENT_QOS = QoSProfile(depth=32, durability=DurabilityPolicy.TRANSIENT_LOCAL)
from wildlife_interfaces.msg import UGVState, DroneState, DeploymentRequest

class UGVNode(Node):
    def __init__(self):
        super().__init__('ugv_manager')
        self.declare_parameter('deployment_mode','SINGLE'); self.declare_parameter('waypoints',[0.,0.,20.,0.,20.,20.])
        self.declare_parameter('speed',1.5); self.declare_parameter('arrival_tolerance',0.5)
        self.declare_parameter('deploy_at_waypoint_indices',[0]); self.declare_parameter('publish_rate_hz',10.0)
        flat=list(self.get_parameter('waypoints').value); self.waypoints=list(zip(flat[::2],flat[1::2]))
        self.mode=str(self.get_parameter('deployment_mode').value); self.speed=float(self.get_parameter('speed').value)
        self.tol=float(self.get_parameter('arrival_tolerance').value); self.deploy_at=set(int(x) for x in self.get_parameter('deploy_at_waypoint_indices').value)
        if self.mode == 'SPLIT' and self.deploy_at == {0}:
            self.deploy_at = {0, 1}
        self.rate=float(self.get_parameter('publish_rate_hz').value)
        self.x,self.y=self.waypoints[0] if self.waypoints else (0.,0.); self.idx=0; self.state=UGVState.IDLE; self.deployment_sent=set()
        self.deployed=set(); self.docked=set()
        self.state_pub=self.create_publisher(UGVState,'/ugv/state',20); self.deploy_pub=self.create_publisher(DeploymentRequest,'/ugv/deployment_request',DEPLOYMENT_QOS)
        self.create_subscription(DroneState,'/drones/state',self.drone_cb,50); self.create_timer(1.0/self.rate,self.tick)
    def drone_cb(self,m):
        if m.state in (DroneState.LAUNCHING,DroneState.TAKEOFF,DroneState.SEARCHING,DroneState.TARGET_DETECTED,DroneState.STANDOFF,DroneState.AWAITING_OPERATOR,DroneState.RETURNING,DroneState.DOCKING,DroneState.DOCKED): self.deployed.add(m.drone_id)
        if m.state==DroneState.DOCKED: self.docked.add(m.drone_id)
    def tick(self):
        if not self.waypoints: self.state=UGVState.MISSION_COMPLETE; self.publish(); return
        if self.idx>=len(self.waypoints): self.state=UGVState.MISSION_COMPLETE; self.publish(); return
        tx,ty=self.waypoints[self.idx]; d=math.hypot(tx-self.x,ty-self.y)
        if d<=self.tol:
            self.x,self.y=tx,ty
            if self.idx in self.deploy_at and self.idx not in self.deployment_sent:
                req=DeploymentRequest(); req.header.stamp=self.get_clock().now().to_msg(); req.waypoint_index=self.idx; req.deployment_mode=self.mode
                req.slot_ids=[]; self.deploy_pub.publish(req); self.deployment_sent.add(self.idx); self.state=UGVState.DEPLOYING
            else: self.state=UGVState.ARRIVED
            if self.idx < len(self.waypoints)-1: self.idx+=1
            else: self.idx+=1
        else:
            self.state=UGVState.MOVING; step=min(self.speed/self.rate,d); self.x+=step*(tx-self.x)/d; self.y+=step*(ty-self.y)/d
        self.publish()
    def publish(self):
        m=UGVState(); m.header.stamp=self.get_clock().now().to_msg(); m.state=self.state; m.pose.pose.position.x=self.x; m.pose.pose.position.y=self.y
        m.current_waypoint_index=max(0,self.idx-1); m.drones_deployed=len(self.deployed); m.drones_docked=len(self.docked); m.deployment_mode=self.mode; self.state_pub.publish(m)

def main(args=None):
    rclpy.init(args=args); n=UGVNode(); rclpy.spin(n); n.destroy_node(); rclpy.shutdown()
