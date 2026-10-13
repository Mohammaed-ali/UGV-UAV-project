# v0.2 dependency plan

## Integrated now
- ROS 2 Jazzy
- Gazebo Harmonic / `gz sim` (visual simulation layer)
- `ros_gz_sim` + `ros_gz_bridge` (Gazebo spawn/bridge)
- OpenCV + `cv_bridge` (optional camera detector executable)

## Deliberately deferred
- **PX4 SITL:** not hard-wired into v0.2. The UAV model is a simple Gazebo visual proxy so the ROS mission logic remains buildable without a PX4 checkout. v0.3 will replace the proxy with PX4 SITL vehicle instances and `px4_msgs`/offboard integration.
- **QGroundControl:** desktop ground-control application; no ROS package is required. Use it alongside PX4 SITL once PX4 is integrated.
- **micro-ROS Agent:** deferred until a microcontroller/embedded node is introduced.
- **Ultralytics YOLO:** deferred until the camera/image pipeline is validated. The intended contract is to keep publishing the existing `wildlife_interfaces/Detection` message, so the detector can be swapped without changing tracking/mission code.

## Ubuntu 24.04 setup

Core ROS/Gazebo packages should be installed through the ROS 2 Jazzy apt repository. Python OpenCV is optional for the camera detector:

```bash
sudo apt install ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-bridge ros-jazzy-cv-bridge python3-opencv
```

If you do not want camera processing yet, you can omit OpenCV/cv_bridge and run the `detector_sim` backend.

## PX4 integration boundary

The project deliberately uses a stable ROS-side interface:

`camera -> Detection -> tracking/fusion -> Target -> assignment -> standoff -> operator decision`

PX4 should own vehicle flight/autopilot behavior. The mission layer should send high-level flight intent, not duplicate PX4's inner-loop controller.
