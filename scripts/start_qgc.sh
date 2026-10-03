#!/usr/bin/env bash
set -e
source "$(dirname "$0")/environment.sh"
export XDG_CONFIG_HOME="${WILDLIFE_QGC_CONFIG_DIR:-/tmp/wildlife-qgc-config}"
export XDG_CACHE_HOME="${WILDLIFE_QGC_CACHE_DIR:-/tmp/wildlife-qgc-cache}"
export XDG_DATA_HOME="${WILDLIFE_QGC_DATA_DIR:-/tmp/wildlife-qgc-data}"
exec "$WILDLIFE_DEPS_DIR/QGroundControl-x86_64.AppImage" --appimage-extract-and-run --logging:Comms.LinkManager,Vehicle.MultiVehicleManager
