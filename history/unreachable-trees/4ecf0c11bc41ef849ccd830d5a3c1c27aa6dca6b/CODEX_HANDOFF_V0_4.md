# V0.4 continuation handoff — 2026-10-04

The original V0.4 request is in `/home/mohammed-ali/.codex/attachments/6f037b0f-202e-4781-ad34-a3ef900b1863/Pasted text.txt`. Continue in `/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3`, branch `codex/v0.4-development`. This is an unfinished development branch, **not** a completed V0.4 release. Do not discard the uncommitted working tree.

## Baseline and committed checkpoints

- V0.3 baseline: `8ca1e9d` (`v0.3-final` tag). Nine ROS 2 packages; existing mission FSM and PX4 adapter were reused.
- `95dacc0`: two PX4 instances with independent namespaces and commands.
- `bc8b6f2`: two-PX4 target mission and completion.
- `f911234`: four- and eight-PX4 stationary structural validation.
- `6d72e5b`: real Gazebo camera, OpenCV localization, and single-PX4 mission.
- Pinned local dependencies remain PX4 v1.17.0 (`d6f12ad1`), px4_msgs (`86d8239e`), and XRCE agent (`73622810`) under `/home/mohammed-ali/Downloads/wildlife_px4_dependencies`.

## Verified live results

- `scripts/validate_px4_single.sh`: both no-target timeout/RTL and target/standoff/HOLD/RETURN passed twice; landed, disarmed, mission COMPLETE.
- `scripts/validate_px4_two.sh`: two vehicles ready, searching, independently commanded and acknowledged, then landed/disarmed. Evidence: `docs/validation/px4_two_isolation.json`.
- `scripts/validate_px4_two_mission.sh`: target assigned only to uav01 while uav02 kept searching; HOLD/RETURN, timeout/RTL, and mission COMPLETE passed. Evidence: `docs/validation/px4_two_mission.json`.
- `scripts/validate_px4_fleet.sh 4` and `8`: unique IDs, namespaces, Gazebo entities, map origins, valid telemetry, DroneState and GCS links passed while stationary. **Eight-UAV flight was not tested.** Evidence: `docs/validation/px4_fleet_4.json`, `px4_fleet_8.json`.
- `scripts/validate_px4_camera.sh`: actual Gazebo RGB down-camera and CameraInfo passed at 640×480, about 10 Hz. The workspace-local `src/wildlife_simulation/models/mono_cam/` copy reduces camera load; no upstream dependency was modified.
- `scripts/validate_px4_real_camera_mission.sh`: latest reduced-load profile passed in 87.6 s with 794 images, 27 OpenCV detections, one persistent target, standoff, HOLD/RETURN, landing/disarm and COMPLETE. Evidence: `docs/validation/px4_real_camera_mission.json`.
- `scripts/validate_px4_two_camera_fusion.sh`: both real PX4 cameras observed the same visual dummy and fused into one `tgt_001` with both UAVs in its witness list. Both returned and landed. Evidence: `docs/validation/px4_two_camera_fusion.json`. This test exercised observation/fusion, not mission assignment.
- Last ROS build passed; last `colcon test` passed **50 entries, 0 failures**, including new tracker, health and motion interpolation tests. ROS logs must be redirected to `/tmp` because the sandbox cannot write `~/.ros/log`.
- `docs/validation/px4_acceptance.json`: `one_uav=PASS`, `two_uav=PASS`, `eight_structural=PASS`, `eight_uav=NOT_TESTED`.

## Uncommitted work

The working tree contains tracker velocity estimation, battery and stale-state assignment filters, one-shot low-battery RETURN_HOME, new regression tests, two-camera launch/probe/bridge scripts, and the workspace-local 640×480/10 Hz camera model. The passing two-camera and latest camera JSON files are also uncommitted. Inspect `git status --short`; commit coherent verified work before beginning a new feature.

There is also a newly coded **moving-target scenario that has not been live-tested**: `src/wildlife_simulation/config/moving_target.yaml`, `wildlife_simulation/target_motion.py`, `scripts/move_dummy_target.py`, `scripts/validate_px4_moving_target.sh`, `tests/test_target_motion.py`, and optional `--moving` checks in `tests/px4_real_camera_mission_probe.py`. The Gazebo `set_pose` service exists, but its calls and the full moving-target mission still need live validation. Run the script, resolve any runtime or service-format issues, and save the resulting evidence. Local PX4/Gazebo runtime needs sandbox escalation for UDP/DDS sockets.

The first two-camera attempt at 1280×960/30 Hz saturated telemetry and triggered failsafe landing; the 640×480/10 Hz local model passed. Preserve this lower-load profile for two-camera work.

## Documentation and remaining gates

`docs/V0_4_VALIDATION.md` and `docs/V0_4_CAMERA_GEOMETRY.md` still contain old 1280×960/30 Hz single-camera numbers and incorrectly list two-camera fusion as pending. Update them from the latest JSON evidence. Existing documentation includes `README.md`, `ARCHITECTURE.md`, `docs/DEPENDENCIES.md`, and the two V0.4 documents above.

Still pending: moving-target live test; live low-battery/fault and reassignment tests; deconfliction flight; eight-UAV flight/deployment; QGroundControl multi-vehicle UI inspection; RViz visual QA; and any other gates in the original V0.4 brief. YOLO remains optional and unimplemented. Required release documentation/report/tag/archive are not done. No `v0.4` final tag exists; do not claim V0.4 definition of done.

Suggested next sequence: inspect working tree and original brief; commit the already verified fusion/health work; correct stale docs; run the moving-target gate; then work through remaining live gates and the final report. Stop broad optional retesting once each concrete risk is verified.
