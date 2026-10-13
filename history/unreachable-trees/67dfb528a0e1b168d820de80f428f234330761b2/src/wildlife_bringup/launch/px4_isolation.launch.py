"""Two real PX4 adapters without automatic deployment or mission commands."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    vehicles = os.path.join(get_package_share_directory('wildlife_vehicles'), 'params', 'vehicles.yaml')
    px4 = os.path.join(get_package_share_directory('wildlife_simulation'), 'config', 'px4.yaml')
    return LaunchDescription([
        Node(package='wildlife_simulation', executable='px4_uav_adapter',
             name=f'uav{index + 1:02d}_manager', output='screen',
             parameters=[vehicles, px4, {
                 'sitl_enabled': True,
                 'drone_id': f'uav{index + 1:02d}',
                 'system_id': index + 1,
                 'px4_namespace': f'/uav{index + 1:02d}',
                 'slot_id': 1,
                 'is_upper_position': index == 0,
                 'search_altitude': 10.0 + 1.5 * index,
                 'search_timeout': 240.0,
                 'map_origin_x': 0.0,
                 'map_origin_y': -35.0 * index,
             }]) for index in range(2)
    ])
