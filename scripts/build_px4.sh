#!/usr/bin/env bash
set -e
source "$(dirname "$0")/environment.sh"
source "$WILDLIFE_DEPS_DIR/px4-venv/bin/activate"
cd "$WILDLIFE_DEPS_DIR/PX4-Autopilot"
make px4_sitl_default -j2
