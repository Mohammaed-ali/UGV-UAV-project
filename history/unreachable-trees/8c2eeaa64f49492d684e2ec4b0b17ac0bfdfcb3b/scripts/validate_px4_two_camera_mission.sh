#!/usr/bin/env bash
set -e
source "$(dirname "$0")/environment.sh"
export ROS_DOMAIN_ID=90
export GZ_PARTITION=wildlife-v04-two-camera-mission
export ROS_LOG_DIR=/tmp/wildlife-v04-two-camera-mission-logs
export WILDLIFE_RUN_DIR=/tmp/wildlife-v04-two-camera-mission
cd "$WILDLIFE_WORKSPACE_DIR"
python3 tests/px4_two_mission_probe.py --two-camera \
  --output docs/validation/px4_two_camera_mission.json & probe_pid=$!
runtime_pid=
cleanup() {
  if [[ -n "$runtime_pid" ]]; then kill -INT "$runtime_pid" 2>/dev/null || true; wait "$runtime_pid" 2>/dev/null || true; fi
  if [[ -n "$probe_pid" ]]; then kill "$probe_pid" 2>/dev/null || true; wait "$probe_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
sleep 3
HEADLESS=1 scripts/start_px4_two_camera.sh px4_single.launch.py \
  sitl_enabled:=true vehicle_count:=2 detector_backend:=opencv \
  show_rviz:="${SHOW_RVIZ:-false}" search_timeout:=65.0 loiter_duration:=3.0 \
  "validation_file:=$WILDLIFE_WORKSPACE_DIR/docs/validation/px4_acceptance.json" & runtime_pid=$!
while kill -0 "$probe_pid" 2>/dev/null; do
  if ! kill -0 "$runtime_pid" 2>/dev/null; then echo "Two-camera mission runtime exited; inspect $WILDLIFE_RUN_DIR" >&2; exit 1; fi
  sleep .5
done
wait "$probe_pid"
probe_pid=
