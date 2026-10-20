import {useEffect,useRef,useState} from 'react';
import {api,ApiError,artifactUrl,requestKey,terminal,type Artifact,type Job,type Manifest,type Revision} from './api';
import {designPdfLabel} from './downloads';

const labels:Record<string,string>={documents:'Measured design packet',stock:'Stock layout and cost',package:'Project ZIP'};
const stages:Record<string,string>={queued:'Queued',generating_documents:'Generating measured drawings',verifying_documents:'Checking document consistency',planning_stock:'Planning stock',packaging:'Packaging this artifact set',publishing:'Saving verified outputs'};
type Costs={rows:{stock_id:string;material_id:string;sheets_purchased:number;unit_price_usd:string|null;purchased_cost_usd:string|null;consumed_finished_value_usd:string|null}[];known_sheet_subtotal_usd:string;sheet_purchase_subtotal_usd:string|null;estimate_complete:boolean;project_total_usd:null;excluded_items:string[]};
type StockRecord={plan:{status:string;unplaced_instance_ids:string[];costs:Costs}};

export function ProjectOutputs({revision,manifest,disabled,promotedFiles,onActiveChange,onCompleted}:{revision:Revision;manifest:Manifest;disabled:boolean;promotedFiles:Artifact[];onActiveChange:(value:boolean)=>void;onCompleted:()=>Promise<void>}){
  const [job,setJob]=useState<Job|null>(null);
  const [zip,setZip]=useState<string|null>(null);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(true);
  const [recoveryNeeded,setRecoveryNeeded]=useState(false);
  const mounted=useRef(false);
  const pendingRequest=useRef<{path:string;body:Record<string,string>}|null>(null);
  const activityChange=useRef(onActiveChange);activityChange.current=onActiveChange;
  const [stockSummary,setStockSummary]=useState<StockRecord|null>(null);
  const active=!!job&&!terminal(job.state);
  useEffect(()=>{mounted.current=true;void recover();return()=>{mounted.current=false;activityChange.current(false);};},[revision.id]);
  useEffect(()=>{setStockSummary(null);const artifact=manifest.artifacts.find(a=>a.relative_path==='stock-layout.json');if(!artifact)return;let stopped=false;void api<StockRecord>('/artifacts/'+encodeURIComponent(artifact.artifact_id)+'/download').then(value=>{if(!stopped)setStockSummary(value);}).catch(value=>{if(!stopped)setError(value instanceof Error?value.message:'The stock summary could not be read.');});return()=>{stopped=true;};},[manifest.artifact_set_id]);
  useEffect(()=>{
    if(!job||terminal(job.state))return;
    let stopped=false;
    const timer=setTimeout(async()=>{try{
      const result=await api<{job:Job}>('/jobs/'+encodeURIComponent(job.id));
      if(stopped)return;
      await receive(result.job);
    }catch(value){if(!stopped){setError(value instanceof Error?value.message:'Output status is unavailable.');setJob(previous=>previous?{...previous}:previous);}}},1000);
    return()=>{stopped=true;clearTimeout(timer);};
  },[job,onCompleted]);
  async function receive(result:Job){
    setJob(result);
    if(result.state==='succeeded'){
      try{if(result.kind==='package')setZip(result.result_artifact_id||null);else await onCompleted();}
      finally{activityChange.current(false);}
    }else if(terminal(result.state))activityChange.current(false);
  }
  async function recover(){
    setBusy(true);activityChange.current(true);
    try{
      const {jobs}=await api<{jobs:Job[]}>('/revisions/'+encodeURIComponent(revision.id));
      if(!mounted.current)return;
      const running=jobs.find(j=>j.revision_id===revision.id&&['documents','stock','package'].includes(j.kind||'')&&!j.idempotency_key?.startsWith('plans:')&&!terminal(j.state));
      setJob(running||null);setRecoveryNeeded(false);setError('');activityChange.current(!!running);
    }catch{if(mounted.current){setRecoveryNeeded(true);setError('Saved output status could not be confirmed. Reconnect before starting another output.');}}
    finally{if(mounted.current)setBusy(false);}
  }
  async function queue(kind:'documents'|'stock'|'package'){
    const path='/revisions/'+encodeURIComponent(revision.id)+(kind==='package'?'/package':'/jobs');
    const body:Record<string,string>=kind==='package'?{idempotency_key:requestKey(),artifact_set_id:manifest.artifact_set_id}:{kind,idempotency_key:requestKey(),source_artifact_set_id:manifest.artifact_set_id};
    pendingRequest.current={path,body};await submit();
  }
  async function submit(){
    const request=pendingRequest.current;if(!request)return;
    setError('');setBusy(true);activityChange.current(true);
    try{
      const result=await api<{job:Job}>(request.path,request.body);
      if(!mounted.current)return;
      pendingRequest.current=null;setRecoveryNeeded(false);
      try{await receive(result.job);}catch{setError('Output saved. Reopen the project to refresh its files.');}
    }catch(value){
      if(!mounted.current)return;
      if(value instanceof ApiError&&value.status<500){pendingRequest.current=null;setRecoveryNeeded(false);activityChange.current(false);setError(value.message);}
      else{setRecoveryNeeded(true);setError((value instanceof Error?value.message+' ':'')+'Output submission could not be confirmed. Reconnect to the same request.');}
    }finally{if(mounted.current)setBusy(false);}
  }
  async function cancel(){if(job)try{const result=(await api<{job:Job}>('/jobs/'+encodeURIComponent(job.id)+'/cancel',{})).job;setJob(result);if(terminal(result.state))activityChange.current(false);}catch(value){setError(value instanceof Error?value.message:'Cancellation could not be confirmed.');}}
  const individualFiles=manifest.artifacts.filter(a=>!promotedFiles.some(p=>p.relative_path===a.relative_path));
  const pdf=individualFiles.find(a=>a.relative_path==='design-packet.pdf');
  const native=manifest.artifacts.filter(a=>a.kind==='pdf'&&a.definition_id);
  const stock=manifest.artifacts.find(a=>a.relative_path==='stock-layout.json');
  const cost=manifest.artifacts.find(a=>a.relative_path==='cost-estimate.json');
  const stockPdf=individualFiles.find(a=>a.relative_path==='stock-layout.pdf');
  const svg=manifest.artifacts.filter(a=>a.kind==='svg'&&a.relative_path.includes('stock'));
  return <section className="project-outputs" aria-label="Documents and project package">
    <div className="section-heading"><h2>Project packet <small>revision {revision.number}</small></h2><span className="output-state">{manifest.construction.status==='complete'?'Technical fabrication method complete':manifest.construction.status==='recipe_unselected'?'Construction method unselected':'Construction '+manifest.construction.status}</span></div>
    <p className="help">Drawings and packages use this saved revision. Physical construction review and site installation remain separate from dimensional checks.</p>
    {manifest.construction.recipe_id&&<p className="help">This template models nominal panel blanks. Planned drilling and fastening references are in the recipe packet; they are not machined holes in the CAD files.</p>}
    <details className="individual-outputs"><summary>Individual output tools</summary><div className="button-row"><button disabled={disabled||busy||active||recoveryNeeded} onClick={()=>void queue('documents')}>Generate measured PDF · revision {revision.number}</button><button disabled={disabled||busy||active||recoveryNeeded} onClick={()=>void queue('stock')}>Plan stock and cost · revision {revision.number}</button><button disabled={disabled||busy||active||recoveryNeeded} onClick={()=>void queue('package')}>Export project ZIP · revision {revision.number}</button></div></details>
    {error&&<p className="error" role="alert">{error}</p>}
    {recoveryNeeded&&<button disabled={busy} onClick={()=>void(pendingRequest.current?submit():recover())}>{pendingRequest.current?'Reconnect output':'Reconnect output status'}</button>}
    {job&&<div className="output-job" role="status"><span>{labels[job.kind||'']||'Outputs'}: {active?stages[job.stage]||'Working':job.state==='succeeded'?'complete':job.state==='failed'?'failed; prior outputs preserved':job.state}</span>{active&&<button disabled={job.state==='cancelling'} onClick={()=>void cancel()}>Cancel output job</button>}</div>}
    <div className="button-row output-links">{pdf&&<a href={artifactUrl(pdf.artifact_id)} download>{designPdfLabel(manifest)} · revision {revision.number}</a>}{zip&&<a data-testid="project-zip" href={artifactUrl(zip)} download>Download project ZIP · revision {revision.number}</a>}{stockPdf&&<a href={artifactUrl(stockPdf.artifact_id)} download>Stock layout and cut sequence PDF · revision {revision.number}</a>}{stock&&<a href={artifactUrl(stock.artifact_id)} download>Stock layout data</a>}{cost&&<a href={artifactUrl(cost.artifact_id)} download>Cost estimate data</a>}</div>
    {stockSummary&&<section className="purchase-summary" aria-label="Verified stock purchase estimate"><h3>{stockSummary.plan.status==='complete'?'Verified stock purchase':'Incomplete stock candidate'}</h3>{stockSummary.plan.unplaced_instance_ids.length>0&&<p className="notice">Unplaced: {stockSummary.plan.unplaced_instance_ids.join(', ')}. A sufficient purchase is not established.</p>}<div className="table-scroll" tabIndex={0}><table><caption>{stockSummary.plan.status==='complete'?'Whole sheets for the independently checked cut sequence.':'Partial layout only; counts below do not establish sufficient stock.'}</caption><thead><tr><th scope="col">Stock</th><th scope="col">Sheets</th><th scope="col">Unit price (USD)</th><th scope="col">Purchase (USD)</th><th scope="col">Finished-part allocation (USD)</th></tr></thead><tbody>{stockSummary.plan.costs.rows.map(row=><tr key={row.stock_id}><th scope="row">{row.stock_id}</th><td>{row.sheets_purchased}</td><td>{row.unit_price_usd??'Unknown'}</td><td>{row.purchased_cost_usd??'Unknown'}</td><td>{row.consumed_finished_value_usd??'Unknown'}</td></tr>)}</tbody></table></div><p data-testid="sheet-subtotal">{stockSummary.plan.costs.sheet_purchase_subtotal_usd!==null?'Sheet purchase subtotal: USD '+stockSummary.plan.costs.sheet_purchase_subtotal_usd:stockSummary.plan.costs.rows.some(r=>r.unit_price_usd!==null)?'Known sheet subtotal: USD '+stockSummary.plan.costs.known_sheet_subtotal_usd+'; remaining prices or layout are incomplete.':'Sheet purchase subtotal unknown. Enter the missing prices to calculate it.'}</p><p className="help">Full project total remains unknown. Hardware, finish, tax, shipping and tools are excluded. Finished-part allocation differs from whole-sheet purchase cost.</p></section>}
    {native.length>0&&<details><summary>Native metric part drawings</summary><ul>{native.map(a=><li key={a.artifact_id}><a href={artifactUrl(a.artifact_id)} download>{a.definition_id} · A4 landscape · millimeters</a></li>)}</ul></details>}
    {manifest.validation.stock_layout==='unplaceable'&&<p className="notice">Some blanks cannot fit the supplied stock. The geometry remains valid; this layout does not establish a sufficient sheet purchase.</p>}
    {svg.length>0&&<details><summary>Suggested stock diagrams</summary>{svg.map(a=><figure key={a.artifact_id}><img src={artifactUrl(a.artifact_id)} alt={'Verified stock layout for revision '+revision.number}/><figcaption><a href={artifactUrl(a.artifact_id)} download>Download {a.relative_path}</a></figcaption></figure>)}</details>}
    {manifest.construction.findings.length>0&&<details><summary>Construction findings</summary><ul>{manifest.construction.findings.map((finding,i)=><li key={i}>{finding}</li>)}</ul></details>}
  </section>;
}
