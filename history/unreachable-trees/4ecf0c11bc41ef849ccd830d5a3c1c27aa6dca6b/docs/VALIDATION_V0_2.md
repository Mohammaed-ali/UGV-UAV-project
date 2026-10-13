# V0.2 freeze validation — 2026-10-03

## PASS

- Ubuntu 24.04 / ROS 2 Jazzy: nine packages build with colcon --symlink-install.
- rosdep check: all dependencies satisfied after installing ros_gz_sim/bridge and initializing rosdep.
- colcon test: nine packages finish; 15 behavioral pytest cases pass (colcon aggregates 16 including the CTest wrapper), zero errors/failures/skips.
- Python AST, nine package XMLs, eleven SDF assets and seven YAML files parse.
- Live logic demo: eight unique UAVs reach DOCKED. Two assigned UAVs accept HOLD then RETURN through /operator/decision. 772 MarkerArray messages observed, up to 21 markers. See validation/logic.json.
- Gazebo: nine models spawn. All eight cameras deliver 640x480 RGB images through ros_gz_bridge. 831 odometry samples observed; UGV travels from x=0.776 to x=19.523. See validation/gazebo.json.
- RViz opens with OpenGL 4.6 and subscribes to /visualization/markers using the saved configuration. Marker data reaches a separate subscriber. No screenshot-based aesthetic review claimed.
- Typed message/service/action definitions preserved byte-for-byte from the supplied V0.2 tree.

## Necessary changes

Launch aliases now share YAML-loaded complete composition including docking and optional RViz. SPLIT requests both deployment waypoints. Deployment request/command durability fixes late-subscriber startup loss. Bridge parameter substitution, rendering sensor system and UGV wheel contact geometry corrected. UGV heading uses measured odometry, wrapped yaw error and freshness stopping.

HOLD retains RETURN authority; invalid decisions are rejected. Pause restores the previous UAV phase and excludes paused time from timeouts. Mission overrides inhibit queued launches, alerts cannot erase pause/abort, late startup recovers phase from drone states, normal docking supports completion. RESET rejects unsupported cross-node reset rather than reporting false success; restart the launch for a new mission. Target reservation prevents duplicate assignments. Detector RNG is seeded per drone, with sequential detection IDs.

## Warnings / scope limits

- Seeded detection measurements are repeatable for identical input states/ticks. DDS scheduling and timestamps are not bit-for-bit deterministic; which UAV wins an assignment may vary.
- Gazebo UAVs remain static visual proxies. Logical UAV motion is deliberately separate until V0.3.
- UGV logical waypoint timing remains authoritative; adapter follows it using physical odometry, without feeding physical arrival back to deployment.
- OpenCV remains optional image plumbing, with approximate coordinates lacking calibrated world projection. Real images are verified; wildlife recognition/geolocation is not claimed.
- NavigateWaypoints/SearchArea and DeployDrone have definitions but no V0.2 servers.
- Shutdown of legacy nodes can log KeyboardInterrupt; this did not represent a runtime failure.
- Some earlier probes failed due to startup race, insufficient timeout or wrong standalone RViz node name. Final acceptance runner and results supersede them.

## Reproduce

From wildlife_ws:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
rosdep check --from-paths src --ignore-src
colcon test
colcon test-result --verbose
./tests/run_acceptance.sh
```

The acceptance script issues HOLD/RETURN only inside isolated simulation ROS domains 77/78 and stops its test launches afterward. Run with desktop rendering and local DDS/Gazebo networking available.
