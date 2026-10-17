import {useEffect,useRef,useState} from 'react';
import {api,artifactUrl,terminal,type Job,type Manifest,type Revision} from './api';
import {discoverPlans,newPlans,planLabels,planSteps,preparePlans,type PlanCheckpoint,type ReadyPlans} from './planWorkflow';

export function Plans({revision,manifest,disabled,onActiveChange,onCompleted}:{revision:Revision;manifest:Manifest;disabled:boolean;onActiveChange:(value:boolean)=>void;onCompleted:()=>Promise<void>}){
  const [run,setRun]=useState<PlanCheckpoint|null>(null);
  const [ready,setReady]=useState<ReadyPlans|null>(null);
  const [state,setState]=useState<'checking'|'idle'|'running'|'stopped'|'ready'>('checking');
  const [error,setError]=useState('');
  const [cancelling,setCancelling]=useState(false);
  const checkpoint=useRef<PlanCheckpoint|null>(null);
  const mounted=useRef(false),working=useRef(false),cancelled=useRef(false),cancelPending=useRef(false);
  const completed=useRef(onCompleted);completed.current=onCompleted;
  const activeChange=useRef(onActiveChange);activeChange.current=onActiveChange;
  const progress=(next:PlanCheckpoint)=>{checkpoint.current=next;setRun(next);};
  async function drive(initial:PlanCheckpoint,retry=false,refresh=true){
    if(working.current)return;
    working.current=true;cancelled.current=false;setState('running');setError('');activeChange.current(true);
    try{
      const result=await preparePlans(revision.id,initial,progress,()=>mounted.current&&!cancelled.current,retry);
      if(!mounted.current)return;
      setReady(result);setState('ready');
      if(refresh)try{await completed.current();}catch{setError('Plans are ready. The project view could not refresh; the downloads below use the verified plans set.');}
    }catch(value){
      if(mounted.current){
        setState('stopped');
        if(value instanceof DOMException&&value.name==='AbortError'){
          if(cancelPending.current)setError('Plans paused while cancellation is being confirmed. Completed files were preserved.');
        }else setError(value instanceof Error?value.message:'Plans could not be prepared. Earlier files were preserved.');
      }
    }finally{working.current=false;if(mounted.current&&!cancelPending.current)activeChange.current(false);}
  }
  useEffect(()=>{
    mounted.current=true;
    void discoverPlans(revision.id).then(found=>{
      if(!mounted.current)return;
      if(!found){setState('idle');return;}
      progress(found);void drive(found,false,false);
    }).catch(value=>{if(mounted.current){setState('stopped');setError(value instanceof Error?value.message:'Plans status could not be read.');}});
    return()=>{mounted.current=false;};
  },[revision.id]);
  async function start(){
    if(working.current||cancelPending.current)return;
    // After an unknown submission, this retained checkpoint resends the same key.
    // A reload reconstructs it from the persistent server job ledger instead.
    working.current=true;setState('checking');setError('');activeChange.current(true);
    let next:PlanCheckpoint|null=null;
    try{next=checkpoint.current||await discoverPlans(revision.id)||newPlans(manifest.artifact_set_id);}
    catch(value){if(mounted.current){setState('stopped');setError(value instanceof Error?value.message:'Plans status could not be read.');}}
    finally{working.current=false;if(mounted.current)activeChange.current(false);}
    if(next&&mounted.current){progress(next);await drive(next,true);}
  }
  async function cancel(){
    const job=checkpoint.current?.job;if(!job||terminal(job.state)||cancelPending.current||cancelled.current)return;
    // Stop advancing immediately, independently of the cancellation response.
    // Retry stays locked until this response can no longer affect a newer run.
    cancelled.current=true;cancelPending.current=true;setCancelling(true);setError('');
    try{await api<{job:Job}>('/jobs/'+encodeURIComponent(job.id)+'/cancel',{});if(mounted.current){if(!working.current)setState('stopped');setError('Plans stopped. Completed files were preserved.');}}
    catch{if(mounted.current){if(!working.current)setState('stopped');setError('Plans paused. Cancellation could not be confirmed. Retry plans to check the existing job.');}}
    finally{cancelPending.current=false;if(mounted.current){setCancelling(false);if(!working.current)activeChange.current(false);}}
  }
  const index=run?planSteps.indexOf(run.step):0;
  return <section className="plans" aria-label="Get plans">
    <p className="help">Get measured drawings, a stock layout and the cut list together in one ZIP for saved revision {revision.number}.</p>
    <div className="button-row"><button className="primary" disabled={disabled||cancelling||state==='checking'||state==='running'} onClick={()=>void start()}>{state==='running'?'Preparing plans…':state==='stopped'?'Retry plans':'Get plans'} · revision {revision.number}</button>{state==='running'&&run?.job&&!terminal(run.job.state)&&<button disabled={cancelling||cancelled.current} onClick={()=>void cancel()}>Cancel plans</button>}</div>
    {(run||state==='checking')&&<div className="plans-progress" role="status" aria-label="Plans progress">{state==='checking'?'Checking saved plans…':state==='ready'?`Plans ready · revision ${revision.number}`:`${state==='stopped'?'Stopped at':'Preparing'} step ${index+1} of 3: ${planLabels[run!.step]} · revision ${revision.number}`}</div>}
    {run&&<ol className="plans-steps">{planSteps.map((step,i)=><li key={step} aria-current={i===index&&state!=='ready'?'step':undefined}>{planLabels[step]} <span>{state==='ready'||i<index?'complete':i===index?state==='stopped'?'stopped':'in progress':'waiting'}</span></li>)}</ol>}
    {error&&<p className="error" role="alert">{error}</p>}
    {ready&&<div className="button-row output-links" aria-label={'Plans downloads revision '+revision.number}><a className="download" href={artifactUrl(ready.zipArtifactId)} download>Download plans ZIP · revision {revision.number}</a>{[['design-packet.pdf','Plans measured PDF'],['stock-layout.pdf','Plans stock layout PDF'],['cut-list.csv','Plans cut list CSV']].map(([path,label])=>{const artifact=ready.manifest.artifacts.find(a=>a.relative_path===path);return artifact&&<a key={path} href={artifactUrl(artifact.artifact_id)} download>{label} · revision {revision.number}</a>;})}</div>}
  </section>;
}
