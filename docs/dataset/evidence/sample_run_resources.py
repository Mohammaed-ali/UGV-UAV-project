"""Read-only samples of the currently owned dataset processes, never other sims."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/synthetic_dataset/scripts'))
from common import utc_now, write_json

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('dataset'); p.add_argument('report'); args = p.parse_args()
root = Path(args.dataset)
owned = sorted(root.glob('runtime/*/owned_processes.json'))
if not owned: raise SystemExit('No owned process record yet')
ownership = json.loads(owned[-1].read_text())
rows = subprocess.check_output(['ps', '-eo', 'pid,ppid,pgid,pcpu,rss,comm'], text=True).splitlines()[1:]
processes = []
for line in rows:
    pid, ppid, pgid, cpu, rss, command = line.split(maxsplit=5)
    if int(pgid) == ownership['gazebo_pgid'] or int(pid) in (ownership['generator_pid'], ownership['service_worker_pid']):
        processes.append({'pid': int(pid), 'ppid': int(ppid), 'pgid': int(pgid),
                          'cpu_percent_lifetime': float(cpu), 'rss_kib': int(rss), 'command': command})
out = Path(args.report)
report = json.loads(out.read_text()) if out.exists() else {'note': 'Process lifetime CPU percentages, not instantaneous or whole-host CPU load.', 'samples': []}
report['samples'].append({'timestamp': utc_now(), 'completed_markers': len(list((root / '.state').glob('*.json'))),
                          'ownership': ownership, 'processes': processes})
write_json(out, report)
print(json.dumps(report['samples'][-1], indent=2))
