"""PX4 mission graph; runtime counts above one require prior validation."""
import json
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def _nodes(context):
    count = int(LaunchConfiguration('vehicle_count').perform(context))
    if count not in (1, 2, 8):
        raise ValueError('vehicle_count must be 1, 2 or 8')
    validation = LaunchConfiguration('validation_file').perform(context)
    single_target = LaunchConfiguration('single_target').perform(context).lower() == 'true'
    backend = LaunchConfiguration('detector_backend').perform(context)
    if backend not in ('sim', 'opencv', 'none'):
        raise ValueError('detector_backend must be sim, opencv or none')
    if backend == 'opencv' and count != 1:
        raise ValueError('real camera backend is validated only for uav01')
    if count > 1:
        with open(validation) as stream:
            passed = json.load(stream)
        needed = ('one_uav',) if count == 2 else ('two_uav', 'eight_structural')
        for gate in needed:
            if passed.get(gate) != 'PASS':
                raise RuntimeError(f'{gate} acceptance must pass before this vehicle count')
    def params(package, filename):
        return os.path.join(get_package_share_directory(package), 'params', filename)
    vp = params('wildlife_vehicles', 'vehicles.yaml')
    pp = params('wildlife_perception', 'perception.yaml')
    tp = params('wildlife_targets', 'targets.yaml')
    mp = params('wildlife_mission', 'mission.yaml')
    px = os.path.join(get_package_share_directory('wildlife_simulation'), 'config', 'px4.yaml')
    ids = [f'uav{i:02d}' for i in range(1, count + 1)]
    mode = LaunchConfiguration('deployment_mode')
    nodes = [
        Node(package='wildlife_vehicles', executable='ugv_node', name='ugv_manager', parameters=[vp, {'deployment_mode': mode}], output='screen'),
        Node(package='wildlife_vehicles', executable='deployment_node', name='deployment_manager', parameters=[vp, {'deployment_mode': mode, 'active_drone_ids': ids, 'require_ready': True}], output='screen'),
        Node(package='wildlife_vehicles', executable='docking_node', name='docking_manager', parameters=[vp, {'expected_drones': count}], output='screen'),
        Node(package='wildlife_targets', executable='detection_mux', name='detection_mux', parameters=[tp], output='screen'),
        Node(package='wildlife_targets', executable='tracker', name='target_tracker', parameters=[tp], output='screen'),
        Node(package='wildlife_targets', executable='target_manager', name='target_manager', parameters=[tp], output='screen'),
        Node(package='wildlife_swarm', executable='coordinator', name='swarm_coordinator', parameters=[params('wildlife_swarm', 'swarm.yaml')], output='screen'),
        Node(package='wildlife_mission', executable='mission_manager', name='mission_manager', parameters=[mp, {'expected_drones': count}], output='screen'),
        Node(package='wildlife_mission', executable='operator_interface', name='operator_interface', parameters=[mp, {'input_enabled': False}], output='screen'),
        Node(package='wildlife_core', executable='visualization_node', name='wildlife_visualization', output='screen'),
        Node(package='rviz2', executable='rviz2', name='rviz2', arguments=['-d', os.path.join(get_package_share_directory('wildlife_bringup'), 'rviz', 'wildlife.rviz')], condition=IfCondition(LaunchConfiguration('show_rviz')), output='screen'),
    ]
    for index, did in enumerate(ids):
        nodes.append(Node(package='wildlife_simulation', executable='px4_uav_adapter', name=f'{did}_manager', parameters=[vp, px, {
                'sitl_enabled': ParameterValue(LaunchConfiguration('sitl_enabled'), value_type=bool),
                'drone_id': did, 'system_id': index + 1, 'px4_namespace': '/' + did,
                'slot_id': index // 2 + 1, 'is_upper_position': index % 2 == 0,
                'search_altitude': 10.0 + 1.5 * index,
                'search_timeout': ParameterValue(LaunchConfiguration('search_timeout'), value_type=float),
                'loiter_duration': ParameterValue(LaunchConfiguration('loiter_duration'), value_type=float),
                'map_origin_x': float((index % 4) * 12 - 18) if count == 8 else 0.0,
                'map_origin_y': float(-18 if index < 4 else 18) if count == 8 else -35.0 * index,
            }], output='screen'))
        if backend == 'sim':
            nodes.append(Node(package='wildlife_perception', executable='detector_sim', name=f'{did}_perception', parameters=[pp, {
                'drone_id': did,
                'detection_probability': ParameterValue(LaunchConfiguration('detection_probability'), value_type=float),
                **({'target_positions': [15.0, 12.0]} if single_target else {}),
            }], output='screen'))
        elif backend == 'opencv':
            nodes.append(Node(package='wildlife_perception', executable='opencv_px4_detector',
                              name=f'{did}_perception',
                              parameters=[params('wildlife_perception', 'opencv_px4.yaml'),
                                          {'drone_id': did}], output='screen'))
    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('sitl_enabled', default_value='false'),
        DeclareLaunchArgument('vehicle_count', default_value='1'),
        DeclareLaunchArgument('deployment_mode', default_value='SINGLE'),
        DeclareLaunchArgument('show_rviz', default_value='true'),
        DeclareLaunchArgument('search_timeout', default_value='90.0'),
        DeclareLaunchArgument('loiter_duration', default_value='20.0'),
        DeclareLaunchArgument('detection_probability', default_value='0.55'),
        DeclareLaunchArgument('detector_backend', default_value='sim'),
        DeclareLaunchArgument('single_target', default_value='false'),
        DeclareLaunchArgument('validation_file', default_value='/tmp/wildlife_px4_acceptance.json'),
        OpaqueFunction(function=_nodes),
    ])
