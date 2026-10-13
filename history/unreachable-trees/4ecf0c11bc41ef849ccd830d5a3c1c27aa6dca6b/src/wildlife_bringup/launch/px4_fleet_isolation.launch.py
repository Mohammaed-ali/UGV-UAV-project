"""Four/eight PX4 adapters for stationary structural scale validation."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def fleet_origin(index):
    return float((index % 4) * 12 - 18), float(-18 if index < 4 else 18)


def nodes(context):
    count = int(LaunchConfiguration('vehicle_count').perform(context))
    if count not in (4, 8):
        raise ValueError('fleet isolation requires 4 or 8 vehicles')
    vehicles = os.path.join(get_package_share_directory('wildlife_vehicles'), 'params', 'vehicles.yaml')
    px4 = os.path.join(get_package_share_directory('wildlife_simulation'), 'config', 'px4.yaml')
    result = []
    for index in range(count):
        did = f'uav{index + 1:02d}'
        x, y = fleet_origin(index)
        result.append(Node(package='wildlife_simulation', executable='px4_uav_adapter',
                           name=f'{did}_manager', output='screen',
                           parameters=[vehicles, px4, {
                               'sitl_enabled': True, 'drone_id': did,
                               'system_id': index + 1, 'px4_namespace': '/' + did,
                               'slot_id': index // 2 + 1,
                               'is_upper_position': index % 2 == 0,
                               'search_altitude': 10.0 + 1.5 * index,
                               'map_origin_x': x, 'map_origin_y': y,
                           }]))
    return result


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('vehicle_count', default_value='4'),
        OpaqueFunction(function=nodes),
    ])
