from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(package="wildlife_vehicles", executable="ugv_node", name="ugv_manager",
             parameters=[{"deployment_mode":"SPLIT","waypoints":[0.0,0.0,20.0,0.0,20.0,20.0]}], output="screen"),
        Node(package="wildlife_vehicles", executable="deployment_node", name="deployment_manager",
             parameters=[{"deployment_mode":"SPLIT","inter_drone_delay":2.0}], output="screen"),
        Node(package="wildlife_simulation", executable="detection_mux", name="detection_mux", output="screen"),
        Node(package="wildlife_tracking", executable="tracker", name="target_tracker", output="screen"),
        Node(package="wildlife_targets", executable="target_manager", name="target_manager", output="screen"),
        Node(package="wildlife_swarm", executable="coordinator", name="swarm_coordinator", output="screen"),
        Node(package="wildlife_mission", executable="mission_manager", name="mission_manager", output="screen"),
        Node(package="wildlife_mission", executable="operator_interface", name="operator_interface", output="screen"),
    ] + [
        Node(package="wildlife_vehicles", executable="uav_node", name=f"uav{i:02d}_manager",
             parameters=[{"drone_id":f"uav{i:02d}"}], output="screen")
        for i in range(1,9)
    ] + [
        Node(package="wildlife_perception", executable="detector_sim", name=f"uav{i:02d}_perception",
             parameters=[{"drone_id":f"uav{i:02d}"}], output="screen")
        for i in range(1,9)
    ])
