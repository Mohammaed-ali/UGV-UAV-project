import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    vh=get_package_share_directory('wildlife_vehicles'); ph=get_package_share_directory('wildlife_perception'); th=get_package_share_directory('wildlife_targets'); sh=get_package_share_directory('wildlife_swarm'); mh=get_package_share_directory('wildlife_mission'); ch=get_package_share_directory('wildlife_core'); bh=get_package_share_directory('wildlife_bringup')
    vp=os.path.join(vh,'params','vehicles.yaml'); pp=os.path.join(ph,'params','perception.yaml'); tp=os.path.join(th,'params','targets.yaml'); sp=os.path.join(sh,'params','swarm.yaml'); mp=os.path.join(mh,'params','mission.yaml'); rv=os.path.join(bh,'rviz','wildlife.rviz')
    mode=LaunchConfiguration('deployment_mode'); show_rviz=LaunchConfiguration('show_rviz')
    nodes=[
      Node(package='tf2_ros',executable='static_transform_publisher',name='wildlife_map_frame',arguments=['--frame-id','wildlife_world','--child-frame-id','map'],output='screen'),
      Node(package='wildlife_vehicles',executable='ugv_node',name='ugv_manager',parameters=[vp,{'deployment_mode':mode}],output='screen'),
      Node(package='wildlife_vehicles',executable='deployment_node',name='deployment_manager',parameters=[vp,{'deployment_mode':mode}],output='screen'),
      Node(package='wildlife_vehicles',executable='docking_node',name='docking_manager',parameters=[vp],output='screen'),
      Node(package='wildlife_targets',executable='detection_mux',name='detection_mux',parameters=[tp],output='screen'),
      Node(package='wildlife_targets',executable='tracker',name='target_tracker',parameters=[tp],output='screen'),
      Node(package='wildlife_targets',executable='target_manager',name='target_manager',parameters=[tp],output='screen'),
      Node(package='wildlife_swarm',executable='coordinator',name='swarm_coordinator',parameters=[sp],output='screen'),
      Node(package='wildlife_mission',executable='mission_manager',name='mission_manager',parameters=[mp],output='screen'),
      Node(package='wildlife_mission',executable='operator_interface',name='operator_interface',parameters=[mp],output='screen'),
      Node(package='wildlife_core',executable='visualization_node',name='wildlife_visualization',parameters=[{'standoff_radius':12.0}],output='screen'),
    ]
    tray=[(1,1,True),(1,2,False),(2,3,True),(2,4,False),(3,5,True),(3,6,False),(4,7,True),(4,8,False)]
    for slot,num,upper in tray:
      did=f'uav{num:02d}'
      nodes.append(Node(package='wildlife_vehicles',executable='uav_node',name=f'{did}_manager',parameters=[vp,{'drone_id':did,'slot_id':slot,'is_upper_position':upper}],output='screen'))
      nodes.append(Node(package='wildlife_perception',executable='detector_sim',name=f'{did}_perception',parameters=[pp,{'drone_id':did}],output='screen'))
    nodes.append(Node(package='rviz2',executable='rviz2',name='rviz2',arguments=['-d',rv],condition=__import__('launch.conditions',fromlist=['IfCondition']).IfCondition(show_rviz),output='screen'))
    return LaunchDescription([DeclareLaunchArgument('deployment_mode',default_value='SINGLE'),DeclareLaunchArgument('show_rviz',default_value='true')]+nodes)
