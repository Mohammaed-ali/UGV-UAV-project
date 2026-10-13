# V0.2 repository audit — 2026-10-03

Authoritative source: wildlife_ws in V0.2 final. Historical comparison: wildlife_ws_v0_1_council. No usable Git repository or AGENTS.md found. This audit precedes source edits.

## Package and ROS graph

| Package / node | Inputs | Outputs / services | Main parameters |
|---|---|---|---|
| wildlife_interfaces | — | 8 messages, 3 services, 2 actions | — |
| wildlife_vehicles / ugv_manager | /drones/state | /ugv/state, /ugv/deployment_request | waypoints, speed, deploy_at_waypoint_indices, deployment_mode |
| deployment_manager | /ugv/deployment_request | /deployment/commands, /deployment/status | inter_drone_delay |
| uav01_manager … uav08_manager | /deployment/commands, /mission/drone_commands, /targets/assigned, /targets/operator_decision | /drones/state, /operator/alerts | ID, slot, altitude, speed, standoff, timeout, home |
| docking_manager | /drones/state | /docking/status | report_period |
| wildlife_perception / uav01_perception … uav08_perception | /drones/state | /drones/<id>/detections | range, probability, noise, target positions/classes |
| opencv_detector (optional, not launched) | /drones/<id>/camera/image_raw | /drones/<id>/detections | min_area, hfov_deg, camera_height_m |
| wildlife_targets / detection_mux | eight detection topics | /detections/all | queue_depth |
| target_tracker | /detections/all | /targets/tracked | gate_radius, alpha, stale_timeout, minimum_confidence |
| target_manager | /targets/tracked, /targets/assigned, /targets/operator_decision | /targets/registry, /targets/unassigned | report_period |
| wildlife_swarm / swarm_coordinator | /targets/unassigned, /drones/state | /targets/assigned | max_assignment_distance, cost weights |
| wildlife_mission / mission_manager | UGV, drone, assignment, alert, decision topics | /mission/status, /mission/drone_commands; /mission/control service | expected_drones, status_period |
| operator_interface | /operator/alerts | /targets/operator_decision; /operator/decision service | input_enabled |
| wildlife_core / visualization | drone, UGV, registry topics | /visualization/markers | standoff_radius, marker scales |
| wildlife_simulation / ugv_gazebo_adapter | /ugv/state | /ugv/cmd_vel | waypoints, speed, yaw_gain |
| scenario_manager (not launched) | — | /simulation/scenario | scenario |
| wildlife_bringup | launch composition | logic / Gazebo / RViz profiles | deployment_mode, show_rviz |

NavigateWaypoints and SearchArea are interface definitions only: no action servers exist. DeployDrone likewise has no server. String messages are diagnostic status/scenario only, not operational protocols. Eight DroneState publishers intentionally share an aggregate topic distinguished by drone_id.

## Historical comparison

The actual V0.1 council tree already has nine packages with tracking merged into wildlife_targets. V0.2 retains the vehicle/mission/target/swarm implementations and typed contracts; only a UGVState comment changes the interface source. V0.2 adds Gazebo models/world/bridge/adapter, OpenCV, documentation, package installation changes and launch wiring. No reason to restore wildlife_tracking. Older deployment launch aliases retain inconsistent YAML/default behavior.

## Council findings and additional correctness defects

- PASS source inspection: simulation manifest already has rclpy, launch and launch_ros, with no ros2launch key. Missing direct wildlife_interfaces/std_msgs dependencies remain.
- PASS source inspection: simulation.launch.py loads vehicle/perception YAML; exact node names match eight parameter blocks. It omits docking_manager and RViz, although subject1 includes it. Legacy split_simulation omits YAML entirely.
- PASS contract: UGV internal idx is next target; published max(0, idx-1) is last completed. Initial position is waypoint 0, reached on first tick. Adapter +1 is correct.
- FAIL: adapter controls absolute bearing from logical position, ignores Gazebo odometry and heading.
- FAIL: SPLIT still uses deploy_at_waypoint_indices=[0], so only four drones deploy.
- FAIL: bridge path interpolates a PathJoinSubstitution into an f-string instead of resolving it.
- WARN: UGV wheel links have no collisions; chassis bottom is below wheel contact surface. DiffDrive joint motion alone cannot establish useful wheel traction.
- PASS source presence: eight static camera-equipped proxies, eight matching Image bridge entries. FAIL: world lacks explicit rendering sensor system. No runtime camera claim is justified.
- WARN: OpenCV uses an approximate bearing as world coordinates without camera pose; this is plumbing only, not validated geolocation. Keep isolated from the default demo.
- FAIL: detector_sim uses unseeded global randomness and wall-time IDs; reproducibility is not guaranteed.
- FAIL: CONTINUE_HOLD removes the pending operator alert, while UAV alert suppression prevents a later RETURN decision.
- FAIL: unknown operator decisions are treated as HOLD.
- FAIL: coordinator can assign one target to multiple UAVs before registry feedback; no per-target reservation.
- FAIL: repeated deployment request checks a string against tuple queue elements; duplicates enter queue (sent guard prevents repeat launch).
- WARN: mission completion only handles ABORT; resolving depends on stale callback order. PAUSE/ABORT can be overwritten by an alert, and pending launches are not inhibited by mission override.
- WARN: RESUME loses the pre-pause UAV phase; returning or taking off can resume searching incorrectly.
- RViz MarkerArray exists in map; config topic is a scalar, whereas Jazzy uses a topic property map. Runtime subscription and rendering require validation.
- No committed tests. Python 3.13 cache files are bundled; local ROS uses system Python 3.12.

## Environment and gates

Ubuntu 24.04, ROS Jazzy, colcon, RViz and cv_bridge present. Gazebo executable, ros_gz_sim/bridge, PX4, px4_msgs, Micro XRCE-DDS Agent and QGroundControl not found. rosdep check fails because rosdep is not initialized. Missing Gazebo packages installation attempted with approved sudo command; sudo requires a password.

V0.2 must not be called a verified freeze until build, regression tests, logic demo, RViz and Gazebo camera/UGV checks pass. V0.3 implementation is gated by that baseline, per the handoff. No eight-aircraft PX4 work is authorized before the single-aircraft milestone.

## Recommended scope

1. Blockers: install/validate simulation dependencies; repair bridge, sensor activation and UGV controller/model.
2. Correctness: consistent launch YAML/SPLIT, repeatable detector, operator HOLD/RETURN, pause/abort handling, assignment reservation and meaningful regression tests.
3. After verified freeze: isolated one-UAV PX4 adapter with sole telemetry authority, ENU/NED conversion, telemetry freshness, command acknowledgement and takeoff/hold/return checks. Keep existing Detection/Target contracts and PX4 inner-loop control.
