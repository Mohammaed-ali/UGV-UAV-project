"""Compare confirmation scheduling using recorded image-derived detections.

This is a replay of perception outputs, not a new physical-flight gate.
"""
import argparse,json,tempfile,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.config import Mission
from backend.mission import Engine

def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args()
    mission=Mission.model_validate_json((a.directory/'mission.json').read_text())
    vision=SimpleNamespace(latest={},object_latest={},confidence=mission.confidence)
    gz=SimpleNamespace(sim_time=0.,camera=lambda *args:None)
    runtime=SimpleNamespace(gz=gz,state='offline')
    with tempfile.TemporaryDirectory() as temporary:
        engine=Engine(Path(temporary),runtime,vision);engine.configure(mission)
        report={d:{'first_matching_frame':None,'original_confirmation':None,'replay_confirmation':None} for s in mission.stops for d in s.drones}
        for line in (a.directory/'telemetry.jsonl').open():
            row=json.loads(line);gz.sim_time=row['sim_time']
            for captured in row['drones']:
                did=captured['id']
                if did not in report:continue
                output=report[did]
                if captured.get('target') and output['original_confirmation'] is None:
                    output['original_confirmation']=captured['target']['time']
                if captured['state'] not in ('TAKEOFF','SEARCHING','OBSERVING'):continue
                obs=captured.get('vision')
                if not obs or gz.sim_time-obs['time']>1 or obs.get('sync_error',999)>.25:continue
                valid=[d for d in obs.get('detections',[]) if d['class']==mission.target_class and d['position'] is not None]
                if valid and output['first_matching_frame'] is None:output['first_matching_frame']=obs['time']
                vision.object_latest[did]=obs
                drone=engine.drones[did]
                if not drone.get('target'):
                    drone['state']='SEARCHING';engine.check_detection(drone,mission.stops[0])
                if drone.get('target') and output['replay_confirmation'] is None:
                    output['replay_confirmation']=drone['target']['time']
        for output in report.values():
            first=output['first_matching_frame']
            for label in ('original','replay'):
                confirmed=output[label+'_confirmation']
                output[label+'_delay_sim_seconds']=round(confirmed-first,3) if first is not None and confirmed is not None else None
        result={'source_run':json.loads((a.directory/'result.json').read_text())['run_id'],
                'kind':'Recorded image-detection replay; not physical-flight acceptance',
                'sampling_note':'Observer snapshots omit intermediate perception frames. Missing replay confirmation does not invalidate live confirmation; delay starts at the first recorded matching frame.',
                'drones':report}
        (a.directory/'target-confirmation-replay.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2))

if __name__=='__main__':main()
