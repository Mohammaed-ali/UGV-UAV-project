import {useEffect,useState,type ReactNode} from 'react';
import {Compass,KeyRound} from 'lucide-react';

export default function AccessGate({children}:{children:ReactNode}){
  const [authorized,setAuthorized]=useState(false),[checking,setChecking]=useState(true),[key,setKey]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function login(value:string){
    const response=await fetch('/api/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:value})});
    const data=await response.json();
    if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Unable to connect. Check your access key.');
    history.replaceState(null,'',location.pathname+location.search);
    setKey('');setAuthorized(true);
  }
  useEffect(()=>{let cancelled=false;(async()=>{try{
    const response=await fetch('/api/session');
    // A previously started local physics server can finish its flight while the
    // separate, protected sharing gateway serves the new login endpoint.
    if(response.status===404&&['127.0.0.1','localhost','[::1]'].includes(location.hostname)){if(!cancelled)setAuthorized(true);return;}
    const status=await response.json();
    if(!response.ok)throw new Error(status.detail??'This simulation link is unavailable.');
    if(cancelled)return;
    const sharedKey=new URLSearchParams(location.hash.slice(1)).get('key');
    if(status.authorized){history.replaceState(null,'',location.pathname+location.search);setAuthorized(true);}
    else if(sharedKey)await login(sharedKey);
  }catch(e){if(!cancelled)setError((e as Error).message);}finally{if(!cancelled)setChecking(false);}})();return()=>{cancelled=true;};},[]);
  if(authorized)return children;
  return <main className="loading-screen access-screen"><div className="brand-mark"><Compass size={30}/></div><h1>Fieldlab</h1><p>{checking?'Connecting to your simulation…':'Connect to the live simulation'}</p>{!checking&&<form className="access-form" onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');try{await login(key);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}}><label htmlFor="access-key"><KeyRound size={15}/> Simulation access key</label><input id="access-key" type="password" autoComplete="current-password" value={key} onChange={e=>setKey(e.target.value)} required placeholder="Enter your private access key"/><button className="primary" disabled={busy}>{busy?'Connecting…':'Open Mission Studio'}</button></form>}{error&&<p role="alert" className="access-error">{error}</p>}<small>The host PC runs the physics. Your browser controls and views the mission.</small></main>;
}
