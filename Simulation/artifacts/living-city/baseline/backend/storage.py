"""Bound raw PX4 archive storage while retaining small audit summaries."""
import json,os,shutil,time
from pathlib import Path

def prune_run_archives(root,budget_mb=None):
    runs=Path(root)/'artifacts/runs';runs.mkdir(parents=True,exist_ok=True)
    budget=int(budget_mb if budget_mb is not None else os.environ.get('FIELDLAB_ARCHIVE_MB','512'))*1024**2
    folders=sorted((p for p in runs.glob('fieldlab-sitl-*') if p.is_dir() and not p.is_symlink()),key=lambda p:p.stat().st_mtime)
    sizes={p:sum(f.stat().st_size for f in p.rglob('*') if f.is_file()) for p in folders}
    total=sum(sizes.values());removed=[]
    for folder in folders:
        if total<=budget:break
        # Only this runtime's disposable native flight log / parameter archives.
        files=[p for p in folder.rglob('*') if p.is_file()]
        if any(p.is_symlink() or p.suffix not in ('.ulg','.bson') for p in files):continue
        summary={'archive':folder.name,'removed_at':time.time(),'bytes':sizes[folder],
                 'reason':'Raw flight-log archive quota','files':[str(p.relative_to(folder)) for p in files]}
        (runs/(folder.name+'.summary.json')).write_text(json.dumps(summary,indent=2))
        shutil.rmtree(folder);total-=sizes[folder];removed.append(folder.name)
    return {'budget_bytes':budget,'retained_bytes':total,'removed':removed}
