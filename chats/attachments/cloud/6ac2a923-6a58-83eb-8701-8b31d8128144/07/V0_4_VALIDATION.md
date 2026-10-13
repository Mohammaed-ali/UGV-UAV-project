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
Result: `validation/px4_two_mission.json` (143.7 s). The runner used the existing
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

## Gate 7 — QGroundControl multi-vehicle view: PASS for two vehicles

The four/eight runs observed `gcs_connection_lost == false` for each distinct
PX4 system ID. During the accepted two-camera mission, the QGC UI visibly
showed separate Vehicle 1/2 cards: Vehicle 1 in Safe Recovery at 3.9 m while
Vehicle 2 remained armed in Offboard at 15.2 m. The selected vehicle showed
50% battery, map position and motion indicators. Evidence:
`validation/qgc_two_camera_mission.png`. The initial fleet sensor warning
was also visible and retained in `qgc_fleet_initial_fault.png`.
Eight system IDs/links passed backend probes; every eight-vehicle UI page
was not individually inspected. QGC remains native flight status; the ROS
operator service remains mission authority.

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
interpolation. At that checkpoint, live health and moving-target validation
were still pending; the later sections record their completed live gates. Logs: `/tmp/wildlife-v04-continuation-build.log` and
`/tmp/wildlife-v04-continuation-tests.log`.

## Release gate tracking

All applicable release gates are recorded below, including final examiner/RViz
visual QA. Failed attempts are retained alongside passing results. The scope
limits are separate from successful configured demonstrations.

## Gate 13 — moving visual target: PASS

`scripts/validate_px4_moving_target.sh` passed in 104.0 s. The YAML waypoint
loop moves `dummy_wildlife_01` at a configured 0.35 m/s using Gazebo's
`set_pose` service. 186 updates were accepted; one startup request failed.
The real camera delivered 771 images and 31 OpenCV detections. Tracking
retained one `tgt_001`, populated velocity (maximum reported 0.731 m/s), and
the existing mission completed standoff, CONTINUE_HOLD, RETURN, measured
landing/disarm and COMPLETE. Evidence: `validation/px4_moving_target.json`
and `validation/moving_target_motion.json`.

Velocity is a smoothed finite difference of noisy camera locations, not a
calibrated speed measurement. The probe's `minimum_target_error_m` compares
with the starting point (15, 8), not the contemporaneous moving-model pose;
it must not be interpreted as moving-target localization accuracy. The UAV
holds its original standoff point; it does not chase the target. Stale/lost
and reacquisition behavior remains covered by regression tests.

## Gate 14 — health, recovery, reassignment and multiple targets: PASS

`scripts/validate_px4_health.sh low_battery` passed using PX4's own battery
simulator. uav01 reported below 20% in both BatteryStatus and DroneState;
mission logic requested RETURN exactly once. The coordinator released its
assignment on a positive RETURNING state and the same `tgt_001` transferred
to uav02. The new observer completed HOLD/RETURN. Both landed/disarmed before
COMPLETE. The probe restored the original PX4 simulator parameters.

`scripts/validate_px4_health.sh vehicle_unavailable` passed after a deliberate
PX4 Offboard-to-loiter mode change. The adapter reported PAUSED and stopped
its heartbeat; it did not fight the PX4-selected mode. No release occurred
during the three-second pause. An explicit typed RETURN enabled recovery
and the same target transferred to uav02. Both landed/disarmed and completed.
This tests mode-loss recovery, not every possible PX4 native failsafe.

`scripts/validate_px4_health.sh two_targets` passed with two spatially
separated synthetic targets. Two distinct IDs were assigned to different
UAVs; each completed HOLD/RETURN, landing/disarm and mission COMPLETE.
These three gates use typed synthetic Detections with real PX4 movement.
Evidence: `validation/px4_low_battery.json`,
`validation/px4_vehicle_unavailable.json`, `validation/px4_two_targets.json`.
Unit tests cover stale-state exclusion, no reassignment on pause, retry when
no UAV is available, terminal target preservation and no duplicate UAV use.

## Gate 16 — two-camera perception through the complete mission: PASS

`scripts/validate_px4_two_camera_mission.sh` passed in 163.7 s with the
640×480/10 Hz profile. uav01/uav02 supplied 38/53 real-camera detections,
both witnessed one `tgt_001`, and only uav01 was assigned. uav02 kept
searching; uav01 completed HOLD/RETURN, and uav02 later timed out to RTL.
Both landed/disarmed before COMPLETE. Evidence:
`validation/px4_two_camera_mission.json`.

The first complete camera attempt assigned the first observer before fusion
and created a second track as views changed. Its failed evidence remains in
`validation/px4_two_camera_mission_attempt_1.json`. The two-camera mission
profile now requires two witnesses before assignment and uses the already
validated 4 m camera fusion gate. Single-camera and synthetic profiles retain
one-witness assignment. This gate is an association radius, not a claim that
arbitrarily close physical animals can be distinguished.

QGroundControl visibly displayed Vehicle 1/2 with distinct flight modes,
armed states and altitudes during this run. The selected vehicle's battery,
map position, velocity and recovery mode were visible. The older QGC process
stopped responding after repeated eight-vehicle restarts; it was replaced
with a fresh instance using the existing helper. Screenshots and final RViz
QA are recorded separately.

## Gates 15 and eight-aircraft deployment/flight — PASS

