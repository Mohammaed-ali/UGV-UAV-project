#!/usr/bin/env bash
set -e
source "$(dirname "$0")/environment.sh"
scenario="${1:-low_battery}"
case "$scenario" in low_battery|vehicle_unavailable|two_targets) ;; *) echo "Unknown health scenario: $scenario" >&2; exit 2 ;; esac
export ROS_DOMAIN_ID=88
export GZ_PARTITION=wildlife-v04-health
export ROS_LOG_DIR=/tmp/wildlife-v04-health-logs
export WILDLIFE_RUN_DIR="/tmp/wildlife-v04-$scenario"
cd "$WILDLIFE_WORKSPACE_DIR"
python3 tests/px4_health_reassignment_probe.py --scenario "$scenario" \
  --output "docs/validation/px4_$scenario.json" & probe_pid=$!
runtime_pid=
cleanup() {
  if [[ -n "$probe_pid" ]]; then kill -INT "$probe_pid" 2>/dev/null || true; wait "$probe_pid" 2>/dev/null || true; fi
  if [[ -n "$runtime_pid" ]]; then kill -INT "$runtime_pid" 2>/dev/null || true; wait "$runtime_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
sleep 3
HEADLESS=1 scripts/start_px4_two.sh px4_single.launch.py \
  sitl_enabled:=true vehicle_count:=2 detector_backend:=none show_rviz:=false \
  search_timeout:=200.0 loiter_duration:=3.0 \
  "validation_file:=$WILDLIFE_WORKSPACE_DIR/docs/validation/px4_acceptance.json" & runtime_pid=$!
while kill -0 "$probe_pid" 2>/dev/null; do
  if ! kill -0 "$runtime_pid" 2>/dev/null; then echo "Health runtime exited; inspect $WILDLIFE_RUN_DIR" >&2; exit 1; fi
  sleep .5
done
wait "$probe_pid"
probe_pid=
