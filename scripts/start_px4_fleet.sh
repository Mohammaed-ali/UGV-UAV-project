#!/usr/bin/env bash
set -e
source "$(dirname "$0")/environment.sh"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-85}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-/tmp/wildlife-v04-fleet-logs}"
export GZ_PARTITION="${GZ_PARTITION:-wildlife-v04-fleet}"
source "$WILDLIFE_DEPS_DIR/PX4-Autopilot/build/px4_sitl_default/rootfs/gz_env.sh"
exec python3 "$WILDLIFE_WORKSPACE_DIR/scripts/run_px4_fleet.py" "$@"
