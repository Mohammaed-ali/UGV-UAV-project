# Wildlife ROS 2 architecture — V0.4 development

This continues the confirmed V0.3 nine-package workspace. Typed messages,
services and actions remain unchanged. PX4 owns flight stabilization and native
failsafes; ROS owns mission intent, observation, assignment, standoff requests
and operator decisions. There is one PX4 adapter per real vehicle and no
second mission FSM.

```text
wildlife_interfaces   frozen Detection, Target, DroneState and control contracts
wildlife_core         shared math and RViz markers
wildlife_vehicles     UGV logic, readiness-aware deployment, logical UAV, docking
wildlife_perception   deterministic detector_sim; legacy logical OpenCV;
                      real PX4-camera OpenCV and ray/ground geometry
wildlife_targets      detection mux, tracking/fusion, persistent target registry
wildlife_swarm        target-to-available-UAV assignment
wildlife_mission      mission FSM and typed operator service
wildlife_simulation   Gazebo worlds, UGV adapter, existing PX4 UAV adapter
wildlife_bringup      launch profiles, parameters and RViz configuration
```

## Observation and mission flow

```text
Gazebo camera -> ros_gz_bridge -> sensor_msgs/Image + CameraInfo
PX4 attitude --------------------\
PX4 local position -> PX4 adapter -> DroneState(map pose)
                                   \
                                    OpenCV + camera geometry -> Detection(map)
detector_sim -------------------------------------------> Detection(map)
Detection -> detection_mux -> tracker -> Target manager -> coordinator
          -> assigned Target -> existing UAV behavior -> PX4 adapter
          -> namespaced PX4 command/setpoint -> PX4 -> measured telemetry
                                  |
                            OperatorAlert -> /operator/decision
```

The launch parameter `detector_backend` selects `sim`, `opencv` or `none`.
The deterministic SIM backend remains the default and needs no camera. The
real OpenCV profile is currently validated for uav01 only. The older V0.2
OpenCV node remains available for its logical camera demo; it does not provide
the V0.4 map projection. YOLO is optional and has not been added.

## PX4 fleet identity

Each PX4 process uses instance `i-1`, system ID and XRCE-DDS key `i`, DDS
namespace `/uavNN`, and one correspondingly named ROS adapter. For the tested
two-flight profile, uav01 spawns at (0, 0) m and uav02 at (0, -35) m. The
adapter adds this origin to local NED-to-ENU position and subtracts it for
Offboard setpoints. PX4 command targets use the matching system ID; ACKs are
accepted only from the adapter's external source on that vehicle's namespaced
topic. Gazebo entities are `x500_0` and `x500_1`. Eight-vehicle structural
testing uses 12 m spaced columns in two rows; eight-vehicle flight has not
been validated.

The real camera profile mounts the pinned `x500_mono_cam_down` on uav01 and
bridges its observed Gazebo image topic to
`/drones/uav01/camera/image_raw`. Pixel rays use CameraInfo, PX4 FRD/NED
attitude and measured map position to intersect a flat ground plane. Detailed
frame definitions and timing limits are in `docs/V0_4_CAMERA_GEOMETRY.md`.

## Deployment and completion

The UGV requests SINGLE or SPLIT deployment. The deployment node filters
active IDs, waits for recent per-vehicle readiness, and sends typed LAUNCH.
The PX4 adapter queues LAUNCH until ready; flight mode, arming, position and
landing are measured from PX4. RETURN delegates RTL to PX4. DOCKED means
landed/disarmed at home in this simulation; it does not claim physical tray
contact. The mission manager reaches COMPLETE only when the configured active
vehicle count has docked.

The verified V0.4 gates are listed in `docs/V0_4_VALIDATION.md`. QGC
multi-vehicle UI inspection, two-camera fusion, moving visual targets and
eight-vehicle flight remain separate validation tasks.
