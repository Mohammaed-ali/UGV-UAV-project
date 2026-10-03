# Wildlife ROS 2 Jazzy — V0.4 development

Primary development workspace: `/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3`.
V0.2 remains frozen at `v0.2.0-verified` in Git and in the cleaned V0.2 folder.

The academic mission pipeline remains:
`detector -> Detection -> tracking/fusion -> Target -> assignment -> UAV behavior -> PX4 adapter -> PX4`.
Measured PX4 telemetry returns through `DroneState`. PX4 owns flight control. The existing nine packages and all message/service/action definitions are preserved. The confirmed V0.3 implementation is checkpointed at `v0.3-final` and remains the V0.4 baseline.

## Build and tests

```bash
cd "/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3"
scripts/check_prereqs.sh
scripts/build_ros.sh
source scripts/environment.sh
colcon test --base-paths src --executor sequential
colcon test-result --verbose
```

See `docs/DEPENDENCIES.md` for pinned PX4, px4_msgs, agent and Python setup. Upstream dependency sources live once in `/home/mohammed-ali/Downloads/wildlife_px4_dependencies`, outside the ROS source workspace.

## Single PX4 UAV

In one terminal, start QGroundControl if it is not already running:

```bash
scripts/start_qgc.sh
```

Choose PX4, Multirotor and metric units in its initial preferences. SITL connects through localhost UDP 14550; its serial-device warning does not require changing serial permissions or removing ModemManager for this workflow. Keep QGC connected: the pinned PX4 airframe requires the GCS link before arming.

In another terminal:

```bash
scripts/start_px4_single.sh
```

This starts one x500 in the PX4-compatible wildlife world, one DDS agent, one PX4 adapter, the existing mission graph and RViz. `uav_node` does not run alongside the adapter. Deployment waits for fresh telemetry/preflight readiness. Ctrl+C stops only the process groups this script started. Logs default to `/tmp/wildlife-v03-run`.

Use `/operator/alerts` to find the current target and UAV. The existing `/operator/decision` service accepts `decision: 1` for HOLD and `decision: 0` for RETURN. HOLD retains the opportunity for a later RETURN. Return and landing are performed by PX4 RTL; DOCKED is reported only after measured landing and disarming.

For simulation-only automated acceptance with QGC already running:

```bash
scripts/validate_px4_single.sh
```

This runs no-target timeout/return and target/standoff/HOLD/RETURN missions, then writes the acceptance gate. It exercises simulated operator decisions; normal interactive runs use the operator service.

## Independent deterministic logic demo

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch wildlife_bringup subject1_demo.launch.py
```

The original Gazebo proxy/camera demo remains available via `subject2_demo.launch.py`. It uses logical UAV movement; PX4 runs use `start_px4_single.sh`.

## V0.4 two-PX4 validation

The V0.3 baseline has been checkpointed at `v0.3-final`; V0.4 development is
on `codex/v0.4-development`. With QGroundControl connected, the two-vehicle
isolation and mission gates can be reproduced using:

```bash
scripts/validate_px4_two.sh
scripts/validate_px4_two_mission.sh
```

The first gate independently commands uav01 and uav02 and verifies separate
PX4 telemetry, commands, ACKs, map origins, physical search, return and landing.
The second runs the existing mission graph: both search, one target is assigned
to uav01, the operator holds then returns uav01, and uav02 times out to RTL.
Both vehicles land/disarm before mission COMPLETE. Four/eight stationary PX4
structure can be checked with `scripts/validate_px4_fleet.sh 4` or `8`; this
checks identities, telemetry and readiness without launching the fleet. See
`docs/V0_4_VALIDATION.md`.

## Real Gazebo camera and OpenCV mission

With QGroundControl connected, the one-vehicle camera profile uses the pinned
PX4 `x500_mono_cam_down` model. It bridges actual Gazebo images and CameraInfo
to ROS, where a separate OpenCV PX4 backend produces map-frame Detections from
the visible orange dummy target. Run:

```bash
scripts/validate_px4_camera.sh
scripts/validate_px4_real_camera_mission.sh
```

The second command passed image detection, map localization, one persistent
target assignment, physical standoff, HOLD, RETURN, measured landing/disarm
and COMPLETE. The default PX4 profile still uses `detector_sim`; the real
camera profile selects `detector_backend:=opencv`. Camera frame assumptions
and timing limits are in `docs/V0_4_CAMERA_GEOMETRY.md`.

## Current scope

Single-PX4 target and no-target missions, two-PX4 isolation, one two-PX4
mission flow, and stationary four/eight-PX4 structure pass. QGC links and
single-vehicle RViz markers passed; the QGC multi-vehicle UI and eight-PX4
flight are not yet validated. The two-PX4 runtime uses 35 m separated spawn
points and matching map origins.

The default PX4 run uses deterministic synthetic detections and a logical UGV.
The selected one-PX4 camera profile uses measured-pose ground-plane
localization. Physical UGV/Gazebo integration in the PX4 world, exact
sensor-time pose synchronization, moving visual targets and YOLO remain future
work. The older V0.2 OpenCV node remains available for its logical-camera
demo; it still uses an approximate projection.

See `docs/V0_3_VALIDATION.md`, `docs/V0_3_COMPARISON.md`, `docs/CLEANUP_REPORT.json` and `CODEX_HANDOFF_V0_3.md`.
