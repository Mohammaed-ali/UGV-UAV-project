from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    sim=LaunchConfiguration('use_gazebo')
    world=PathJoinSubstitution([FindPackageShare('wildlife_simulation'),'worlds','wildlife_field.sdf'])
    bridge=PathJoinSubstitution([FindPackageShare('wildlife_simulation'),'config','bridge.yaml'])
    ugv=PathJoinSubstitution([FindPackageShare('wildlife_simulation'),'models','ugv','model.sdf'])
    uav_models={i: PathJoinSubstitution([FindPackageShare('wildlife_simulation'),'models',f'uav{i:02d}','model.sdf']) for i in range(1,9)}
    actions=[DeclareLaunchArgument('use_gazebo',default_value='true')]
    actions.append(ExecuteProcess(cmd=['gz','sim','-r',world],output='screen',condition=IfCondition(sim)))
    actions.append(Node(package='wildlife_simulation',executable='ugv_gazebo_adapter',name='ugv_gazebo_adapter',output='screen'))
    actions.append(TimerAction(period=2.0,actions=[Node(package='ros_gz_bridge',executable='parameter_bridge',parameters=[{'config_file': bridge}],output='screen')]))
    actions.append(TimerAction(period=3.0,actions=[Node(package='ros_gz_sim',executable='create',arguments=['-name','ugv','-file',ugv,'-x','0','-y','0','-z','0.4'],output='screen')]))
    for i in range(1,9):
        x=((i-1)%4)*3.0+2.0; y=((i-1)//4)*4.0-2.0
        actions.append(TimerAction(period=4.0+i*0.15,actions=[Node(package='ros_gz_sim',executable='create',arguments=['-name',f'uav{i:02d}','-file',uav_models[i],'-x',str(x),'-y',str(y),'-z','0.4'],output='screen')]))
    return LaunchDescription(actions)
