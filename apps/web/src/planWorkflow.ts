import {api,requestKey,terminal,type Job,type Manifest} from './api';

export const planSteps=['documents','stock','package'] as const;
export type PlanStep=typeof planSteps[number];
export const planLabels:Record<PlanStep,string>={documents:'Measured drawings',stock:'Stock layout',package:'Project ZIP'};
export type PlanCheckpoint={runId:string;step:PlanStep;attempt:number;sourceSetId:string;job:Job|null};
export type ReadyPlans={manifest:Manifest;zipArtifactId:string};
const keyFor=(run:PlanCheckpoint)=>`plans:${run.runId}:${run.step}:${run.attempt}`;

function checkJob(job:Job,revisionId:string,run:PlanCheckpoint){
  if(job.revision_id!==revisionId||job.kind!==run.step||job.source_artifact_set_id!==run.sourceSetId||job.idempotency_key!==keyFor(run)){
    throw new Error('The output job does not match this saved revision and frozen source. No further step was started.');
  }
}
export async function discoverPlans(revisionId:string):Promise<PlanCheckpoint|null>{
  const {jobs}=await api<{jobs:Job[]}>('/revisions/'+encodeURIComponent(revisionId));
  // The ledger returns newest first. The latest step contains its frozen source,
  // so recovery does not depend on earlier jobs remaining in the bounded listing.
  for(const job of jobs){
    const match=/^plans:([0-9a-f-]{36}):(documents|stock|package):(\d+)$/.exec(job.idempotency_key||'');
    if(!match)continue;
    const run:PlanCheckpoint={runId:match[1],step:match[2] as PlanStep,attempt:Number(match[3]),sourceSetId:job.source_artifact_set_id||'',job};
    checkJob(job,revisionId,run);
    if(!run.sourceSetId)throw new Error('The plans source could not be recovered. Existing files remain available.');
    return run;
  }
  return null;
}
export function newPlans(sourceSetId:string):PlanCheckpoint{return {runId:requestKey(),step:'documents',attempt:0,sourceSetId,job:null};}

async function frozenManifest(revisionId:string,setId:string,step:PlanStep){
  const result=await api<{artifact_set_id:string;manifest:Manifest}>('/revisions/'+encodeURIComponent(revisionId)+'/manifest?artifact_set_id='+encodeURIComponent(setId));
  const manifest=result.manifest;
  if(result.artifact_set_id!==setId||manifest.artifact_set_id!==setId||manifest.revision_id!==revisionId){
    throw new Error('The plans output does not match its saved revision and frozen artifact set.');
  }
  if(!manifest.capabilities.includes('documents')||manifest.validation.documents!=='passed'||!manifest.artifacts.some(a=>a.relative_path==='design-packet.pdf')){
    throw new Error('The measured drawings are incomplete. Existing files remain available.');
  }
  if(step!=='documents'&&(!manifest.capabilities.includes('stock_layout')||manifest.validation.stock_layout!=='passed'||!manifest.artifacts.some(a=>a.relative_path==='stock-layout.pdf'))){
    throw new Error('Stock layout is incomplete. Check the stock sheets in Advanced settings and update the design.');
  }
  return manifest;
}

export async function preparePlans(revisionId:string,initial:PlanCheckpoint,onProgress:(run:PlanCheckpoint)=>void,alive:()=>boolean,retry=false):Promise<ReadyPlans>{
  const guard=()=>{if(!alive())throw new DOMException('Plans paused.','AbortError');};
  let run={...initial};
  for(let index=planSteps.indexOf(run.step);index<planSteps.length;index++){
    guard();onProgress(run);
    // A known job is authoritative even if its acknowledgement or a poll was lost.
    if(run.job){
      run={...run,job:(await api<{job:Job}>('/jobs/'+encodeURIComponent(run.job.id))).job};guard();checkJob(run.job!,revisionId,run);
    }
    while(retry&&run.job?.state==='cancelling'){
      onProgress(run);await new Promise(resolve=>setTimeout(resolve,1000));guard();
      run={...run,job:(await api<{job:Job}>('/jobs/'+encodeURIComponent(run.job!.id))).job};guard();checkJob(run.job!,revisionId,run);
    }
    if(run.job&&terminal(run.job.state)&&run.job.state!=='succeeded'&&retry){
      run={...run,attempt:run.attempt+1,job:null};
    }
    retry=false;
    if(!run.job){
      guard();onProgress(run); // Retain the request identity before sending it.
      const body=run.step==='package'?{idempotency_key:keyFor(run),artifact_set_id:run.sourceSetId}:{kind:run.step,idempotency_key:keyFor(run),source_artifact_set_id:run.sourceSetId};
      const path='/revisions/'+encodeURIComponent(revisionId)+(run.step==='package'?'/package':'/jobs');
      run={...run,job:(await api<{job:Job}>(path,body)).job};guard();checkJob(run.job!,revisionId,run);onProgress(run);
    }
    while(!terminal(run.job!.state)){
      await new Promise(resolve=>setTimeout(resolve,1000));guard();
      run={...run,job:(await api<{job:Job}>('/jobs/'+encodeURIComponent(run.job!.id))).job};guard();checkJob(run.job!,revisionId,run);onProgress(run);
    }
    if(run.job!.state!=='succeeded')throw new Error(`${planLabels[run.step]} ${run.job!.state}${run.job!.diagnostic_code?' ('+run.job!.diagnostic_code+')':''}. Earlier completed files were preserved.`);
    const setId=run.step==='package'?run.sourceSetId:run.job!.result_artifact_set_id;
    if(!setId)throw new Error('The completed job has no verified output set. Earlier files were preserved.');
    const manifest=await frozenManifest(revisionId,setId,run.step);guard();
    if(run.step==='package'){
      if(!run.job!.result_artifact_id)throw new Error('The ZIP is not available yet. Earlier files were preserved.');
      return {manifest,zipArtifactId:run.job!.result_artifact_id!};
    }
    run={...run,step:planSteps[index+1],attempt:0,sourceSetId:setId,job:null};
  }
  throw new Error('The plans workflow could not be completed.');
}
