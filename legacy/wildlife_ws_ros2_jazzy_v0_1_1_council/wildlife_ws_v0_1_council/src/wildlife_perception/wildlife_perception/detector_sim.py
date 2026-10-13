import math, random, time
import rclpy
from rclpy.node import Node
from wildlife_interfaces.msg import Detection, DroneState
class DetectorSim(Node):
    def __init__(self):
        super().__init__('perception_detector')
        for k,v in {'drone_id':'uav01','detection_range':18.0,'detection_probability':0.55,'confidence_noise_sigma':0.03,'position_noise_sigma':0.25,'confidence_threshold':0.50,'publish_period':1.0,'target_positions':[15.,12.,25.,8.],'target_classes':['dummy_animal','dummy_animal']}.items(): self.declare_parameter(k,v)
        g=lambda k:self.get_parameter(k).value; self.id=str(g('drone_id')); self.range=float(g('detection_range')); self.prob=float(g('detection_probability')); self.csig=float(g('confidence_noise_sigma')); self.psig=float(g('position_noise_sigma')); self.thr=float(g('confidence_threshold')); self.x=self.y=self.z=0.; self.state=DroneState.STORED
        flat=list(g('target_positions')); classes=list(g('target_classes')); self.targets=[(f'dummy_{i+1:03d}',classes[i] if i<len(classes) else 'dummy_animal',float(x),float(y)) for i,(x,y) in enumerate(zip(flat[::2],flat[1::2]))]
        self.pub=self.create_publisher(Detection,f'/drones/{self.id}/detections',20); self.create_subscription(DroneState,'/drones/state',self.state_cb,50); self.create_timer(float(g('publish_period')),self.tick)
    def state_cb(self,m):
        if m.drone_id==self.id: self.x=m.pose.pose.position.x; self.y=m.pose.pose.position.y; self.z=m.pose.pose.position.z; self.state=m.state
    def tick(self):
        if self.state not in (DroneState.SEARCHING,DroneState.STANDOFF): return
        for tid,cls,tx,ty in self.targets:
            d=math.hypot(tx-self.x,ty-self.y)
            if d>self.range or random.random()>self.prob: continue
            conf=max(0.,min(1.,1.-d/self.range+random.gauss(0,self.csig)))
            if conf<self.thr: continue
            m=Detection(); m.header.stamp=self.get_clock().now().to_msg(); m.drone_id=self.id; m.detection_id=f'{self.id}_{tid}_{time.time_ns()}'; m.target_class=cls; m.confidence=conf; m.position_world.x=tx+random.gauss(0,self.psig); m.position_world.y=ty+random.gauss(0,self.psig); m.position_world.z=0.; m.covariance_xx=self.psig**2; m.covariance_yy=self.psig**2; m.distance_from_drone=d; self.pub.publish(m)
def main(args=None):
    rclpy.init(args=args); n=DetectorSim(); rclpy.spin(n); n.destroy_node(); rclpy.shutdown()
