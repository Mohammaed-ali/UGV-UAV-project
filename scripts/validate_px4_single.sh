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
(base/'px4_acceptance.json').write_text(json.dumps({'one_uav':'PASS','two_uav':'NOT_TESTED','eight_uav':'NOT_TESTED'},indent=2)+'\n')
print('One-UAV acceptance passed; two/eight-UAV flight remains untested.')
PY
