"""Compare read-only original-workspace state with the snapshot taken before this build."""
import hashlib,json,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
baseline=json.loads((root/'artifacts/primary-baseline.json').read_text());primary=Path(baseline['primary'])
changed=[]
for relative,digest in baseline['files'].items():
    p=primary/relative
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:changed.append(relative)
status=subprocess.check_output(['git','status','--porcelain'],cwd=primary,env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'},text=True)
report={'primary':str(primary),'checked_files':len(baseline['files']),'changed_files':changed,'git_status_matches':status==baseline['git_status'],'passed':not changed and status==baseline['git_status']}
(root/'artifacts/primary-preservation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
