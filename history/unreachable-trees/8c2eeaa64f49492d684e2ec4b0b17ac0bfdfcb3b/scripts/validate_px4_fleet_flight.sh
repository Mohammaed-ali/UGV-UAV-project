#!/usr/bin/env bash
set -e
source "$(dirname "$0")/environment.sh"
export ROS_DOMAIN_ID=89
export GZ_PARTITION=wildlife-v04-fleet-flight
export ROS_LOG_DIR=/tmp/wildlife-v04-fleet-flight-logs
export WILDLIFE_RUN_DIR=/tmp/wildlife-v04-fleet-flight
cd "$WILDLIFE_WORKSPACE_DIR"
python3 - <<'PY'
import json
from pathlib import Path
p=Path('docs/validation')
for name in ('px4_fleet_8.json','px4_low_battery.json','px4_vehicle_unavailable.json'):
    assert json.loads((p/name).read_text())['result']=='PASS', name
PY
python3 tests/px4_fleet_flight_probe.py --output docs/validation/px4_fleet_flight.json & probe_pid=$!
runtime_pid=
cleanup() {
  if [[ -n "$runtime_pid" ]]; then kill -INT "$runtime_pid" 2>/dev/null || true; wait "$runtime_pid" 2>/dev/null || true; fi
  if [[ -n "$probe_pid" ]]; then kill "$probe_pid" 2>/dev/null || true; wait "$probe_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
sleep 3
HEADLESS=1 scripts/start_px4_fleet.sh 8 px4_single.launch.py \
  sitl_enabled:=true deployment_mode:=SPLIT detector_backend:=none show_rviz:=false \
  search_timeout:=45.0 loiter_duration:=3.0 \
  "validation_file:=$WILDLIFE_WORKSPACE_DIR/docs/validation/px4_acceptance.json" & runtime_pid=$!
while kill -0 "$probe_pid" 2>/dev/null; do
  if ! kill -0 "$runtime_pid" 2>/dev/null; then echo "Fleet runtime exited; inspect $WILDLIFE_RUN_DIR" >&2; exit 1; fi
  sleep .5
done
wait "$probe_pid"
probe_pid=
python3 - <<'PY'
import json
from pathlib import Path
p=Path('docs/validation/px4_acceptance.json')
data=json.loads(p.read_text()); data['eight_uav']='PASS'
p.write_text(json.dumps(data,indent=2)+'\n')
PY
