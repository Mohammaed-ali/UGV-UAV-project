#!/usr/bin/env bash
set -e
source "$(dirname "$0")/environment.sh"
export ROS_DOMAIN_ID=84
export GZ_PARTITION=wildlife-v04-two
export ROS_LOG_DIR=/tmp/wildlife-v04-two-mission-logs
export WILDLIFE_RUN_DIR=/tmp/wildlife-v04-two-mission
cd "$WILDLIFE_WORKSPACE_DIR"
python3 tests/px4_two_mission_probe.py --output docs/validation/px4_two_mission.json & probe_pid=$!
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
HEADLESS=1 scripts/start_px4_two.sh px4_single.launch.py \
  'sitl_enabled:=true' 'vehicle_count:=2' 'single_target:=true' \
  'show_rviz:=false' 'detection_probability:=1.0' \
  'search_timeout:=65.0' 'loiter_duration:=3.0' \
  "validation_file:=$WILDLIFE_WORKSPACE_DIR/docs/validation/px4_acceptance.json" & runtime_pid=$!
while kill -0 "$probe_pid" 2>/dev/null; do
  if ! kill -0 "$runtime_pid" 2>/dev/null; then
    echo "Two-PX4 mission runtime exited; inspect $WILDLIFE_RUN_DIR" >&2
    exit 1
  fi
  sleep .5
done
wait "$probe_pid"
probe_pid=
python3 - <<'PY'
import json
from pathlib import Path

base = Path('docs/validation')
assert json.loads((base / 'px4_two_isolation.json').read_text())['result'] == 'PASS'
assert json.loads((base / 'px4_two_mission.json').read_text())['result'] == 'PASS'
gate = base / 'px4_acceptance.json'
status = json.loads(gate.read_text())
assert status['one_uav'] == 'PASS'
status['two_uav'] = 'PASS'
gate.write_text(json.dumps(status, indent=2) + '\n')
PY
