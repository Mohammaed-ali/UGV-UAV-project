"""Two real PX4 cameras observing one visual dummy, without assignment flight."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    vehicles = os.path.join(get_package_share_directory('wildlife_vehicles'), 'params', 'vehicles.yaml')
    px4 = os.path.join(get_package_share_directory('wildlife_simulation'), 'config', 'px4.yaml')
    opencv = os.path.join(get_package_share_directory('wildlife_perception'), 'params', 'opencv_px4.yaml')
    targets = os.path.join(get_package_share_directory('wildlife_targets'), 'params', 'targets.yaml')
    nodes = [
        Node(package='wildlife_targets', executable='detection_mux',
             name='detection_mux', parameters=[targets], output='screen'),
        Node(package='wildlife_targets', executable='tracker',
             name='target_tracker', parameters=[targets, {'gate_radius': 4.0}], output='screen'),
        Node(package='wildlife_targets', executable='target_manager',
             name='target_manager', parameters=[targets], output='screen'),
    ]
    for index in range(2):
        did = f'uav{index + 1:02d}'
        nodes.extend([
            Node(package='wildlife_simulation', executable='px4_uav_adapter',
                 name=f'{did}_manager', output='screen',
                 parameters=[vehicles, px4, {
                     'sitl_enabled': True, 'drone_id': did,
                     'system_id': index + 1, 'px4_namespace': '/' + did,
                     'slot_id': 1, 'is_upper_position': index == 0,
                     'search_altitude': 10.0 if index == 0 else 15.0,
                     'search_timeout': 240.0,
                     'search_half_height': 0.0,
                     'map_origin_x': 0.0 if index == 0 else -10.0,
                     'map_origin_y': 0.0,
                 }]),
            Node(package='wildlife_perception', executable='opencv_px4_detector',
                 name=f'{did}_perception', output='screen',
                 parameters=[opencv, {'drone_id': did}]),
        ])
    return LaunchDescription(nodes)
