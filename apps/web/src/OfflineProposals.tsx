import {useEffect,useState} from 'react';
import {api,requestKey,type Project,type Revision} from './api';

type Change={field:string;value_mm?:string;value_count?:number};
type Proposal={id:string;base_revision_id:string;state:string;stale?:boolean;applied_revision_id?:string|null;diagnostic_code?:string|null;proposal:{applicable:boolean;response:{intent:string;explanation:string;changes:Change[];questions:{field:string;question:string}[]}}|null};
const fieldLabels:Record<string,string>={'dimensions.outside_width_mm':'Outside width','dimensions.outside_height_mm':'Outside height','dimensions.outside_depth_mm':'Outside depth','dimensions.fixed_shelf_count':'Fixed shelves'};
function previous(revision:Revision,field:string){const key=field.split('.')[1];return revision.spec.dimensions[key as keyof typeof revision.spec.dimensions];}

export function OfflineProposals({project,revision,disabled,onApplied}:{project:Project;revision:Revision;disabled:boolean;onApplied:(revision:Revision)=>Promise<void>}){
  const [enabled,setEnabled]=useState(false);
  const [text,setText]=useState('Make the width 36 in');
  const [record,setRecord]=useState<Proposal|null>(null);
  const [baseSnapshot,setBaseSnapshot]=useState<Revision|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  useEffect(()=>{if(!record)return;let stopped=false;void api<{proposal:Proposal}>('/proposals/'+encodeURIComponent(record.id)).then(value=>{if(!stopped)setRecord(value.proposal);}).catch(value=>{if(!stopped)setError(value instanceof Error?value.message:'Proposal status is unavailable.');});return()=>{stopped=true;};},[revision.id,record?.id]);
  async function propose(){setBusy(true);setError('');try{setRecord((await api<{proposal:Proposal}>('/projects/'+encodeURIComponent(project.id)+'/proposals',{base_revision_id:revision.id,text,idempotency_key:requestKey(),mode:'fake'})).proposal);setBaseSnapshot(revision);}catch(value){setError(value instanceof Error?value.message:'The demo proposal could not be checked.');}finally{setBusy(false);}}
  async function apply(){if(!record)return;setBusy(true);setError('');try{const result=await api<{revision:Revision}>('/proposals/'+encodeURIComponent(record.id)+'/apply',{expected_base_revision_id:record.base_revision_id});setRecord(previous=>previous?{...previous,state:'applied',applied_revision_id:result.revision.id}:previous);await onApplied(result.revision);}catch(value){setError(value instanceof Error?value.message:'The proposal could not be applied.');}finally{setBusy(false);}}
  const stale=!!record&&(record.stale||record.base_revision_id!==revision.id)&&!record.applied_revision_id;
  const response=record?.proposal?.response;
  return <section className="offline-proposals" aria-label="Offline proposal demo"><h2>Optional editing demo</h2><p className="help">Manual forms are the normal workflow. This deterministic offline demo uses no API key or paid provider and cannot run generated code.</p><label className="check-label"><input type="checkbox" checked={enabled} onChange={event=>setEnabled(event.target.checked)}/>Enable offline proposal demo</label>
    {enabled&&<><div className="field"><label htmlFor="proposal-text">Describe a supported change</label><textarea id="proposal-text" rows={2} maxLength={4000} value={text} onChange={event=>setText(event.target.value)}/><small>The demo recognizes outside-width edits; other measurements remain in the forms.</small></div><button disabled={busy||disabled||!text.trim()} onClick={()=>void propose()}>Review demo proposal</button>
      {error&&<p className="error" role="alert">{error}</p>}
      {record&&<div className="proposal-review" data-testid="proposal-review"><h3>Review before applying</h3>{response&&<p data-testid="proposal-explanation">{response.explanation}</p>}{response?.changes.map(change=><p key={change.field}>{fieldLabels[change.field]||'Supported parameter'}: {String(previous(baseSnapshot||revision,change.field))} → {change.value_mm??change.value_count} {change.value_mm?'mm':'shelves'}</p>)}{response?.questions.length? <ul>{response.questions.map((q,i)=><li key={i}>{q.question}</li>)}</ul>:null}
        {stale&&<p className="notice" role="status">This proposal is stale. The accepted revision changed; request and review a fresh proposal.</p>}
        {record.state==='failed'&&<p role="status">The demo response failed validation. Your accepted design remains unchanged.</p>}{record.state==='uncertain'&&<p role="status">The demo timed out. Your accepted design remains unchanged; manual editing is available.</p>}{record.applied_revision_id&&<p role="status">Proposal applied once. The new revision uses the ordinary deterministic CAD workflow.</p>}
        {record.proposal?.applicable&&<button disabled={busy||disabled||stale||!!record.applied_revision_id||record.state!=='ready'} onClick={()=>void apply()}>Apply reviewed proposal and generate</button>}
      </div>}
    </>}
  </section>;
}
