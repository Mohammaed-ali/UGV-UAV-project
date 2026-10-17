import {useEffect,useState} from 'react';
import type {Mission,Snapshot} from './types';

export default function CloseApproach({mission,snapshot,busy,action}:{mission:Mission;snapshot:Snapshot;busy:boolean;action:(name:string,target?:string,clearance?:number)=>void}){
  const [distance,setDistance]=useState(String(mission.approach_clearance??.5));
  useEffect(()=>setDistance(String(mission.approach_clearance??.5)),[snapshot.run_id,mission.approach_clearance]);
  const close=snapshot.tracking.close_approach;
  const active=!!close&&['APPROACHING','HOLDING','RETREATING'].includes(close.state);
  const target=snapshot.catalogue.find(t=>t.id===snapshot.tracking.target_id);
  const drone=snapshot.drones.find(d=>d.id===snapshot.tracking.drone_id);
  const value=Number(distance),valid=distance.trim()!==''&&Number.isFinite(value)&&value>=.5&&value<=10;
  const locked=snapshot.state==='TRACKING'&&snapshot.tracking.state==='TRACKING'&&!snapshot.hold&&!snapshot.physics.paused;
  const fresh=target&&target.age<=.5&&!target.ambiguous&&target.drone===snapshot.tracking.drone_id&&target.identity_confidence>=mission.reacquire_confidence;
  const canClose=locked&&fresh&&drone?.state==='TARGET_TRACKING'&&!active;
  return <section className="close-approach" aria-label="Close approach">
    <div className="close-heading"><b>Close in on tracked target</b><span>{active?close!.state.toLowerCase().replaceAll('_',' '):'Overhead approach'}</span></div>
    <p>{snapshot.tracking.target_id?<>Aircraft {snapshot.tracking.drone_id?.toUpperCase()} → <b>{snapshot.tracking.target_id}</b></>:'Start tracking a camera target to enable close approach.'}</p>
    <label className="numeric-label"><span>Minimum aircraft-to-surface clearance</span><div className="number-wrap"><input aria-label="Minimum close-approach clearance" type="number" min={.5} max={10} step={.05} value={distance} disabled={busy||active} onChange={e=>setDistance(e.target.value)}/><small>m</small></div></label>
    {!valid&&<small className="warn">Enter a clearance from 0.50 to 10.00 m.</small>}
    <div className="close-metrics"><span>Requested minimum <b>{(active?close!.requested_clearance_m:value||.5).toFixed(2)} m</b></span><span>Depth clearance <b>{close?.measured_clearance_m!=null?close.measured_clearance_m.toFixed(2)+' m':'Waiting for range'}</b></span></div>
    <div className="target-actions"><button className="primary compact" aria-label="Close in above tracked target" disabled={busy||!canClose||!valid} onClick={()=>action('approach_start',undefined,value)}>Close in from above</button><button className="secondary compact" disabled={busy||!active||close?.state==='RETREATING'} onClick={()=>action('approach_stop')}>Back off to tracking</button></div>
    <small>The 0.50 m starting value is adjustable for visual review. Gap is measured from a 0.50 m aircraft radius (rotors and gear) to surfaces seen by downward depth; the controller reserves an extra 0.25 m.</small>
    <small>Close hold only. No spraying or delivery is performed.</small>
    {close?.reason&&<p role="status">{close.reason}</p>}
    {!active&&snapshot.state==='TRACKING'&&!fresh&&<small>Waiting for a fresh, unambiguous view from the tracking aircraft.</small>}
  </section>;
}
