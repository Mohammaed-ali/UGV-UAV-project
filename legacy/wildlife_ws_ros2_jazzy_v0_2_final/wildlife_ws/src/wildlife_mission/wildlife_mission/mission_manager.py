import time
import rclpy
from rclpy.node import Node
from wildlife_interfaces.msg import DroneState, UGVState, Target, OperatorAlert, DroneCommand
from wildlife_interfaces.srv import MissionControl
class Phase:
    INIT='INIT'; DEPLOYING='DEPLOYING'; SEARCHING='SEARCHING'; TARGET_FOUND='TARGET_FOUND'; AWAITING_OPERATOR='AWAITING_OPERATOR'; RESOLVING='RESOLVING'; COMPLETE='COMPLETE'; PAUSED='PAUSED'; ABORTED='ABORTED'
class MissionManager(Node):
    def __init__(self):
        super().__init__('mission_manager'); self.declare_parameter('status_period',1.0); self.declare_parameter('expected_drones',8); self.phase=Phase.INIT; self.resume_phase=Phase.INIT; self.mission_id=f'M_{int(time.time())}'; self.drones={}; self.targets={}
        self.status_pub=self.create_publisher(__import__('std_msgs.msg',fromlist=['String']).String,'/mission/status',10); self.cmd_pub=self.create_publisher(DroneCommand,'/mission/drone_commands',20)
        self.create_service(MissionControl,'/mission/control',self.control_cb); self.create_subscription(UGVState,'/ugv/state',self.ugv_cb,20); self.create_subscription(DroneState,'/drones/state',self.drone_cb,50); self.create_subscription(Target,'/targets/assigned',self.target_cb,20); self.create_subscription(OperatorAlert,'/operator/alerts',self.alert_cb,20); self.create_subscription(Target,'/targets/operator_decision',self.decision_cb,20); self.create_timer(float(self.get_parameter('status_period').value),self.status)
    def control_cb(self,req,res):
        if req.command==MissionControl.Request.START:
            if self.phase in (Phase.ABORTED, Phase.COMPLETE):
                res.accepted = False
                res.message = 'Restart the launch for a new mission'
                res.mission_id = self.mission_id
                return res
            self.phase = self.resume_phase if self.phase == Phase.PAUSED else Phase.DEPLOYING
            self.broadcast(DroneCommand.RESUME)
        elif req.command == MissionControl.Request.PAUSE:
            if self.phase not in (Phase.PAUSED, Phase.ABORTED, Phase.COMPLETE):
                self.resume_phase = self.phase
                self.phase = Phase.PAUSED
                self.broadcast(DroneCommand.HOLD_POSITION)
        elif req.command==MissionControl.Request.ABORT: self.phase=Phase.ABORTED; self.broadcast(DroneCommand.RETURN_HOME)
        elif req.command == MissionControl.Request.RESET:
            # No cross-node reset protocol exists; never claim to reset vehicles.
            res.accepted = False
            res.mission_id = self.mission_id
            res.message = 'Restart the launch to reset vehicle, deployment and target state'
            return res
        else: res.accepted=False; res.mission_id=self.mission_id; res.message='Unknown command'; return res
        res.accepted=True; res.mission_id=self.mission_id; res.message=f'Command {req.command} applied'; return res
    def broadcast(self,cmd):
        drone_ids = set(self.drones) | {f'uav{i:02d}' for i in range(1, int(self.get_parameter('expected_drones').value) + 1)}
        for did in sorted(drone_ids):
            m=DroneCommand(); m.drone_id=did; m.command=cmd; self.cmd_pub.publish(m)
    def ugv_cb(self,m):
        if m.state==UGVState.DEPLOYING and self.phase==Phase.INIT: self.phase=Phase.DEPLOYING
    def drone_cb(self,m):
        self.drones[m.drone_id]=m
        if self.phase == Phase.INIT and any(d.state not in (DroneState.STORED, DroneState.DOCKED) for d in self.drones.values()):
            self.phase = Phase.DEPLOYING
        if self.phase==Phase.DEPLOYING and any(d.state==DroneState.SEARCHING for d in self.drones.values()): self.phase=Phase.SEARCHING
        if self.phase==Phase.ABORTED and len(self.drones) >= int(self.get_parameter("expected_drones").value) and all(d.state in (DroneState.DOCKED,DroneState.STORED) for d in self.drones.values()): self.phase=Phase.COMPLETE
        expected = int(self.get_parameter('expected_drones').value)
        if self.phase not in (Phase.INIT, Phase.PAUSED, Phase.ABORTED, Phase.COMPLETE):
            if len(self.drones) >= expected and all(d.state == DroneState.DOCKED for d in self.drones.values()):
                self.phase = Phase.COMPLETE
            elif self.phase == Phase.AWAITING_OPERATOR and not any(d.state == DroneState.AWAITING_OPERATOR for d in self.drones.values()):
                self.phase = Phase.RESOLVING
    def target_cb(self,m): self.targets[m.target_id]=m; self.phase=Phase.TARGET_FOUND if self.phase==Phase.SEARCHING else self.phase
    def alert_cb(self,m):
        if m.severity==OperatorAlert.ACTION_REQUIRED and self.phase not in (Phase.PAUSED, Phase.ABORTED, Phase.COMPLETE): self.phase=Phase.AWAITING_OPERATOR
    def decision_cb(self,m):
        if m.target_id in self.targets: self.targets[m.target_id].status=m.status
        if not any(d.state==DroneState.AWAITING_OPERATOR for d in self.drones.values()) and self.phase==Phase.AWAITING_OPERATOR: self.phase=Phase.RESOLVING
    def status(self):
        s=sum(d.state==DroneState.SEARCHING for d in self.drones.values()); w=sum(d.state==DroneState.AWAITING_OPERATOR for d in self.drones.values()); r=sum(d.state==DroneState.RETURNING for d in self.drones.values()); k=sum(d.state==DroneState.DOCKED for d in self.drones.values()); line=f'[{self.mission_id}] Phase={self.phase} Targets={len(self.targets)} Searching={s} Awaiting={w} Returning={r} Docked={k}/{int(self.get_parameter("expected_drones").value)}'; self.get_logger().info(line); from std_msgs.msg import String; m=String(); m.data=line; self.status_pub.publish(m)
def main(args=None):
    rclpy.init(args=args); n=MissionManager(); rclpy.spin(n); n.destroy_node(); rclpy.shutdown()
