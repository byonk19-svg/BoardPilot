import {useEffect,useState} from 'react';
import {terminal,type Job} from './api';

const stages:Record<string,string>={queued:'Queued',validating:'Checking dimensions',compiling:'Calculating parts',generating_geometry:'Generating CAD',generating_side_panels:'Building side panels',generating_horizontal_panels:'Building shelves, top and bottom',generating_back_panel:'Building the back panel',assembling_geometry:'Assembling panels',inspecting_geometry:'Checking saved geometry',verifying_artifacts:'Checking saved files',publishing:'Saving verified outputs'};

function failureDetail(job:Job,revision:number){
  const reason=job.diagnostic_code==='CAD_TIMEOUT'||job.diagnostic_code==='WORKER_TIMEOUT'?'The build reached its time limit.':job.diagnostic_code==='CAD_INSPECTION_FAILED'?'The saved geometry did not pass verification.':'The CAD worker stopped before verification finished.';
  return `${reason} Revision ${revision} is saved. Retry this revision to finish it; existing verified outputs remain available.`;
}

export function GenerationStatus({job,revision,submitting,connectionIssue,onCancel,onRetry}:{job:Job;revision:number;submitting:boolean;connectionIssue:boolean;onCancel:()=>void;onRetry:()=>void}){
  const active=!terminal(job.state);
  const [now,setNow]=useState(Date.now());
  useEffect(()=>{if(!active)return;setNow(Date.now());const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer);},[job.id,active]);
  const started=job.started_at?Date.parse(job.started_at):NaN;
  const end=active?now:job.finished_at?Date.parse(job.finished_at):NaN;
  const seconds=Number.isFinite(started)&&Number.isFinite(end)?Math.max(0,Math.floor((end-started)/1000)):null;
  const elapsed=seconds===null?'':seconds>=60?`${Math.floor(seconds/60)}m ${String(seconds%60).padStart(2,'0')}s`:`${seconds}s`;
  const timedOut=job.diagnostic_code==='CAD_TIMEOUT'||job.diagnostic_code==='WORKER_TIMEOUT';
  const title=submitting?'Submitting generation…':active?(job.state==='cancelling'?'Cancelling generation…':stages[job.stage]||'Working…'):job.state==='failed'&&timedOut?'Generation timed out':{succeeded:'Generation complete',failed:'Generation failed',cancelled:'Generation cancelled',interrupted:'Generation interrupted'}[job.state]||'Generation stopped';
  return <section className="job-status" role="status" aria-label="Generation status" aria-live="off">
    <div><strong aria-live="polite">{title}</strong>{elapsed&&<small data-testid="generation-elapsed"> · Elapsed {elapsed}</small>}
      {!active&&!submitting&&job.state==='failed'&&<p className="help">{failureDetail(job,revision)}</p>}
      {active&&connectionIssue&&<p className="help">Reconnecting to generation status. Your accepted revision and saved outputs are safe.</p>}
    </div>
    {active&&<button onClick={onCancel} disabled={job.state==='cancelling'||submitting}>Cancel generation</button>}
    {!active&&job.state!=='succeeded'&&<button onClick={onRetry} disabled={submitting}>Retry revision {revision}</button>}
  </section>;
}
