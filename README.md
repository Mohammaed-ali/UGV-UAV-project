# Wildlife ROS 2 Jazzy — V0.3

Primary development workspace: `/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3`.
V0.2 remains frozen at `v0.2.0-verified` in Git and in the cleaned V0.2 folder.

The academic mission pipeline remains:
`detector -> Detection -> tracking/fusion -> Target -> assignment -> UAV behavior -> PX4 adapter -> PX4`.
Measured PX4 telemetry returns through `DroneState`. PX4 owns flight control. The existing nine packages and all message/service/action definitions are preserved. The supplied V0.3 workspace is a reference, not a replacement.

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

## Current scope

Single-PX4 target and no-target missions, QGC connectivity and RViz markers passed. Two/eight adapter configurations exist with active IDs, namespaced DDS, origin and altitude parameters, but fleet flight and physical separation have not been validated. Counts above one require lower-count acceptance; the provided runtime starts one vehicle only.

The PX4 run uses deterministic synthetic detections and a logical UGV. Physical UGV/Gazebo integration in the same PX4 world and calibrated camera geolocation are later milestones. Optional V0.2 OpenCV plumbing remains available; it is an approximate colored-blob detector, not a validated map-geolocation or YOLO pipeline.

See `docs/V0_3_VALIDATION.md`, `docs/V0_3_COMPARISON.md`, `docs/CLEANUP_REPORT.json` and `CODEX_HANDOFF_V0_3.md`.
