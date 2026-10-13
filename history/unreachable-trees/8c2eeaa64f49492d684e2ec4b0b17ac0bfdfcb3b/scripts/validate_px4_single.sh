#!/usr/bin/env bash
set -e
source "$(dirname "$0")/environment.sh"
cd "$WILDLIFE_WORKSPACE_DIR"
python3 tests/run_px4_acceptance.py no-target
python3 tests/run_px4_acceptance.py target
python3 - <<'PY'
import json
from pathlib import Path
base=Path('docs/validation')
assert all(json.loads((base/name).read_text())['result']=='PASS' for name in ('px4_no_target.json','px4_target.json'))
gate=base/'px4_acceptance.json'
status=json.loads(gate.read_text()) if gate.exists() else {}
status['one_uav']='PASS'
status.setdefault('two_uav','NOT_TESTED')
status.setdefault('eight_structural','NOT_TESTED')
status.setdefault('eight_uav','NOT_TESTED')
gate.write_text(json.dumps(status,indent=2)+'\n')
print('One-UAV acceptance passed; existing fleet gate results preserved.')
PY
