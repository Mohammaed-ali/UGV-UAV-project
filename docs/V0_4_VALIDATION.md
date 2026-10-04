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

## Gate 4 — two-PX4 mission flow: PASS

Run: `scripts/validate_px4_two_mission.sh` with QGroundControl connected.
Result: `validation/px4_two_mission.json` (144.4 s). The runner used the existing
mission graph with one configured synthetic target and separate search lanes.

Both vehicles became ready, armed, entered OFFBOARD and SEARCHING. uav01 made
two detections; the tracker produced one persistent target ID (`tgt_001`),
assigned once to uav01. uav02 remained SEARCHING during the assignment.
uav01 reached STANDOFF and AWAITING_OPERATOR, accepted CONTINUE_HOLD followed
by RETURN, and landed/disarmed. uav02 followed the no-target timeout/loiter/RTL
path and also landed/disarmed. The mission did not enter COMPLETE until both
were DOCKED. The acceptance gate now records `two_uav: PASS`.

## Gates 5–6 — four/eight PX4 structural scale: PASS

Runs: `scripts/validate_px4_fleet.sh 4` and
`scripts/validate_px4_fleet.sh 8` with a GCS link.
Results: `validation/px4_fleet_4.json` and
`validation/px4_fleet_8.json`.

Four and eight PX4 instances each produced distinct, valid local telemetry
with matching ROS DroneState identity and map origins. MAV system IDs were
1–4 and 1–8 respectively; each had a unique `/uavNN` DDS namespace and
`x500_N` Gazebo entity. Every vehicle became ready with a GCS link and
remained STORED/disarmed. No adapter sent a PX4 command before deployment.
The eight-run sample recorded eight PX4 processes at about 21 MiB RSS each
and roughly 18% CPU each while stationary; Gazebo/ROS process load was not
included in that sample. These are structural runs, not multi-vehicle flight.

The initial four-vehicle probe stopped on the final readiness event before
the last DroneState callback. Waiting for the complete telemetry set fixed
the probe; four and eight then passed.

## Gate 7 — QGroundControl multi-vehicle view: PARTIALLY VALIDATED

The four/eight runs observed `gcs_connection_lost == false` for each distinct
PX4 system ID. This verifies a GCS link to each instance. The QGroundControl
vehicle list, displayed position, mode, battery and warnings were not
visually inspected in this session.

## Gates 8–11 — real camera and one target mission: PASS

The pinned `x500_mono_cam_down` Gazebo sensor was observed at its actual
`/world/wildlife_px4/model/x500_mono_cam_down_0/.../imager/image` topic. The
installed `ros_gz_bridge` published it as
`/drones/uav01/camera/image_raw`, together with CameraInfo. The repeatable
camera-only probe `scripts/validate_px4_camera.sh` passed: 15 RGB 640×480
frames, increasing stamps, `camera_link` frame ID, valid intrinsics, and
successful `cv_bridge` conversion. Observed delivery rate was 10.31 fps for
that short sample (`validation/px4_camera.json`).

The world has a stationary orange visual dummy at map (15, 8) m. The
`opencv` backend in `wildlife_perception` uses actual image pixels,
CameraInfo, fresh DroneState position and PX4 attitude for ground-plane
localization. `scripts/validate_px4_real_camera_mission.sh` passed
(`validation/px4_real_camera_mission.json`, 87.6 s): 794 image messages,
27 OpenCV Detections, one persistent Target assigned to uav01, physical
standoff, operator HOLD then RETURN, measured landing/disarming and mission
COMPLETE. The best measured detection was 0.54 m from the configured target
position. This result does not establish a general geolocation error bound;
see `V0_4_CAMERA_GEOMETRY.md` for frame and timing assumptions.

## Gate 12 — two real cameras, one fused target: PASS

`scripts/validate_px4_two_camera_fusion.sh` passed in 77.3 s
(`validation/px4_two_camera_fusion.json`). uav01 and uav02 produced 5 and 1
real-image detections respectively. The tracker retained one `tgt_001` with
both UAVs as witnesses. Both vehicles became ready, flew in OFFBOARD, then
returned, landed and disarmed. This profile tests observation/fusion; it does
not run mission assignment. The separate two-PX4 mission gate tests assignment.

The workspace-local `mono_cam` model uses 640×480 at 10 Hz for both camera
profiles. The earlier 1280×960 at 30 Hz two-camera attempt overloaded
telemetry and triggered failsafe landing. Keep the reduced-load profile;
upstream PX4 sources and dependency pins remain unchanged.

## Continuation regression — 2026-10-04: PASS

All nine ROS packages rebuilt. `colcon test-result --verbose` reports
50 entries, zero errors/failures/skips, including target velocity, battery and
stale-state assignment filters, one-shot low-battery RETURN, and motion
interpolation. These unit checks do not establish the pending live health
and moving-target gates. Logs: `/tmp/wildlife-v04-continuation-build.log` and
`/tmp/wildlife-v04-continuation-tests.log`.

## Later gates

Eight-PX4 deployment/flight, QGC multi-vehicle UI inspection,
moving-target flight, health/fault flight and deconfliction flight
remain pending validation. Their launch/configuration presence is not evidence
of completion.
