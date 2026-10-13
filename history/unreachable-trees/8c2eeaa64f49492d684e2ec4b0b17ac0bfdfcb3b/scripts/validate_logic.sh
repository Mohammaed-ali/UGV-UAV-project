#!/usr/bin/env bash
set -e
source "$(dirname "$0")/environment.sh"
export ROS_DOMAIN_ID=77
export ROS_LOG_DIR=/tmp/wildlife-v04-logic-logs
cd "$WILDLIFE_WORKSPACE_DIR"
python3 tests/live_probe.py --output docs/validation/v04_logic.json > /tmp/wildlife-v04-logic-probe.log 2>&1 & probe_pid=$!
launch_pid=
cleanup() {
  if [[ -n "$launch_pid" ]]; then
    kill -INT -- "-$launch_pid" 2>/dev/null || true
    wait "$launch_pid" 2>/dev/null || true
  fi
  if [[ -n "$probe_pid" ]]; then
    kill "$probe_pid" 2>/dev/null || true
    wait "$probe_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT
setsid ros2 launch wildlife_bringup subject1_demo.launch.py show_rviz:=false > /tmp/wildlife-v04-logic.log 2>&1 & launch_pid=$!
wait "$probe_pid"
probe_pid=
cat docs/validation/v04_logic.json
