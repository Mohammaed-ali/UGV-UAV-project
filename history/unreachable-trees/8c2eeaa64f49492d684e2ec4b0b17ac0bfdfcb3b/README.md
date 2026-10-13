# Wildlife ROS 2 Jazzy — V0.4

Academic, non-contact wildlife observation with one logical UGV and up to eight
PX4 SITL UAVs. This continues the verified `v0.3-final` baseline in
`/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3`, on
`codex/v0.4-development`. The nine-package architecture and typed interfaces
are preserved. V0.2 remains frozen separately.

The mission follows deployment → physical search → Detection → persistent
Target → one observer assignment → standoff → operator HOLD/RETURN → PX4 RTL
→ measured landing/disarm → configured docking total → COMPLETE.
PX4 owns flight control and native failsafes. ROS owns mission intent and the
existing `/operator/decision` service remains the operator authority.

## Build and test

```bash
scripts/check_prereqs.sh
scripts/build_ros.sh
source scripts/environment.sh
colcon test --base-paths src --executor sequential
colcon test-result --verbose
```

Use the pinned dependencies in [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md).
ROS logs default to `/tmp`; local transport uses loopback. Run one PX4
scenario at a time and do not rebuild during flight. Start QGroundControl
with `scripts/start_qgc.sh` before flight; this PX4 profile requires its GCS
link for preflight readiness.

## Demonstrations

```bash
# Independent logic demo: eight logical UAVs; no PX4 or camera required.
source scripts/environment.sh
ros2 launch wildlife_bringup subject1_demo.launch.py

# Interactive single-PX4 mission, synthetic detector.
scripts/start_px4_single.sh

# Real Gazebo down-camera and OpenCV, with RViz.
scripts/start_px4_camera.sh detector_backend:=opencv show_rviz:=true
```

Camera operator terminals must use ROS domain 86. Read `/operator/alerts`
for target/UAV IDs. `/operator/decision` accepts `decision: 1` for
CONTINUE_HOLD and `decision: 0` for RETURN. A held observer remains available
for a later RETURN. The automated acceptance helpers simulate these same
typed operator decisions.

[docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) provides the complete commands for
single/two-PX4 missions, four/eight structural checks, two-camera fusion and
mission, moving-target observation, low battery, vehicle unavailability,
two targets, SPLIT eight-aircraft flight and the visible examiner demo.

## Validated scope

Single-PX4 target and no-target missions, independent two-PX4 control, two-UAV
missions, stationary four/eight structure, two real-camera fusion and full
mission, moving dummy observation, battery/mode-loss recovery and reassignment,
and eight-PX4 SPLIT deployment/search/return/COMPLETE have passed live probes.
The eight-aircraft profile uses separated cells and altitude bands with no
cameras; measured minimum horizontal separation was 4.21 m in its accepted
run. QGC displayed distinct Vehicle 1/2 identities and flight states.

Real cameras use the workspace-local **640×480, 10 Hz** model. Retain this
profile: the original 1280×960/30 Hz two-camera attempt overloaded telemetry.
OpenCV projects camera rays through measured PX4 pose onto a flat ground
plane. Two-camera assignment waits for both witnesses before selecting one
observer. Synthetic and single-camera profiles need one witness.

The logical UGV controls deployment timing. Its Gazebo body is a display
proxy, with no physical navigation, tray contact or collision authority.
DOCKED means measured landing/disarm at the simulated home. Tracking velocity
is descriptive; exact image/pose synchronization and calibrated moving-target
accuracy remain unverified. The moving scenario uses a bounded observation
point, with no pursuit. YOLO, eight-camera flight and general collision
avoidance are not implemented or validated.

See [ARCHITECTURE.md](ARCHITECTURE.md), [docs/V0_4_SCOPE.md](docs/V0_4_SCOPE.md),
[docs/V0_4_VALIDATION.md](docs/V0_4_VALIDATION.md),
[docs/V0_4_CAMERA_GEOMETRY.md](docs/V0_4_CAMERA_GEOMETRY.md),
[V0_4_BUILD_REPORT.md](V0_4_BUILD_REPORT.md), and
[V0_4_TEST_RESULTS.md](V0_4_TEST_RESULTS.md) for release evidence and limits.
