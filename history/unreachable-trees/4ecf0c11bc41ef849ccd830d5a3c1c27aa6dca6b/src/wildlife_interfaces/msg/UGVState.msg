std_msgs/Header header
uint8 state
uint8 IDLE=0
uint8 MOVING=1
uint8 ARRIVED=2
uint8 DEPLOYING=3
uint8 WAITING=4
uint8 MISSION_COMPLETE=5
geometry_msgs/PoseStamped pose
# Index of the last completed waypoint. The next navigation target is +1.
uint32 current_waypoint_index
uint32 drones_deployed
uint32 drones_docked
string deployment_mode
