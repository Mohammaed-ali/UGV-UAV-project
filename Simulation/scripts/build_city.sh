#!/usr/bin/env bash
set -eo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/environment.sh"
set -u
cmake -S "$FIELDLAB_ROOT/native" -B "$FIELDLAB_ROOT/.runtime/city-build" -DCMAKE_BUILD_TYPE=Release
cmake --build "$FIELDLAB_ROOT/.runtime/city-build" -j 2
