#!/usr/bin/env bash
set -e
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-87}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-/tmp/wildlife-v04-two-camera-logs}"
export GZ_PARTITION="${GZ_PARTITION:-wildlife-v04-two-camera}"
export WILDLIFE_RUN_DIR="${WILDLIFE_RUN_DIR:-/tmp/wildlife-v04-two-camera}"
export WILDLIFE_PX4_MODEL=gz_x500_mono_cam_down
export WILDLIFE_PX4_AUTOSTART=4014
export WILDLIFE_UAV02_GZ_POSE=-10,0
model_dir="$(cd "$(dirname "$0")/../src/wildlife_simulation/models" && pwd)"
export GZ_SIM_RESOURCE_PATH="$model_dir:${GZ_SIM_RESOURCE_PATH:-}"
exec "$(dirname "$0")/start_px4_two.sh" px4_two_fusion.launch.py
