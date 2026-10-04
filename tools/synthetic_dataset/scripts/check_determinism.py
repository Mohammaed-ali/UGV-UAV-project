#!/usr/bin/env python3
"""Compare independent Gazebo runs. Timing fields are measured, not deterministic."""
import argparse
import json
from pathlib import Path
from common import file_hash, write_json
from storage import committed_records


def normalized(record):
    return {k:v for k,v in record.items() if k not in
            ('simulation_timestamp','annotation_timestamp','timestamp_delta_s','scene_readback_timestamp',
             'settling_sim_seconds','generation_timestamp')}


def compare(a,b):
    a,b=Path(a),Path(b);ra,rb=committed_records(a),committed_records(b)
    errors=[];rgb_equal=0
    if len(ra)!=len(rb): errors.append('Frame counts differ')
    for x,y in zip(ra,rb):
        if normalized(x)!=normalized(y): errors.append('Scene/pose/label metadata differs: '+x['frame_id'])
        la=a/'labels'/x['split']/(x['frame_id']+'.txt');lb=b/'labels'/y['split']/(y['frame_id']+'.txt')
        if la.read_bytes()!=lb.read_bytes(): errors.append('YOLO bytes differ: '+x['frame_id'])
        ia=a/'images'/x['split']/(x['frame_id']+'.png');ib=b/'images'/y['split']/(y['frame_id']+'.png')
        rgb_equal+=file_hash(ia)==file_hash(ib)
    if file_hash(a/'manifests/scenarios.csv')!=file_hash(b/'manifests/scenarios.csv'): errors.append('Scenario manifests differ')
    return {'status':'PASSED' if not errors else 'FAIL','frames':len(ra),'errors':errors,'rgb_identical_frames':rgb_equal,
            'rgb_bytes_identical':rgb_equal==len(ra),
            'comparison_note':'All scene/realized-pose/annotation metadata is compared. Wall time and measured simulation capture/settling timestamps are excluded; those depend on process scheduling.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run_a');p.add_argument('run_b');p.add_argument('--report',required=True)
    args=p.parse_args();r=compare(args.run_a,args.run_b);write_json(args.report,r);print(json.dumps(r,indent=2));return 0 if r['status']=='PASSED' else 1


if __name__=='__main__': raise SystemExit(main())
