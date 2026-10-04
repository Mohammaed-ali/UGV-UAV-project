# V0.4 test results — 2026-10-04

Release: `v0.4-final`, based on `v0.3-final` at `8ca1e9d`. Live evidence belongs
to the tested local dependency pins and host profile, not real hardware.

## Build / automated checks — PASS

- Final ROS build: **9 packages finished**, versions 0.4.0.
- Final colcon result: **56 entries, 0 errors, 0 failures, 0 skipped**.
- Distinct Python cases: **51**; five CTest wrappers account for the remaining
  entries. Suites: general regression 22, PX4 adapter 19, geometry 7, OpenCV
  image/blob handling 1, target motion 2.
- Static checks: 67 Python, 23 XML/SDF/model-config, 14 YAML and 24 shell files;
  all 11 launch descriptions imported/generated. Typed definitions unchanged.
- Evidence: [final_tests.json](docs/validation/v04_final_tests.json),
  [test-result log](docs/validation/v04_final_test_results.log),
  [static checks](docs/validation/v04_static_checks.json).

The behavioral suite covers stable IDs/association/expiry/fusion/velocity,
lifecycle preservation, one observer, fresh state/battery/witness exclusion,
confirmed-return reassignment, multi-target retry, deployment SINGLE/SPLIT,
active IDs/readiness/deduplication/waypoint semantics, HOLD/RETURN, mission
pause/resume/abort and completion, PX4 identity/frame origins/bounds/ACKs/
readiness/queued launch/timeouts/recovery, camera ray transforms and moving
path interpolation. It does not claim full perception accuracy from one
OpenCV image test; actual image callbacks are exercised by live camera runs.

## Live demonstrations — PASS

| Demonstration | Evidence | Accepted elapsed |
|---|---|---:|
| Single no-target timeout/RTL | px4_no_target.json | 85.6 s |
| Single synthetic target/HOLD/RETURN | px4_target.json | 91.3 s |
| Independent two-PX4 commands/telemetry/ACKs | px4_two_isolation.json | 84.1 s |
| Two-PX4 mission, one observer | px4_two_mission.json | 143.7 s |
| Stationary four / eight PX4 | px4_fleet_4.json / px4_fleet_8.json | 17.4 / 20.8 s |
| Real camera/Image/CameraInfo/cv_bridge | px4_camera.json | 9.1 s |
| Real-camera OpenCV target mission | px4_real_camera_mission.json | 87.6 s |
| Two-camera same-target fusion | px4_two_camera_fusion.json | 77.3 s |
| Moving visual dummy + real-camera flight | px4_moving_target.json | 104.0 s |
| Simulated PX4 low battery + reassignment | px4_low_battery.json | 92.4 s |
| Mode-loss unavailable/recovery/reassignment | px4_vehicle_unavailable.json | 92.6 s |
| Two separated synthetic targets | px4_two_targets.json | 81.9 s |
| Eight-PX4 SPLIT flight and separation | px4_fleet_flight.json | 236.8 s |
| Two real-camera full mission | px4_two_camera_mission.json | 163.7 s |
| Visible examiner camera mission | px4_examiner_demo.json | 114.9 s |
| Final examiner visual capture mission | px4_examiner_visual_qa.json | 144.0 s |
| Eight logical UAVs/SINGLE/operator/COMPLETE | v04_logic.json | 160.7 s |

All JSON paths are under `docs/validation/`. Tests that contain flight-to-home
require native landed/disarmed evidence and appropriate mission completion;
stationary structure and camera-only checks do not claim flight completion.
Eight-flight minimum measured horizontal/3D spacing: **4.21 / 4.47 m**,
678 fresh-pose samples. It validates a no-target fleet profile with no cameras.

QGC visual QA: distinct Vehicle 1/2 cards and modes/altitudes/arming, selected
battery/map/motion; `qgc_two_camera_mission.png`. RViz: Global Status OK,
readable measured observer/state/battery/target/confidence/HOLD, standoff ring,
assignment line and trail; `rviz_examiner_standoff.png`. Gazebo: orange dummy,
logical UGV display proxy and camera aircraft entity; standoff/overview PNGs.

## Failed attempts retained / warnings

Three eight-flight attempts failed before the fourth accepted run: readiness,
late transport/accounting loss, and slow-stream freshness. A two-camera full
mission initially produced duplicate tracks before witness gating; the final
run retained one ID. The first visible examiner attempt failed after an
inadvertent one-second slow-stream default; the inherited two-second default
passed subsequent visible runs. Corresponding `*_attempt_*.json` evidence
remains in Git. The high-load two-camera trial predates the reduced profile
and its telemetry overload remains documented; it is not a supported profile.

The separate late fleet-rate probe has NO_DATA and is excluded from passing
measurements. Shutdown after logic COMPLETE printed existing rclpy interrupt
traces and the daemon keyboard-console finalization warning; helpers stopped
all owned mission processes. There were no automated test skips/failures.

Calibration, eight-camera flight, physical UGV/tray docking, YOLO and general
collision avoidance remain untested/unimplemented. See the build report for
PARTIALLY VALIDATED, NOT TESTED and KNOWN LIMITATION distinctions.
