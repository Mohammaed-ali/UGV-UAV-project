#!/usr/bin/env bash
set -e
if [[ "$#" -ne 1 || ( "$1" != 4 && "$1" != 8 ) ]]; then
  echo 'Usage: scripts/validate_px4_fleet.sh 4|8' >&2
  exit 2
fi
count="$1"
source "$(dirname "$0")/environment.sh"
export ROS_DOMAIN_ID=85
export GZ_PARTITION=wildlife-v04-fleet
export ROS_LOG_DIR="/tmp/wildlife-v04-fleet-${count}-logs"
export WILDLIFE_RUN_DIR="/tmp/wildlife-v04-fleet-${count}"
cd "$WILDLIFE_WORKSPACE_DIR"
python3 - <<'PY'
import json
from pathlib import Path
base = Path('docs/validation')
assert json.loads((base / 'px4_two_isolation.json').read_text())['result'] == 'PASS'
assert json.loads((base / 'px4_two_mission.json').read_text())['result'] == 'PASS'
PY
python3 tests/px4_fleet_probe.py --count "$count" \
  --output "docs/validation/px4_fleet_${count}.json" & probe_pid=$!
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
HEADLESS=1 scripts/start_px4_fleet.sh "$count" & runtime_pid=$!
while kill -0 "$probe_pid" 2>/dev/null; do
  if ! kill -0 "$runtime_pid" 2>/dev/null; then
    echo "PX4 fleet runtime exited; inspect $WILDLIFE_RUN_DIR" >&2
    exit 1
  fi
  sleep .5
done
wait "$probe_pid"
probe_pid=
if [[ "$count" == 8 ]]; then
  python3 - <<'PY'
import json
from pathlib import Path
base = Path('docs/validation')
assert json.loads((base / 'px4_fleet_8.json').read_text())['result'] == 'PASS'
gate = base / 'px4_acceptance.json'
status = json.loads(gate.read_text())
status['eight_structural'] = 'PASS'
gate.write_text(json.dumps(status, indent=2) + '\n')
PY
fi
