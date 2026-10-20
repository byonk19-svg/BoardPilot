import {useEffect,useRef,useState} from 'react';
import {api,artifactUrl,terminal,type Artifact,type Job,type Manifest,type Revision} from './api';
import {designPdfLabel} from './downloads';
import {discoverPlans,newPlans,planLabels,planSteps,preparePlans,type PlanCheckpoint,type ReadyPlans} from './planWorkflow';

export function Plans({revision,manifest,disabled,onActiveChange,onDownloadsChange,onCompleted}:{revision:Revision;manifest:Manifest;disabled:boolean;onActiveChange:(value:boolean)=>void;onDownloadsChange:(files:Artifact[])=>void;onCompleted:()=>Promise<void>}){
  const [run,setRun]=useState<PlanCheckpoint|null>(null);
  const [ready,setReady]=useState<ReadyPlans|null>(null);
  const [state,setState]=useState<'checking'|'idle'|'running'|'stopped'|'ready'>('checking');
  const [error,setError]=useState('');
  const [cancelling,setCancelling]=useState(false);
  const checkpoint=useRef<PlanCheckpoint|null>(null);
  const mounted=useRef(false),working=useRef(false),cancelled=useRef(false),cancelPending=useRef(false);
  const completed=useRef(onCompleted);completed.current=onCompleted;
  const activeChange=useRef(onActiveChange);activeChange.current=onActiveChange;
  const downloadsChange=useRef(onDownloadsChange);downloadsChange.current=onDownloadsChange;
  const progress=(next:PlanCheckpoint)=>{checkpoint.current=next;setRun(next);};
  async function drive(initial:PlanCheckpoint,retry=false,refresh=true){
    if(working.current)return;
    working.current=true;cancelled.current=false;setState('running');setError('');activeChange.current(true);
    try{
      const result=await preparePlans(revision.id,initial,progress,()=>mounted.current&&!cancelled.current,retry);
      if(!mounted.current)return;
      setReady(result);setState('ready');
      downloadsChange.current(result.manifest.artifacts.filter(a=>['design-packet.pdf','stock-layout.pdf'].includes(a.relative_path)));
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
    mounted.current=true;activeChange.current(true);
    void discoverPlans(revision.id).then(found=>{
      if(!mounted.current)return;
      if(!found){setState('idle');activeChange.current(false);return;}
      progress(found);
    }).catch(value=>{if(mounted.current){setState('stopped');setError(value instanceof Error?value.message:'Plans status could not be read.');}});
    return()=>{mounted.current=false;activeChange.current(false);downloadsChange.current([]);};
  },[revision.id]);
  useEffect(()=>{
    if(!disabled&&state==='checking'&&run&&!working.current)void drive(run,false,false);
  },[disabled,run,state]);
  async function start(){
    if(working.current||cancelPending.current)return;
    // After an unknown submission, this retained checkpoint resends the same key.
    // A reload reconstructs it from the persistent server job ledger instead.
    working.current=true;setState('checking');setError('');activeChange.current(true);
    let next:PlanCheckpoint|null=null;
    try{next=checkpoint.current||await discoverPlans(revision.id)||newPlans(manifest.artifact_set_id);}
    catch(value){if(mounted.current){setState('stopped');setError(value instanceof Error?value.message:'Plans status could not be read.');}}
    finally{working.current=false;}
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
  return <section id="plans" className="plans" aria-label="Get plans" tabIndex={-1}>
    <p className="help">Get this revision's PDFs, stock layout and cut list together in one ZIP. All files stay local.</p>
    <div className="button-row"><button className="primary" disabled={disabled||cancelling||state==='checking'||state==='running'} onClick={()=>void start()}>{state==='running'?'Preparing plans…':state==='stopped'?'Retry plans':'Get plans'} · revision {revision.number}</button>{state==='running'&&run?.job&&!terminal(run.job.state)&&<button disabled={cancelling||cancelled.current} onClick={()=>void cancel()}>Cancel plans</button>}</div>
    {(run||state==='checking')&&<div className="plans-progress" role="status" aria-label="Plans progress">{state==='checking'?'Checking saved plans…':state==='ready'?`Plans ready · revision ${revision.number}`:`${state==='stopped'?'Stopped at':'Preparing'} step ${index+1} of 3: ${planLabels[run!.step]} · revision ${revision.number}`}</div>}
    {run&&<ol className="plans-steps">{planSteps.map((step,i)=><li key={step} aria-current={i===index&&state!=='ready'?'step':undefined}>{planLabels[step]} <span>{state==='ready'||i<index?'complete':i===index?state==='stopped'?'stopped':'in progress':'waiting'}</span></li>)}</ol>}
    {error&&<p className="error" role="alert">{error}</p>}
    {ready&&<div className="button-row output-links" aria-label={'Plans downloads revision '+revision.number}>{[['design-packet.pdf',designPdfLabel(ready.manifest)],['stock-layout.pdf','Stock layout and cut sequence PDF']].map(([path,label])=>{const artifact=ready.manifest.artifacts.find(a=>a.relative_path===path);return artifact&&<a className={path==='design-packet.pdf'?'download':undefined} key={path} href={artifactUrl(artifact.artifact_id)} download>{label} · revision {revision.number}</a>;})}<a className="download" href={artifactUrl(ready.zipArtifactId)} download>Download plans ZIP · revision {revision.number}</a></div>}
  </section>;
}
