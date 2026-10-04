#!/usr/bin/env bash
set -e
source "$(dirname "$0")/environment.sh"
export ROS_DOMAIN_ID=86
export GZ_PARTITION=wildlife-v04-camera
export ROS_LOG_DIR=/tmp/wildlife-v04-real-camera-logs
export WILDLIFE_RUN_DIR=/tmp/wildlife-v04-real-camera
cd "$WILDLIFE_WORKSPACE_DIR"
python3 tests/px4_real_camera_mission_probe.py \
  --hold-seconds "${OPERATOR_HOLD_S:-3.0}" --output "${CAMERA_EVIDENCE_FILE:-docs/validation/px4_real_camera_mission.json}" & probe_pid=$!
runtime_pid=
cleanup() {
  if [[ -n "$runtime_pid" ]]; then
    kill -INT "$runtime_pid" 2>/dev/null || true
    wait "$runtime_pid" 2>/dev/null || true
  fi
  if [[ -n "$probe_pid" ]]; then
    kill "$probe_pid" 2>/dev/null || true
    wait "$probe_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT
sleep 3
HEADLESS="${HEADLESS-1}" scripts/start_px4_camera.sh detector_backend:=opencv show_rviz:="${SHOW_RVIZ:-false}" \
  search_timeout:=90.0 loiter_duration:=3.0 & runtime_pid=$!
while kill -0 "$probe_pid" 2>/dev/null; do
  if ! kill -0 "$runtime_pid" 2>/dev/null; then
    echo "Real-camera mission runtime exited; inspect $WILDLIFE_RUN_DIR" >&2
    exit 1
  fi
  sleep .5
done
wait "$probe_pid"
probe_pid=
