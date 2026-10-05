"""Run the existing project checks sequentially and preserve each exit status/log."""
import json
import os
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'docs/dataset/evidence'
steps = [
    ('prerequisites', 'scripts/check_prereqs.sh'),
    ('build', 'scripts/build_ros.sh'),
    ('tests', 'source scripts/environment.sh\ncolcon test --base-paths src --executor sequential'),
    ('test_results', 'source scripts/environment.sh\ncolcon test-result --verbose'),
]
env = dict(os.environ, ROS_LOG_DIR='/tmp/wildlife-v05-ros-logs')
report = {'status': 'RUNNING', 'started_utc': datetime.now(timezone.utc).isoformat(),
          'ros_log_dir': env['ROS_LOG_DIR'], 'steps': []}
path = EVIDENCE / 'final_regression_execution.json'
for name, command in steps:
    logfile = EVIDENCE / f'final_{name}.log'
    print(f'Running {name}: {command}', flush=True)
    started = time.monotonic()
    with logfile.open('w') as output:
        result = subprocess.run(['bash', '-c', 'set -e\n' + command], cwd=ROOT,
                                env=env, stdout=output, stderr=subprocess.STDOUT)
    report['steps'].append({'name': name, 'command': command, 'log': str(logfile.relative_to(ROOT)),
                            'exit_code': result.returncode, 'elapsed_s': time.monotonic() - started})
    report['status'] = 'RUNNING' if result.returncode == 0 else 'FAILED'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(f'{name}: exit {result.returncode}', flush=True)
    if result.returncode:
        print(logfile.read_text()[-5000:], flush=True)
        raise SystemExit(result.returncode)
report.update(status='PASSED', finished_utc=datetime.now(timezone.utc).isoformat())
path.write_text(json.dumps(report, indent=2) + '\n')
print(path, flush=True)
