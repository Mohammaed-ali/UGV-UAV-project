import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from visualization_msgs.msg import Marker, MarkerArray
from wildlife_interfaces.msg import DroneState, UGVState, Target

class VisualizationNode(Node):
    """Publish standard RViz MarkerArray from custom project state topics."""
    def __init__(self):
        super().__init__('wildlife_visualization')
        self.declare_parameter('standoff_radius', 12.0)
        self.declare_parameter('drone_marker_scale', 0.8)
        self.declare_parameter('target_marker_scale', 1.0)
        self.standoff_radius=float(self.get_parameter('standoff_radius').value)
        self.drone_scale=float(self.get_parameter('drone_marker_scale').value)
        self.target_scale=float(self.get_parameter('target_marker_scale').value)
        self.drones={}; self.targets={}; self.ugv=None
        self.pub=self.create_publisher(MarkerArray,'/visualization/markers',10)
        self.create_subscription(DroneState,'/drones/state',self.drone_cb,50)
        self.create_subscription(Target,'/targets/registry',self.target_cb,20)
        self.create_subscription(UGVState,'/ugv/state',self.ugv_cb,20)
        self.create_timer(0.2,self.publish_markers)
    def drone_cb(self,m): self.drones[m.drone_id]=m
    def target_cb(self,m): self.targets[m.target_id]=m
    def ugv_cb(self,m): self.ugv=m
    def marker(self, mid, ns, mtype, x,y,z, sx,sy,sz):
        m=Marker(); m.header.frame_id='map'; m.header.stamp=self.get_clock().now().to_msg()
        m.ns=ns; m.id=mid; m.type=mtype; m.action=Marker.ADD
        m.pose.position.x=x; m.pose.position.y=y; m.pose.position.z=z
        m.pose.orientation.w=1.0; m.scale.x=sx; m.scale.y=sy; m.scale.z=sz
        m.color.a=0.85
        return m
    def publish_markers(self):
        arr=MarkerArray(); idx=0
        for did,d in sorted(self.drones.items()):
            p=d.pose.pose.position
            m=self.marker(idx,'drones',Marker.CUBE,p.x,p.y,p.z,self.drone_scale,self.drone_scale,self.drone_scale)
            arr.markers.append(m); idx+=1
            t=Marker(); t.header=m.header; t.ns='drone_labels'; t.id=idx; t.type=Marker.TEXT_VIEW_FACING; t.action=Marker.ADD
            t.pose.position.x=p.x; t.pose.position.y=p.y; t.pose.position.z=p.z+1.0; t.scale.z=0.6; t.color.a=1.0; t.text=did; arr.markers.append(t); idx+=1
        for tid,t in sorted(self.targets.items()):
            p=t.pose.pose.position
            m=self.marker(idx,'targets',Marker.SPHERE,p.x,p.y,p.z+0.2,self.target_scale,self.target_scale,self.target_scale)
            arr.markers.append(m); idx+=1
            c=self.marker(idx,'standoff',Marker.CYLINDER,p.x,p.y,p.z+0.02,self.standoff_radius*2,self.standoff_radius*2,0.05)
            arr.markers.append(c); idx+=1
        if self.ugv:
            p=self.ugv.pose.pose.position
            arr.markers.append(self.marker(idx,'ugv',Marker.CUBE,p.x,p.y,p.z+0.5,2.0,1.4,1.0))
        self.pub.publish(arr)

def main(args=None):
    rclpy.init(args=args); n=VisualizationNode(); rclpy.spin(n); n.destroy_node(); rclpy.shutdown()
