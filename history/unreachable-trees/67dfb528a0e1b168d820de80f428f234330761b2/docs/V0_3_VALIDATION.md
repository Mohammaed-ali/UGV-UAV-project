# V0.3 single-UAV milestone — 2026-10-04

| Check | Result | Evidence |
|---|---|---|
| ROS build | PASS, 9 packages | validation/v03_build.log |
| PX4 v1.17 SITL build | PASS, 1139 build steps | pinned checkout and executable; original build log /tmp/wildlife-v03-px4-build.log |
| XRCE agent build | PASS | shared agent-build; original log /tmp/wildlife-v03-agent-build.log |
| Behavioral tests | PASS, 32 actual tests; colcon summary 34 includes two wrappers | validation/v03_tests.log |
| Frozen message/service/action definitions | PASS, no differences from v0.2.0-verified | Git diff |
| PX4/px4_msgs definitions | PASS, all 8 used message definitions match after comments/whitespace normalization | pinned sources |
| Logic demo in V0.3 | PASS, 8/8 docked, two HOLD/RETURN decisions, 772 marker messages | validation/v03_logic.json |
| First PX4 target mission in upstream default world | PASS | validation/px4_first_mission.json and .log |
| PX4 no-target mission in wildlife world | PASS, 87.5 seconds | validation/px4_no_target.json |
| PX4 target mission in wildlife world | PASS, 91.1 seconds | validation/px4_target.json |
| QGC telemetry/link | PASS: PX4 GCS connected, vehicle parameter cache downloaded; preflight/arm allowed | both acceptance JSON flight.gcs_connected; QGC isolated cache |
| RViz | PASS: renderer started, live measured state/marker graph, 404/421 marker messages | no_target_ros.log, target_ros.log and JSON |
| Source migration/history | PASS, 110 tracked source files copied with SHA256 checks and .git preserved | original V0.3 commit 72c1c70 and V0.2 tag |
| Two/eight PX4 UAVs | NOT TESTED, launch composition/config only | launch/px4_single.launch.py |
| Optional camera/YOLO | NOT VALIDATED for PX4; no YOLO added | existing OpenCV plumbing preserved |

Both final PX4 probes observed STORED, TAKEOFF, SEARCHING, RETURNING and DOCKED; the target probe also observed STANDOFF and AWAITING_OPERATOR and exercised HOLD then RETURN. The no-target probe observed LOITERING after timeout. Both saw readiness true, Offboard, arming, measured landing/disarm and COMPLETE. Both observed exactly one DroneState publisher. The target probe observed 4 Detection messages and one Target assignment. HOLD was retained for three seconds before RETURN.

## Integration issues found and fixed

- The first run remained STORED without QGC. PX4's GCS preflight requirement was respected; connecting QGC resolved readiness without weakening arming checks.
- The new world initially was omitted from setup.py installation. Added it and a startup file-presence check.
- The custom world needed an explicit AirPressure system for PX4's barometer. Added required IMU/NavSat/Magnetometer/AirPressure systems and spherical coordinates. Preflight then passed.
- Readiness filters active deployment IDs and expired readiness; the adapter queues unready LAUNCH and honors early mission overrides.
- Command ACKs for another external component cannot fault this adapter. Faulted RESUME stays inhibited even with stale telemetry. Fresh faults publish PAUSED; explicit RETURN can delegate RTL and report measured docking without restarting Offboard.
- Runtime owns its child process groups and ends them on exit. No unrelated process is killed. Final target and no-target runners exited successfully.

## Limits and next milestone

The detector is synthetic and deterministic for the same input/ticks; DDS scheduling is not globally deterministic. The PX4 wildlife run has a logical UGV; the separately preserved V0.2 Gazebo UGV follower was validated before freeze but is not yet composed into this PX4 world. DOCKED means landed/disarmed at home, not physical tray contact. PX4 RTL uses its own altitude/speed configuration; the adapter's 60 m horizontal / 30 m vertical bounds constrain ROS Offboard position intent. ROS search_speed does not set PX4 velocity limits. The existing OpenCV detector's approximate projection is not calibrated map geolocation. Action/service interfaces without existing servers remain definitions only; a separate LAND service was not added because verified RETURN already delegates descent/landing to PX4.

Two/eight vehicle structure is unvalidated flight: namespace, system ID, spawn origin and initial altitude separation are configured but collision avoidance, performance and fleet startup need tests. The exact next milestone is two x500 instances with /uav01 and /uav02 DDS namespaces, IDs 1/2, independent telemetry/command isolation, per-spawn map conversion, readiness/deployment and measured return. Eight comes after two passes.

Some preserved ROS nodes still emit KeyboardInterrupt/ExternalShutdownException tracebacks during controlled shutdown. These occur after completed mission evidence; process groups terminate. They do not represent flight-test failures.
