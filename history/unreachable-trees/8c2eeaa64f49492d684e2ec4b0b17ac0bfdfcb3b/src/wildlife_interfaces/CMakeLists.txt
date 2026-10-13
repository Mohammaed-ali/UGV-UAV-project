cmake_minimum_required(VERSION 3.8)
project(wildlife_interfaces)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/DroneState.msg"
  "msg/UGVState.msg"
  "msg/Detection.msg"
  "msg/Target.msg"
  "msg/DroneCommand.msg"
  "msg/TraySlot.msg"
  "msg/OperatorAlert.msg"
  "msg/DeploymentRequest.msg"
  "srv/OperatorDecision.srv"
  "srv/DeployDrone.srv"
  "srv/MissionControl.srv"
  "action/NavigateWaypoints.action"
  "action/SearchArea.action"
  DEPENDENCIES std_msgs geometry_msgs
)
ament_package()
