# V0.4 validation record

Source baseline: `v0.3-final` (`8ca1e9d`). Development branch: `codex/v0.4-development`.
The existing nine package boundaries and typed interfaces are unchanged.

## Gate 1 — V0.3 regression: PASS

- `scripts/check_prereqs.sh`: pinned PX4, px4_msgs and agent paths present.
- `scripts/build_ros.sh`: nine packages built.
- `ROS_LOG_DIR=/tmp/wildlife-v04-ros-logs colcon test --base-paths src --executor sequential`: 34 test entries, zero errors/failures; 32 are behavioral tests.
- `HEADLESS=1 scripts/validate_px4_single.sh`: no-target timeout/RTL and target/standoff/HOLD/RETURN both passed in the existing PX4 wildlife world. Both were measured landed, disarmed and mission COMPLETE. Results: `validation/px4_no_target.json`, `validation/px4_target.json`.
- The first test attempt could not write ROS logs under the session's read-only home directory. Setting `ROS_LOG_DIR` to `/tmp` resolved this environment issue without source changes.

The pinned PX4 SITL and agent binaries were present and exercised by the live missions; neither upstream dependency was rebuilt for this gate.

## Gates 2–3 — two-PX4 namespace and command isolation: PASS

Run: `scripts/validate_px4_two.sh` with an active QGroundControl UDP link.
Result: `validation/px4_two_isolation.json`.

| Vehicle | PX4 instance | MAV system ID / DDS key | DDS namespace | Gazebo entity | spawn / ROS map origin |
|---|---:|---:|---|---|---|
| uav01 | 0 | 1 | /uav01 | x500_0 | (0, 0) m |
| uav02 | 1 | 2 | /uav02 | x500_1 | (0, -35) m |

The probe saw both vehicles ready and separate PX4 telemetry publishers. It launched uav01 while uav02 remained STORED and received no PX4 command. Both later armed, entered OFFBOARD, and moved physically in SEARCHING. HOLD, RESUME and RTL applied to uav01 while uav02 remained SEARCHING. Commands on each namespaced input topic targeted only system ID 1 or 2 respectively; each namespaced ACK stream contained accepted, source-correlated responses. Both returned, landed and disarmed. Two distinct DroneState publishers and per-vehicle map/local-position agreement were observed.

The first probe run failed its movement threshold for uav02 because it commanded RTL immediately after the SEARCHING transition. The probe now waits for measured movement by both vehicles; the corrected run passed. This was probe timing, not a flight failure.

## Later gates

Two-UAV mission flow, three/eight-PX4 scale, QGC multi-vehicle UI, camera and perception are pending validation. Their launch/configuration presence is not evidence of completion.
