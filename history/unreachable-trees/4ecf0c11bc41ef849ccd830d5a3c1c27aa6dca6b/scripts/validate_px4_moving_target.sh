#!/usr/bin/env bash
set -e
source "$(dirname "$0")/environment.sh"
export ROS_DOMAIN_ID=86
export GZ_PARTITION=wildlife-v04-camera
export ROS_LOG_DIR=/tmp/wildlife-v04-moving-logs
export WILDLIFE_RUN_DIR=/tmp/wildlife-v04-moving
cd "$WILDLIFE_WORKSPACE_DIR"
python3 tests/px4_real_camera_mission_probe.py --moving \
  --output docs/validation/px4_moving_target.json & probe_pid=$!
runtime_pid=
motion_pid=
cleanup() {
  if [[ -n "$motion_pid" ]]; then
    kill -INT "$motion_pid" 2>/dev/null || true
    wait "$motion_pid" 2>/dev/null || true
  fi
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
HEADLESS=1 scripts/start_px4_camera.sh detector_backend:=opencv \
  search_timeout:=90.0 loiter_duration:=3.0 & runtime_pid=$!
sleep 5
python3 scripts/move_dummy_target.py \
  --scenario src/wildlife_simulation/config/moving_target.yaml \
  --output docs/validation/moving_target_motion.json & motion_pid=$!
while kill -0 "$probe_pid" 2>/dev/null; do
  if ! kill -0 "$runtime_pid" 2>/dev/null || ! kill -0 "$motion_pid" 2>/dev/null; then
    echo "Moving-target runtime exited; inspect $WILDLIFE_RUN_DIR" >&2
    exit 1
  fi
  sleep .5
done
wait "$probe_pid"
probe_pid=
kill -INT "$motion_pid"
wait "$motion_pid"
motion_pid=
python3 - <<'PY'
import json
from pathlib import Path
base=Path('docs/validation')
assert json.loads((base/'px4_moving_target.json').read_text())['result']=='PASS'
motion=json.loads((base/'moving_target_motion.json').read_text())
assert motion['result']=='PASS' and motion['accepted_updates']>=10
PY
