# Wildlife ROS 2 — v0.2

ROS 2 Jazzy + Ubuntu 24.04 academic multi-UAV/UGV simulation baseline.

## Demo flow

`UGV -> typed deployment -> UAV search -> dummy/OpenCV detection -> target tracking/fusion -> assignment -> standoff -> operator RETURN/HOLD -> return/docking`

The project is intentionally scoped to non-contact search, detection, tracking, standoff and return/docking behaviors.

## Build

```bash
source /opt/ros/jazzy/setup.bash
cd ~/wildlife_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## Logic-only demo

```bash
ros2 launch wildlife_bringup subject1_demo.launch.py
```

## Gazebo demo

Install the Gazebo/bridge packages described in `docs/DEPENDENCIES.md`, then:

```bash
ros2 launch wildlife_bringup subject2_demo.launch.py
```

The Gazebo UAVs in v0.2 are visual proxy vehicles. PX4 SITL is deliberately deferred to v0.3.

## Operator decision

```bash
ros2 service call /operator/decision wildlife_interfaces/srv/OperatorDecision \
"{target_id: tgt_001, assigned_drone_id: uav01, decision: 0, operator_notes: 'return'}"
```

`0 = RETURN`, `1 = CONTINUE_HOLD`.

See `ARCHITECTURE.md`, `docs/V0_2_SCOPE.md`, and `docs/DEPENDENCIES.md`.

## V0.2 final validation

For the logic-level demonstration:

```bash
source /opt/ros/jazzy/setup.bash
cd ~/wildlife_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 launch wildlife_bringup simulation.launch.py
```

For Gazebo + ROS 2 bridge + eight camera-equipped UAV proxies:

```bash
ros2 launch wildlife_bringup subject2_demo.launch.py
```

The V0.2 default perception path remains `detector_sim`; the OpenCV camera detector is an optional plumbing path for the next perception stage.


## Verified baseline

See `docs/AUDIT_V0_2.md` for the pre-change audit and `docs/VALIDATION_V0_2.md` for fixes, passing runtime checks and remaining scope limits. Restart the launch to reset the complete mission; MissionControl RESET explicitly rejects unsupported partial resets. HOLD keeps a later RETURN decision available.
