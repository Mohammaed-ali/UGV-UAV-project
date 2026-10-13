#!/usr/bin/env bash
set -e
source "$(dirname "$0")/environment.sh"
cmake -S "$WILDLIFE_DEPS_DIR/Micro-XRCE-DDS-Agent" -B "$WILDLIFE_DEPS_DIR/agent-build"   -DUAGENT_SUPERBUILD=OFF -DUAGENT_USE_SYSTEM_FASTDDS=ON   -DUAGENT_USE_SYSTEM_FASTCDR=ON -DUAGENT_P2P_PROFILE=OFF -DUAGENT_LOGGER_PROFILE=OFF
cmake --build "$WILDLIFE_DEPS_DIR/agent-build" -j2
