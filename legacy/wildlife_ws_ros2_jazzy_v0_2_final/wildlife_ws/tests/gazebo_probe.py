"""Runtime sensor/odometry/visualization verification in an isolated ROS domain."""
import json
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from nav_msgs.msg import Odometry
from wildlife_interfaces.msg import UGVState, DroneState
from visualization_msgs.msg import MarkerArray
rclpy.init()
n=Node('gazebo_validation_probe')
images={}; odom=[]; markers=[]
for i in range(1,9):
    did=f'uav{i:02d}'
    n.create_subscription(Image, f'/drones/{did}/camera/image_raw', lambda m,did=did: images.update({did:[m.width,m.height,len(m.data)]}), qos_profile_sensor_data)
n.create_subscription(Odometry, '/ugv/odom', lambda m: odom.append((m.pose.pose.position.x,m.pose.pose.position.y)), qos_profile_sensor_data)
n.create_subscription(MarkerArray, '/visualization/markers', lambda m: markers.append(len(m.markers)),10)
p=n.create_publisher(UGVState,'/ugv/state',10)
d=n.create_publisher(DroneState,'/drones/state',10)
end=time.monotonic()+40
while time.monotonic()<end:
    m=UGVState(state=UGVState.MOVING,current_waypoint_index=0)
    p.publish(m);d.publish(DroneState(drone_id='uav01',state=DroneState.STORED))
    rclpy.spin_once(n,timeout_sec=.1)
rviz_subscribers=[e.node_name for e in n.get_subscriptions_info_by_topic('/visualization/markers')]
result={'images':images,'odom_count':len(odom),'first_odom':odom[0] if odom else None,'last_odom':odom[-1] if odom else None,'markers':len(markers),'marker_subscribers':rviz_subscribers}
print(json.dumps(result,indent=2),flush=True)
n.destroy_node();rclpy.shutdown()
assert len(images)==8 and len(odom)>10 and markers and any(name in ('rviz', 'rviz2') for name in rviz_subscribers),result
assert abs(odom[-1][0]-odom[0][0])>1.,result
