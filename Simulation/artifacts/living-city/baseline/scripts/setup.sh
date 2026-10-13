#!/usr/bin/env bash
set -eo pipefail
FIELDLAB_SETUP_ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$FIELDLAB_SETUP_ROOT"
FIELDLAB_BUNDLED_NODE="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin"
if ! command -v node >/dev/null && [[ -x "$FIELDLAB_BUNDLED_NODE/node" ]]; then export PATH="$FIELDLAB_BUNDLED_NODE:$PATH"; fi
if ! command -v node >/dev/null || ! command -v pnpm >/dev/null; then printf '%s\n' 'Node.js and pnpm are required to rebuild the frontend.'; exit 1; fi
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt
export pnpm_config_store_dir=/tmp/fieldlab-pnpm-store
CI=true pnpm install --frozen-lockfile
pnpm --config.verify-deps-before-run=false build
printf '%s\n' 'Setup complete. Run scripts/start.sh.'
