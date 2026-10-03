# Continue V0.3

Primary source: `/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3`.
Shared dependencies: `/home/mohammed-ali/Downloads/wildlife_px4_dependencies`.
Preserve current Git history and V0.2 tag v0.2.0-verified. Reference workspace is a gap checklist only. Keep all nine package boundaries and unchanged typed interfaces. PX4 owns low-level flight control; detector/Target/UAV behavior and operator RETURN/HOLD remain ROS logic. No harmful behavior.

Single-UAV acceptance PASSED in the custom wildlife world for target/standoff/HOLD/RETURN and no-target timeout/RTL, with QGC connected and measured landing/disarming. Build all nine packages and run 32 behavioral regressions. Evidence: docs/V0_3_VALIDATION.md and docs/validation. Use scripts/environment.sh and scripts/start_px4_single.sh; QGC must stay connected. scripts/validate_px4_single.sh reruns both probes.

Next: implement/test an owned-process TWO-instance runtime (IDs 1/2, /uav01 /uav02) with namespace/command isolation, accurate spawn mapping and deployment/return. Do not claim eight flight validated from launch composition. Follow 1 -> 2 -> 8. Eight configuration is structural only. Check performance/separation before fleet operation.

Later: compose physical UGV with measured odometry into the PX4 world; implement calibrated camera projection from actual UAV pose with calibration/synchronization before claiming map detections. Keep synthetic detector selectable. No micro-ROS/Nav2/YOLO additions merely for complexity.

V0.2 cleanup is finished: generated build/install/log/dependency caches removed after new build verification, all source/assets/docs/tests/Git retained. Do not delete shared upstream sources. Desktop saved-project association still uses V0.2 and requires opening V0.3 in the app; commands have already migrated.
