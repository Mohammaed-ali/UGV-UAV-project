"""ONE externally started PX4 SITL vehicle. Never includes eight-UAV deployment."""
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    def params(package, filename):
        return os.path.join(get_package_share_directory(package), 'params', filename)
    return LaunchDescription([
        DeclareLaunchArgument('sitl_enabled', default_value='false',
                              description='Explicitly enable the experimental SITL backend'),
        Node(package='wildlife_simulation', executable='px4_uav_adapter', name='uav01_manager',
             parameters=[params('wildlife_vehicles', 'vehicles.yaml'),
                         {'sitl_enabled': LaunchConfiguration('sitl_enabled')}], output='screen'),
        Node(package='wildlife_perception', executable='detector_sim', name='uav01_perception',
             parameters=[params('wildlife_perception', 'perception.yaml')], output='screen'),
        Node(package='wildlife_targets', executable='detection_mux', name='detection_mux',
             parameters=[params('wildlife_targets', 'targets.yaml')], output='screen'),
        Node(package='wildlife_targets', executable='tracker', name='target_tracker',
             parameters=[params('wildlife_targets', 'targets.yaml')], output='screen'),
        Node(package='wildlife_targets', executable='target_manager', name='target_manager',
             parameters=[params('wildlife_targets', 'targets.yaml')], output='screen'),
        Node(package='wildlife_swarm', executable='coordinator', name='swarm_coordinator',
             parameters=[params('wildlife_swarm', 'swarm.yaml')], output='screen'),
        Node(package='wildlife_mission', executable='mission_manager', name='mission_manager',
             parameters=[params('wildlife_mission', 'mission.yaml'), {'expected_drones': 1}], output='screen'),
        Node(package='wildlife_mission', executable='operator_interface', name='operator_interface',
             parameters=[params('wildlife_mission', 'mission.yaml')], output='screen'),
        Node(package='wildlife_core', executable='visualization_node', output='screen'),
    ])
