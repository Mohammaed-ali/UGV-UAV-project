#!/usr/bin/env bash
WILDLIFE_WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WILDLIFE_DEPS_DIR="${WILDLIFE_DEPS_DIR:-/home/mohammed-ali/Downloads/wildlife_px4_dependencies}"
source /opt/ros/jazzy/setup.bash
if [[ -f "$WILDLIFE_DEPS_DIR/msgs-install/setup.bash" ]]; then
  source "$WILDLIFE_DEPS_DIR/msgs-install/setup.bash"
fi
if [[ -f "$WILDLIFE_WORKSPACE_DIR/install/setup.bash" ]]; then
  source "$WILDLIFE_WORKSPACE_DIR/install/setup.bash"
fi
export PATH="$WILDLIFE_DEPS_DIR/agent-build:$PATH"
export LD_LIBRARY_PATH="$WILDLIFE_DEPS_DIR/agent-build:${LD_LIBRARY_PATH:-}"
export WILDLIFE_WORKSPACE_DIR WILDLIFE_DEPS_DIR
