# Reproducible V0.4 demonstrations

Use the primary workspace `/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3`.
Run one PX4/Gazebo validation at a time: all helpers use one local XRCE agent
on UDP 8888. The helpers own and clean up their child process groups.
Keep QGroundControl running through `scripts/start_qgc.sh`; its GCS link is
required by the pinned PX4 preflight configuration. Do not rebuild while a
flight is running. ROS logs are redirected to `/tmp`.

## Prepare

```bash
scripts/check_prereqs.sh
ROS_LOG_DIR=/tmp/wildlife-v04-build scripts/build_ros.sh
source scripts/environment.sh
ROS_LOG_DIR=/tmp/wildlife-v04-tests colcon test --base-paths src --executor sequential
colcon test-result --verbose
scripts/start_qgc.sh
```

Local ROS discovery and Gazebo transport use loopback. Dependencies and
camera profiles are pinned; do not upgrade them for this demonstration.

## Automated gates

```bash
scripts/validate_logic.sh
scripts/validate_px4_single.sh
scripts/validate_px4_two.sh
scripts/validate_px4_two_mission.sh
scripts/validate_px4_fleet.sh 4
scripts/validate_px4_fleet.sh 8
scripts/validate_px4_camera.sh
scripts/validate_px4_real_camera_mission.sh
scripts/validate_px4_two_camera_fusion.sh
scripts/validate_px4_moving_target.sh
scripts/validate_px4_health.sh low_battery
scripts/validate_px4_health.sh vehicle_unavailable
scripts/validate_px4_health.sh two_targets
scripts/validate_px4_fleet_flight.sh
scripts/validate_px4_two_camera_mission.sh
```

Health scenarios are in `src/wildlife_simulation/config/health_scenarios.yaml`.
The battery gate changes PX4's simulator parameters only, reads genuine PX4
BatteryStatus, and restores the original values. The fault gate deliberately
changes PX4 to loiter, verifies that ROS yields, then explicitly requests
RETURN. No reassignment occurs merely because a vehicle pauses or disappears.
The moving target follows the YAML loop in `moving_target.yaml`; target
velocity is descriptive. The UAV retains a bounded observation point.

The fleet gate uses eight real PX4 vehicles, SPLIT deployment at logical UGV
waypoints 0 and 1, separate search cells, measured separation and all-eight
landing/disarm/COMPLETE. Its YAML profile keeps local position's existing two-second
receipt-age limit; slower status/landing streams allow three seconds because
PX4 LandDetected publishes at one Hz of simulation time. It remains a basic
mission-planning demonstration, not general collision avoidance.

## Examiner demonstration with real images

```bash
HEADLESS= SHOW_RVIZ=true OPERATOR_HOLD_S=15 \
  CAMERA_EVIDENCE_FILE=docs/validation/px4_examiner_demo.json \
  scripts/validate_px4_real_camera_mission.sh
```

This uses the automated simulated operator for reproducible HOLD then RETURN.
Watch the logical UGV and its Gazebo display proxy, readiness-aware launch,
actual camera observations, target assignment, standoff, RViz labels and
assignment line, operator hold, PX4 RTL, landing/disarm and COMPLETE.
QGC shows native vehicle identity, flight mode, arming, position and battery.
ROS remains the mission authority.

For a human-operated session, start `scripts/start_px4_camera.sh detector_backend:=opencv show_rviz:=true`
and inspect `/operator/alerts`. Call the existing `/operator/decision` service
with the observed target and UAV IDs. Decision 1 is CONTINUE_HOLD; 0 is RETURN.
For example, only after the alert identifies `tgt_001` and `uav01`:

```bash
ros2 service call /operator/decision wildlife_interfaces/srv/OperatorDecision \
  '{target_id: tgt_001, assigned_drone_id: uav01, decision: 1}'
```

Camera scripts use ROS domain 86 by default. Source the environment and set
`ROS_DOMAIN_ID=86` in the operator terminal. Use RETURN later to finish.
DOCKED does not claim physical tray contact. The Gazebo UGV proxy has no
collision geometry and does not feed physical arrival into deployment.

The separate logic-only demo remains `subject1_demo.launch.py` and does not
require PX4 or camera processing. The original logical Gazebo camera profile
is also preserved. No YOLO model or dependency is needed.
