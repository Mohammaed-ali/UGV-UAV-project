from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    nodes=[]
    nodes.append(Node(package="wildlife_vehicles", executable="ugv_node", name="ugv_manager",
                       parameters=[{"deployment_mode":"SINGLE","waypoints":[0.0,0.0,20.0,0.0,20.0,20.0]}], output="screen"))
    nodes.append(Node(package="wildlife_vehicles", executable="deployment_node", name="deployment_manager",
                       parameters=[{"deployment_mode":"SINGLE","inter_drone_delay":2.0}], output="screen"))
    nodes.append(Node(package="wildlife_simulation", executable="detection_mux", name="detection_mux", output="screen"))
    nodes.append(Node(package="wildlife_tracking", executable="tracker", name="target_tracker", output="screen"))
    nodes.append(Node(package="wildlife_targets", executable="target_manager", name="target_manager", output="screen"))
    nodes.append(Node(package="wildlife_swarm", executable="coordinator", name="swarm_coordinator", output="screen"))
    nodes.append(Node(package="wildlife_mission", executable="mission_manager", name="mission_manager", output="screen"))
    nodes.append(Node(package="wildlife_mission", executable="operator_interface", name="operator_interface", output="screen"))
    for i in range(1,9):
        did=f"uav{i:02d}"
        nodes.append(Node(package="wildlife_vehicles", executable="uav_node", name=f"{did}_manager",
                           parameters=[{"drone_id":did}], output="screen"))
        nodes.append(Node(package="wildlife_perception", executable="detector_sim", name=f"{did}_perception",
                           parameters=[{"drone_id":did}], output="screen"))
    return LaunchDescription(nodes)
