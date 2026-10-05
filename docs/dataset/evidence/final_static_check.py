"""Repeat frozen V0.4 parse/launch/contract checks and parse offline tooling."""
import ast
from collections import Counter
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import yaml

sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/synthetic_dataset/scripts'))
from common import ROOT,TOOL,write_json,git_revision

baseline=subprocess.check_output(['git','ls-tree','-r','--name-only','v0.4-final'],cwd=ROOT,text=True).splitlines()

def check(names):
    counts=Counter()
    for name in names:
        path=ROOT/name
        if path.suffix=='.py': ast.parse(path.read_text(),filename=name);counts['python']+=1
        elif path.suffix in ('.xml','.sdf') or path.name=='model.config': ET.parse(path);counts['xml_sdf']+=1
        elif path.suffix in ('.yaml','.yml'): yaml.safe_load(path.read_text());counts['yaml']+=1
        elif path.suffix=='.sh': subprocess.run(['bash','-n',str(path)],check=True);counts['shell']+=1
    return dict(counts)

counts=check(baseline);extra=check([str(p.relative_to(ROOT)) for p in TOOL.rglob('*') if p.is_file() and '__pycache__' not in p.parts])
launches=[]
for name in baseline:
    if not name.endswith('.launch.py'): continue
    spec=importlib.util.spec_from_file_location('dataset_regression_launch_'+str(len(launches)),ROOT/name)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.generate_launch_description() is not None
    launches.append(name)
unchanged=subprocess.run(['git','diff','--exit-code','v0.4-final','--','src','scripts'],cwd=ROOT,capture_output=True,text=True).returncode==0
contracts=subprocess.run(['git','diff','--exit-code','v0.4-final','--','src/wildlife_interfaces'],cwd=ROOT,capture_output=True,text=True).returncode==0
versions={}
for path in (ROOT/'src').glob('*/package.xml'): versions[path.parent.name]=ET.parse(path).findtext('version')
passed=unchanged and contracts and len(versions)==9 and len(launches)==11
report={'status':'PASSED' if passed else 'FAIL','baseline_parsed_files':counts,'tooling_parsed_files':extra,
        'launches':launches,'runtime_src_and_scripts_unchanged_from_v04':unchanged,
        'typed_contracts_unchanged_from_v04':contracts,'package_versions':versions,
        'source_release_commit':git_revision('v0.4-final^{commit}'),'checked_revision':git_revision()}
write_json(ROOT/'docs/dataset/evidence/final_static.json',report)
print(json.dumps(report,indent=2));raise SystemExit(0 if passed else 1)
