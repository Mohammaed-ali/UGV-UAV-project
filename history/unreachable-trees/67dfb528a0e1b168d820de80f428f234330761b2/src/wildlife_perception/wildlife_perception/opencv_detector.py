"""Optional OpenCV detector for the v0.2 camera path.

This is intentionally a lightweight dummy-target detector: it looks for a saturated
colored blob in an incoming image and publishes a Detection. It provides the real
camera/OpenCV plumbing without pretending YOLO is already integrated.
"""
import math
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from wildlife_interfaces.msg import Detection
from geometry_msgs.msg import Point

class OpenCVDetector(Node):
    def __init__(self):
        super().__init__('opencv_detector')
        self.declare_parameter('drone_id','uav01')
        self.declare_parameter('target_class','dummy_animal')
        self.declare_parameter('min_area',250.0)
        self.declare_parameter('camera_height_m',10.0)
        self.declare_parameter('hfov_deg',78.0)
        self.did=self.get_parameter('drone_id').value
        self.cls=self.get_parameter('target_class').value
        self.bridge=CvBridge(); self.seq=0
        self.pub=self.create_publisher(Detection,f'/drones/{self.did}/detections',10)
        self.sub=self.create_subscription(Image,f'/drones/{self.did}/camera/image_raw',self.image_cb,10)
        self.get_logger().info(f'OpenCV camera detector ready for {self.did}')
    def image_cb(self,msg):
        try: frame=self.bridge.imgmsg_to_cv2(msg,desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().warning(f'cv_bridge: {exc}'); return
        hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
        mask=cv2.inRange(hsv,(0,80,80),(35,255,255))
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if not contours:return
        c=max(contours,key=cv2.contourArea); area=cv2.contourArea(c)
        if area<float(self.get_parameter('min_area').value):return
        x,y,w,h=cv2.boundingRect(c); cx=x+w/2.0
        fov=math.radians(float(self.get_parameter('hfov_deg').value)); bearing=((cx/frame.shape[1])-0.5)*fov
        d=Detection(); d.header=msg.header; d.drone_id=self.did; d.detection_id=f'{self.did}_cv_{self.seq:06d}'; self.seq+=1
        d.target_class=self.cls; d.confidence=min(0.99,0.5+area/(frame.shape[0]*frame.shape[1]))
        # Camera-frame bearing is preserved as a simple local/world demo convention.
        d.position_world=Point(x=float(self.get_parameter('camera_height_m').value)*math.tan(bearing),y=0.0,z=0.0)
        d.covariance_xx=4.0; d.covariance_yy=4.0; d.distance_from_drone=float(self.get_parameter('camera_height_m').value)
        self.pub.publish(d)

def main():
    rclpy.init(); n=OpenCVDetector(); rclpy.spin(n); n.destroy_node(); rclpy.shutdown()
