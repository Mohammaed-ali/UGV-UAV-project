#!/usr/bin/env bash
set -e
source "$(dirname "$0")/environment.sh"
cd "$WILDLIFE_WORKSPACE_DIR"
colcon build --base-paths src --symlink-install --parallel-workers 2
