#!/usr/bin/env bash
set -eo pipefail
source "$(dirname -- "$0")/environment.sh"
cd "$FIELDLAB_ROOT"
if [[ ! -x .venv/bin/python ]]; then printf '%s\n' 'Run scripts/setup.sh first.'; exit 1; fi
if [[ ! -f dist/index.html ]]; then printf '%s\n' 'Build the frontend using pnpm build first.'; exit 1; fi
mkdir -p .runtime artifacts/runs
printf '%s\n' 'Fieldlab: http://127.0.0.1:8765' 'Use Initialize simulation in the browser to start the isolated Gazebo/PX4 runtime.'
exec .venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port "${FIELDLAB_PORT:-8765}" --no-access-log --no-proxy-headers
