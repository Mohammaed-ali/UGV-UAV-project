#!/usr/bin/env python3
"""Record a gate after programmatic checks AND an explicitly supplied visual review."""
import argparse
import json
from pathlib import Path
from common import ROOT, TOOL, write_json, file_hash, utc_now
from validate_dataset import validate


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('gate',choices=['feasibility','smoke','pilot','audit','full'])
    p.add_argument('evidence');p.add_argument('--visual-review-note',required=True)
    args=p.parse_args();evidence=Path(args.evidence).resolve()
    if args.gate=='feasibility':
        r=json.loads((evidence/'report.json').read_text());a=json.loads((evidence/'alignment.json').read_text())
        if r['programmatic_alignment']!='PASSED' or a['status']!='PASSED' or r['benchmark']['accepted_frames']<20: raise RuntimeError('Feasibility/alignment failed')
        out=ROOT/'docs/dataset/evidence/feasibility.json'
        gate={k:r[k] for k in ('camera_sha256','asset_manifest_sha256','gazebo_version')}
    else:
        validation=validate(evidence)
        if validation['status']!='PASSED': raise RuntimeError('Validator failed: '+str(validation['errors'][:5]))
        count=validation['counts']['images'];minimum={'smoke':200,'pilot':2000,'audit':2000,'full':10000}[args.gate]
        if count<minimum: raise RuntimeError('Insufficient actual accepted frames')
        index=json.loads((evidence/'qa/preview_index.json').read_text())
        if len(index['previews'])<100: raise RuntimeError('100 representative previews required')
        if args.gate in ('audit','full'):
            audit=json.loads((evidence/'qa/annotation_audit.json').read_text())
            if audit['audited_frames']<300 or len(index['lowest_iou_frames'])<50: raise RuntimeError('300-frame audit and 50 lowest-IoU samples required')
        gate={'dataset_path':str(evidence),'validator':validation,'manifest_sha256':file_hash(evidence/'manifest.json')}
        out=ROOT/f'docs/dataset/evidence/{args.gate}_gate.json'
    gate.update(status='PASSED',visual_review=args.visual_review_note,review_timestamp=utc_now(),evidence_path=str(evidence))
    write_json(out,gate);print(str(out))


if __name__=='__main__': main()
