import math, time
import rclpy
from rclpy.node import Node
from wildlife_interfaces.msg import Detection, Target
class Track:
    def __init__(self,det,tid,alpha):
        self.tid=tid; self.cls=det.target_class; self.x=det.position_world.x; self.y=det.position_world.y; self.conf=det.confidence; self.covx=det.covariance_xx; self.covy=det.covariance_yy; self.witnesses={det.drone_id}; self.count=1; self.last=time.monotonic(); self.alpha=alpha
    def update(self,det):
        self.x=(1-self.alpha)*self.x+self.alpha*det.position_world.x; self.y=(1-self.alpha)*self.y+self.alpha*det.position_world.y; self.conf=max(self.conf,det.confidence); self.covx=max(.01,self.covx*.95); self.covy=max(.01,self.covy*.95); self.witnesses.add(det.drone_id); self.count+=1; self.last=time.monotonic()
class Tracker(Node):
    def __init__(self):
        super().__init__('target_tracker'); self.declare_parameter('gate_radius',3.0); self.declare_parameter('alpha',.25); self.declare_parameter('stale_timeout',15.0); self.declare_parameter('minimum_confidence',.5); self.declare_parameter('report_period',5.0)
        self.gate=float(self.get_parameter('gate_radius').value); self.alpha=float(self.get_parameter('alpha').value); self.timeout=float(self.get_parameter('stale_timeout').value); self.min_conf=float(self.get_parameter('minimum_confidence').value); self.tracks={}; self.next_id=1; self.pub=self.create_publisher(Target,'/targets/tracked',20); self.create_subscription(Detection,'/detections/all',self.cb,50); self.create_timer(float(self.get_parameter('report_period').value),self.expire)
    def cb(self,d):
        if d.confidence<self.min_conf: return
        t=self.associate(d)
        if t is None: t=Track(d,f'tgt_{self.next_id:03d}',self.alpha); self.next_id+=1; self.tracks[t.tid]=t
        else: t.update(d)
        self.publish(t,d.header.stamp)
    def associate(self,d):
        best=None; bd=self.gate
        for t in self.tracks.values():
            dist=math.hypot(t.x-d.position_world.x,t.y-d.position_world.y)
            if dist<bd and t.cls==d.target_class: best,bd=t,dist
        return best
    def publish(self,t,stamp):
        m=Target(); m.header.stamp=stamp; m.target_id=t.tid; m.target_class=t.cls; m.confidence=t.conf; m.pose.pose.position.x=t.x; m.pose.pose.position.y=t.y; m.detecting_drones=list(sorted(t.witnesses)); m.status=Target.UNASSIGNED; m.detection_count=t.count; m.fused_covariance_xx=t.covx; m.fused_covariance_yy=t.covy; self.pub.publish(m)
    def expire(self):
        now=time.monotonic()
        for t in list(self.tracks.values()):
            if now-t.last>self.timeout:
                m=Target(); m.header.stamp=self.get_clock().now().to_msg(); m.target_id=t.tid; m.target_class=t.cls; m.confidence=t.conf; m.pose.pose.position.x=t.x; m.pose.pose.position.y=t.y; m.detecting_drones=list(sorted(t.witnesses)); m.status=Target.LOST; m.detection_count=t.count; m.fused_covariance_xx=t.covx; m.fused_covariance_yy=t.covy; self.pub.publish(m); del self.tracks[t.tid]
def main(args=None):
    rclpy.init(args=args); n=Tracker(); rclpy.spin(n); n.destroy_node(); rclpy.shutdown()
