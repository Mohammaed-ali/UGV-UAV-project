import math, time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy

# Retain one-shot deployment events for nodes joining during launch.
DEPLOYMENT_QOS = QoSProfile(depth=32, durability=DurabilityPolicy.TRANSIENT_LOCAL)
from wildlife_interfaces.msg import DroneCommand, DroneState, Target, OperatorAlert

class UAVNode(Node):
    def __init__(self):
        super().__init__('uav_manager')
        for name,default in {
            'drone_id':'uav01','slot_id':1,'is_upper_position':True,'search_altitude':10.0,'standoff_distance':12.0,
            'search_speed':1.2,'loiter_duration':20.0,'search_timeout':90.0,'battery_drain_per_second':0.15,
            'lane_spacing':5.0,'search_half_width':30.0,'standoff_altitude_offset':3.0,'motion_tolerance':0.5,'home_x':0.0,'home_y':0.0}.items(): self.declare_parameter(name,default)
        g=lambda k:self.get_parameter(k).value
        self.id=str(g('drone_id')); self.slot_id=int(g('slot_id')); self.is_upper=bool(g('is_upper_position')); self.alt=float(g('search_altitude')); self.standoff=float(g('standoff_distance')); self.speed=float(g('search_speed')); self.loiter=float(g('loiter_duration')); self.timeout=float(g('search_timeout')); self.drain=float(g('battery_drain_per_second')); self.lane=float(g('lane_spacing')); self.half_width=float(g('search_half_width')); self.alt_offset=float(g('standoff_altitude_offset')); self.tol=float(g('motion_tolerance')); self.home_x=float(g('home_x')); self.home_y=float(g('home_y'))
        self.launch_inhibited = False
        self.resume_state = DroneState.STORED
        self.pause_started = None
        self.state=DroneState.STORED; self.x=self.y=self.z=0.; self.battery=100.; self.target=None; self.search_start=None; self.loiter_start=None; self.last=time.monotonic(); self.lane_dir=1.; self.hold_position=False; self.alerted_target=None
        self.state_pub=self.create_publisher(DroneState,'/drones/state',20); self.alert_pub=self.create_publisher(OperatorAlert,'/operator/alerts',20)
        self.create_subscription(DroneCommand,'/deployment/commands',self.command_cb,DEPLOYMENT_QOS); self.create_subscription(DroneCommand,'/mission/drone_commands',self.command_cb,20); self.create_subscription(Target,'/targets/assigned',self.target_cb,20); self.create_subscription(Target,'/targets/operator_decision',self.decision_cb,20)
        self.create_timer(0.1,self.tick)
    def command_cb(self,m):
        if m.drone_id!=self.id: return
        if m.command in (DroneCommand.HOLD_POSITION, DroneCommand.RETURN_HOME):
            self.launch_inhibited = True
        elif m.command == DroneCommand.RESUME:
            self.launch_inhibited = False
        if m.command==DroneCommand.LAUNCH and self.state==DroneState.STORED and not self.launch_inhibited: self.state=DroneState.LAUNCHING; self.hold_position=False
        elif m.command==DroneCommand.RETURN_HOME and self.state not in (DroneState.STORED,DroneState.DOCKED): self.state=DroneState.RETURNING; self.hold_position=False
        elif m.command == DroneCommand.HOLD_POSITION and self.state not in (DroneState.STORED, DroneState.DOCKED, DroneState.PAUSED):
            self.resume_state = self.state
            self.pause_started = time.monotonic()
            self.state = DroneState.PAUSED
            self.hold_position = True
        elif m.command==DroneCommand.GO_TO_STANDOFF and self.target: self.state=DroneState.STANDOFF; self.hold_position=False
        elif m.command == DroneCommand.RESUME and self.state == DroneState.PAUSED:
            paused_for = time.monotonic() - self.pause_started
            if self.search_start is not None:
                self.search_start += paused_for
            if self.loiter_start is not None:
                self.loiter_start += paused_for
            self.state = self.resume_state
            self.hold_position = False
    def target_cb(self,m):
        if m.assigned_drone_id==self.id and m.target_id and self.state==DroneState.SEARCHING: self.target=m; self.state=DroneState.TARGET_DETECTED; self.alerted_target=None
    def decision_cb(self,m):
        if m.assigned_drone_id!=self.id or m.target_id!=(self.target.target_id if self.target else ''): return
        if self.state!=DroneState.AWAITING_OPERATOR: return
        if m.status==Target.CLEARED: self.state=DroneState.RETURNING
        elif m.status == Target.STANDOFF_HOLD:
            # Stay available for a later operator RETURN without another alert.
            self.hold_position = True
    def tick(self):
        self.drain_battery(); s=self.state
        if s==DroneState.LAUNCHING: self.state=DroneState.TAKEOFF
        elif s==DroneState.TAKEOFF:
            self.z=min(self.alt,self.z+self.speed*0.1)
            if self.z>=self.alt: self.state=DroneState.SEARCHING; self.search_start=time.monotonic()
        elif s==DroneState.SEARCHING:
            self.lawnmower_step()
            if self.search_start and time.monotonic()-self.search_start>=self.timeout: self.state=DroneState.LOITERING; self.loiter_start=time.monotonic()
        elif s==DroneState.LOITERING:
            if self.loiter_start and time.monotonic()-self.loiter_start>=self.loiter: self.state=DroneState.RETURNING
        elif s==DroneState.TARGET_DETECTED: self.state=DroneState.STANDOFF
        elif s==DroneState.STANDOFF and self.target:
            if self.move_to_standoff(): self.state=DroneState.AWAITING_OPERATOR; self.send_alert_once()
        elif s==DroneState.RETURNING:
            if self.move_toward(self.home_x,self.home_y,0.): self.state=DroneState.DOCKING
        elif s==DroneState.DOCKING:
            self.z=max(0.,self.z-self.speed*0.1)
            if self.z<=0.: self.state=DroneState.DOCKED
        self.publish()
    def lawnmower_step(self):
        self.x+=self.lane_dir*self.speed*0.1
        if abs(self.x)>=self.half_width: self.lane_dir*=-1.; self.y+=self.lane
    def move_to_standoff(self):
        if not self.target: return False
        p=self.target.pose.pose.position; return self.move_toward(p.x,p.y+self.standoff,self.alt+self.alt_offset)
    def move_toward(self,tx,ty,tz):
        dx,dy,dz=tx-self.x,ty-self.y,tz-self.z; d=math.sqrt(dx*dx+dy*dy+dz*dz)
        if d<=self.tol: self.x,self.y,self.z=tx,ty,tz; return True
        step=min(self.speed*0.1,d); self.x+=step*dx/d; self.y+=step*dy/d; self.z+=step*dz/d; return False
    def send_alert_once(self):
        if not self.target or self.alerted_target==self.target.target_id: return
        a=OperatorAlert(); a.header.stamp=self.get_clock().now().to_msg(); a.alert_id=f'alert_{self.id}_{self.target.target_id}'; a.drone_id=self.id; a.target_id=self.target.target_id; a.target_class=self.target.target_class; a.confidence=self.target.confidence; a.target_position=self.target.pose.pose.position; a.alert_message=f'{self.id} is holding standoff on {self.target.target_class}; operator decision required.'; a.severity=OperatorAlert.ACTION_REQUIRED; self.alert_pub.publish(a); self.alerted_target=self.target.target_id
    def drain_battery(self):
        now=time.monotonic(); dt=now-self.last; self.last=now
        if self.state not in (DroneState.STORED,DroneState.DOCKED): self.battery=max(0.,self.battery-self.drain*dt)
    def publish(self):
        m=DroneState(); m.header.stamp=self.get_clock().now().to_msg(); m.drone_id=self.id; m.state=self.state; m.pose.pose.position.x=self.x; m.pose.pose.position.y=self.y; m.pose.pose.position.z=self.z; m.battery_percent=self.battery; m.standoff_distance=self.standoff; m.slot_id=self.slot_id; m.is_upper_position=self.is_upper; m.assigned_target_id=self.target.target_id if self.target else ''; self.state_pub.publish(m)

def main(args=None):
    rclpy.init(args=args); n=UAVNode(); rclpy.spin(n); n.destroy_node(); rclpy.shutdown()
