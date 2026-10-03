#!/usr/bin/env bash
set -e
source "$(dirname "$0")/environment.sh"
python3 -c 'from px4_msgs.msg import VehicleStatus; print("px4_msgs MESSAGE_VERSION:", VehicleStatus.MESSAGE_VERSION)'
for tool in ros2 colcon gz MicroXRCEAgent; do command -v "$tool"; done
for repo in PX4-Autopilot px4_msgs Micro-XRCE-DDS-Agent; do
  git -C "$WILDLIFE_DEPS_DIR/$repo" rev-parse HEAD
 done
[[ -x "$WILDLIFE_DEPS_DIR/PX4-Autopilot/build/px4_sitl_default/bin/px4" ]]
