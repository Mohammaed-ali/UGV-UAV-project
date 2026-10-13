import json
from backend.storage import prune_mission_logs

def test_trace_quota_preserves_current_run_and_audit_summary(tmp_path):
 runs=tmp_path/'artifacts/runs';runs.mkdir(parents=True)
 old=runs/'10000000-0000-0000-0000-000000000001.jsonl';active=runs/'10000000-0000-0000-0000-000000000002.jsonl'
 line=json.dumps({'state':'COMPLETE','padding':'x'*600000})+'\n'
 old.write_text(line);active.write_text(line);unrelated=runs/'important.jsonl';unrelated.write_text('retain')
 result=prune_mission_logs(tmp_path,keep=active.stem,budget_mb=1)
 assert old.name in result['removed'] and active.exists() and unrelated.read_text()=='retain'
 assert json.loads(old.with_suffix('.summary.json').read_text())['last_state']['state']=='COMPLETE'