`scripts/validate_px4_fleet_flight.sh` passed in 236.8 s with eight actual
PX4 vehicles. SPLIT waypoint events 0/1 produced exactly one launch per UAV
in order. All became ready, armed and entered OFFBOARD; all eight searched
simultaneously. Every command targeted the correct system ID and each had
accepted source-correlated ACKs. All eight returned, landed and disarmed
before COMPLETE. No PAUSED fault state occurred. Evidence:
`validation/px4_fleet_flight.json`; `px4_acceptance.json` now records
`eight_uav: PASS`. This demonstrates a no-target fleet mission, not eight
camera/perception missions.

The 12 m spaced cells use a +/-4 m X sweep and no Y sweep, with altitude
layers. Across 678 samples with fresh measured poses, horizontal separation
never fell below 4.21 m; minimum 3D separation was 4.47 m. This is basic
mission-level planning for this profile, not arbitrary collision avoidance.

Three failed attempts are retained. Attempt 1 lacked uav03 sensor readiness;
sequential model/PX4 startup resolved it. Attempt 2 flew all eight but
telemetry loss prevented final ROS docking accounting. Attempt 3 stopped
early in takeoff because slow telemetry exceeded its receipt-age threshold.
Local discovery, terminal measured-docking handling, and a separate three-
second status/landing limit were then verified. Local position retains the
existing two-second limit configured in `config/px4.yaml`. The separate
class default is one second; it was not the live profile's effective value.
The earlier one-second live-profile description was incorrect.

PX4's pinned LandDetector source publishes at one Hz of simulation time.
The passing run measured status gaps up to 1.513 wall seconds and landing
status gaps up to 2.943 seconds. The larger slow-stream limit does not extend
local-position freshness or replace PX4's native failsafes. Recovered native
landing requires fresh landing/disarm and proximity to the latched home.
Confirmed DOCKED is retained across later transport loss.

Performance evidence: `validation/px4_fleet_performance.json` and the flight
probe's CPU/RSS samples. On this i5-13420H / roughly 16 GB host, the Gazebo
return-phase timing sample was about 0.40 real-time factor. Process CPU values
are lifetime averages and RSS is KiB. This is one measured local profile,
not a capacity guarantee. Eight cameras/YOLO are not tested. The separate
late rate probe received no data and is explicitly marked NO_DATA; the
passing flight's internal interval measurements are the valid evidence.

## Gate 17 — visible examiner demonstration and RViz QA: PASS

The visible real-camera examiner mission passed in 114.9 s
(`validation/px4_examiner_demo.json`). A final capture run passed in 144.0 s
(`validation/px4_examiner_visual_qa.json`): 1122 real images, 31 detections,
one persistent target/observer, CONTINUE_HOLD, RETURN, measured home landing,
disarm and COMPLETE. The Gazebo UGV visual proxy mirrored logical pose and
the actual camera aircraft was present in the world.

The captured RViz view has Global Status: OK and readable uav01,
AWAITING_OPERATOR, 50% battery, tgt_001/dummy_animal/confidence/HOLD,
measured path, standoff ring and target-to-UAV assignment line. Evidence:
`validation/rviz_examiner_standoff.png`. Gazebo captures show the orange dummy,
UGV proxy and actual x500 camera entity; a wider view includes the small
aircraft above the ground horizon. Evidence:
`validation/gazebo_examiner_standoff.png`, `gazebo_examiner_overview.png`.
The viewer angle was adjusted without changing world poses or flight commands.
RViz provides the clearer mission overview; the Gazebo ground is visually dark.

The first GUI examiner attempt failed after 31.5 s without detections. Its
landing-status receipt gap (1.04 s) exceeded an inadvertently introduced
one-second split default. The default now inherits the configured two-second
baseline timeout; only the fleet profile explicitly selects three seconds.
The failed result is preserved in `px4_examiner_demo_attempt_1.json`.
The earlier small RViz view/map-frame warning is preserved as initial QA
(`rviz_camera_initial_qa.png`); the final view uses an explicit identity TF
and a larger view. Only the final captures support the visual PASS.

## Final automated regression — PASS

All nine packages built at version 0.4.0. Final colcon result: **56 entries,
0 errors, 0 failures, 0 skipped**. This comprises 51 distinct Python cases
plus five CTest wrapper entries, not 56 independent behavioral tests.
Evidence: `validation/v04_final_tests.json` and `v04_final_test_results.log`.
The checks cover deployment, operator/mission state, tracker/fusion/velocity,
health assignment/recovery, PX4 identity/frames/ACKs, camera rays and motion.
Static checks parsed 67 Python, 23 XML/SDF/model-config, 14 YAML and 24 shell
files, and imported/generated all 11 launch descriptions. Typed definitions
are identical to v0.3-final. Evidence: `validation/v04_static_checks.json`.

## Independent logic / SINGLE deployment regression — PASS

`scripts/validate_logic.sh` passed in 160.7 s: the original eight logical UAVs
launched exactly once in order at SINGLE waypoint 0. uav01/uav05 accepted
HOLD then RETURN; remaining vehicles completed their configured search/return.
All eight docked before COMPLETE; 780 marker arrays were observed. Evidence:
`validation/v04_logic.json`. SPLIT was separately verified by the eight-PX4
flight and unit tests; no waypoint-index arithmetic was changed.

After COMPLETE, forced process-group shutdown produced existing rclpy
ExternalShutdownException/KeyboardInterrupt traces; the optional daemon stdin
console also aborted at interpreter finalization. This is a shutdown warning,
not a live mission failure. The typed service completed successfully and all
owned mission processes stopped. Graceful console-thread shutdown remains a
known cleanup limitation. QGC is left running for the user.
