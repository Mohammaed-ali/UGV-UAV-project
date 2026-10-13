#!/usr/bin/env bash
FIELDLAB_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export FIELDLAB_ROOT
export FIELDLAB_DEPS="${FIELDLAB_DEPS:-/home/mohammed-ali/Downloads/wildlife_px4_dependencies}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-93}"
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export ROS_LOG_DIR="$FIELDLAB_ROOT/.runtime/ros-logs"
export GZ_PARTITION="${GZ_PARTITION:-fieldlab-independent-93}"
export GZ_IP=127.0.0.1
export GZ_LOG_PATH="$FIELDLAB_ROOT/.runtime/gazebo-logs"
export GZ_FUEL_CACHE_PATH="$FIELDLAB_ROOT/.runtime/fuel"
export PYTHONPYCACHEPREFIX="$FIELDLAB_ROOT/.runtime/pycache"
export PYTHONUNBUFFERED=1
export DRI_PRIME="${DRI_PRIME:-0}"
source /opt/ros/jazzy/setup.bash
if [[ -f "$FIELDLAB_DEPS/msgs-install/setup.bash" ]]; then source "$FIELDLAB_DEPS/msgs-install/setup.bash"; fi
export PATH="$FIELDLAB_DEPS/agent-build:$PATH"
export LD_LIBRARY_PATH="$FIELDLAB_DEPS/agent-build:${LD_LIBRARY_PATH:-}"
export GZ_SIM_RESOURCE_PATH="$FIELDLAB_ROOT/assets/models:$FIELDLAB_DEPS/PX4-Autopilot/Tools/simulation/gz/models:${GZ_SIM_RESOURCE_PATH:-}"
export GZ_SIM_SYSTEM_PLUGIN_PATH="$FIELDLAB_DEPS/PX4-Autopilot/build/px4_sitl_default/src/modules/simulation/gz_plugins:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
unset GZ_SIM_SERVER_CONFIG_PATH
