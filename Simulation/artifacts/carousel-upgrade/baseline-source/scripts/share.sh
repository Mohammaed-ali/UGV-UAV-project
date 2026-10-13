#!/usr/bin/env bash
set -eo pipefail
cd -- "$(dirname -- "$0")/.."
exec .venv/bin/python scripts/share.py
