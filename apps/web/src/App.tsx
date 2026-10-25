import {useEffect,useRef,useState} from 'react';
import type {ProjectSpec,StockSheet} from './contracts';
import {Viewer} from './Viewer';
import {api,ApiError,ServiceUnavailableError,artifactUrl,requestKey,terminal,type Artifact,type Finding,type Job,type Manifest,type Project,type Revision,type Template} from './api';
import {changeSummary,displayUnit,formFrom,groupLabel,restoreForm,sameSpec,validateForm,type Form,type Unit,type Validated} from './forms';
import {ProjectOutputs} from './ProjectOutputs';
import {Plans} from './Plans';
import {AssemblyReadiness} from './AssemblyReadiness';
import {additionalRevisionFiles} from './downloads';
import {OfflineProposals} from './OfflineProposals';
import {ImportProject} from './ImportProject';
import {GenerationStatus} from './GenerationStatus';
import {formatMeasurement,formatDualMeasurement,fractionDenominators} from './measurements';

const partLabel:Record<string,string>={side_left:'Left side',side_right:'Right side',bottom:'Bottom',top:'Top',back:'Applied back',shelf_01:'Shelf 1',shelf_02:'Shelf 2',shelf_03:'Shelf 3',shelf_04:'Shelf 4'};
type SavedDraft={base_revision_id:string;raw:unknown};

class MissingProjectError extends Error {
  constructor(public projectId:string){super('This saved project is not available in this local store. Choose another saved project, try opening it again, or start a new bookcase.');}
}

// Browser storage is a recovery convenience; the local service owns revisions.
function cachedValue(key:string){try{return localStorage.getItem(key);}catch{return null;}}
function cacheValue(key:string,value:string){try{localStorage.setItem(key,value);}catch{/* Server records and in-memory drafts remain available. */}}
function forgetCachedValue(key:string){try{localStorage.removeItem(key);}catch{/* Storage may be disabled by the browser. */}}

export function App(){
  const [templates,setTemplates]=useState<Template[]>([]);
  const [projects,setProjects]=useState<Project[]>([]);
  const [project,setProject]=useState<Project|null>(null);
  const [accepted,setAccepted]=useState<Revision|null>(null);
  const [shown,setShown]=useState<Revision|null>(null);
  const [manifest,setManifest]=useState<Manifest|null>(null);
  const [form,setForm]=useState<Form|null>(null);
  const [baseId,setBaseId]=useState<string|null>(null);
  const [validated,setValidated]=useState<Validated|null>(null);
  const [findings,setFindings]=useState<Finding[]>([]);
  const [error,setError]=useState<Error|null>(null);
  const [notice,setNotice]=useState('');
  const [checking,setChecking]=useState(false);
  const [busy,setBusy]=useState(false);
  const [job,setJob]=useState<Job|null>(null);
  const [selected,setSelected]=useState<string[]>([]);
  const [draftSaved,setDraftSaved]=useState(false);
  const [unsupportedDraft,setUnsupportedDraft]=useState(false);
  const [advancedOpen,setAdvancedOpen]=useState(false);
  const [pollTick,setPollTick]=useState(0);
  const [submittingGeneration,setSubmittingGeneration]=useState(false);
  const [generationConnectionIssue,setGenerationConnectionIssue]=useState(false);
  const [planDownloads,setPlanDownloads]=useState<{revisionId:string;artifacts:Artifact[]}|null>(null);
  const [plansActivity,setPlansActivity]=useState<string|null>(null);
  const [outputActivity,setOutputActivity]=useState<string|null>(null);
  const generationRequest=useRef(false);
  const unconfirmedGeneration=useRef<{revisionId:string;key:string}|null>(null);
  const navigation=useRef(0);
  const validation=useRef(0);
  const projectRef=useRef<string|null>(null);
  const formRef=useRef<Form|null>(null);
  const localDrafts=useRef<Record<string,SavedDraft>>({});
  useEffect(()=>{formRef.current=form;},[form]);
  const active=!!job&&!terminal(job.state);
  const dirty=!!form&&(!accepted||!validated||!sameSpec(validated.spec,accepted.spec)||baseId!==accepted.id);
  const upToDate=!dirty&&!!accepted&&shown?.id===accepted.id&&manifest?.revision_id===accepted.id&&manifest?.validation.geometry==='passed';
  const unit:Unit=form?.spec.display.preferred_unit==='mm'?'mm':'in';
  const requestedPrecision=form?.spec.display.fraction_denominator;
  const precision=fractionDenominators.find(value=>value===requestedPrecision)||64;
  const savedPrecision=fractionDenominators.find(value=>value===shown?.spec.display.fraction_denominator)||64;
  const dimension=(mm:string)=>formatMeasurement(mm,unit,savedPrecision);
  const dualDimension=(mm:string)=>formatDualMeasurement(mm,unit,savedPrecision);
  useEffect(()=>{
    if(findings.some(({field})=>field.startsWith('manufacturing.')||field.startsWith('construction.')||field.startsWith('documents.')||field.endsWith('.nominal_label')||field.endsWith('.face_grain'))){
      setAdvancedOpen(true);
    }
  },[findings]);

  const failure=(value:unknown)=>{setError(value instanceof Error?value:new Error('This operation could not be completed.'));};
  function keepLocalDraft(id:string,raw:Form,base:string){const kept={base_revision_id:base,raw};localDrafts.current[id]=kept;cacheValue('woodwork-local-draft-'+id,JSON.stringify(kept));}
  function forgetLocalDraft(id:string){delete localDrafts.current[id];forgetCachedValue('woodwork-local-draft-'+id);}
  async function refreshProjects(){const response=await api<{projects:Project[]}>('/projects');setProjects(response.projects);}
  async function openProject(id:string,preserveDraft=false){
    const priorId=projectRef.current,priorForm=formRef.current,priorBase=baseId;
    const sequence=++navigation.current;projectRef.current=id;
    setError(null);setBusy(true);
    try{
      if(!preserveDraft&&priorId&&priorForm&&priorBase){
        try{await api('/projects/'+encodeURIComponent(priorId)+'/draft',{base_revision_id:priorBase,raw:priorForm},'PUT');forgetLocalDraft(priorId);}
        catch(value){keepLocalDraft(priorId,priorForm,priorBase);if(!(value instanceof ApiError)||![404,409].includes(value.status))throw value;}
      }
      const container=await api<{project:Project;draft:SavedDraft|null}>('/projects/'+encodeURIComponent(id)).catch(value=>{if(value instanceof ApiError&&value.status===404)throw new MissingProjectError(id);throw value;});
      const revision=await api<{revision:Revision;jobs?:Job[]}>('/revisions/'+encodeURIComponent(container.project.latest_accepted_revision_id));
      let saved:Revision|null=null,scene:Manifest|null=null;
      if(container.project.latest_successful_revision_id){
        saved=container.project.latest_successful_revision_id===revision.revision.id?revision.revision:(await api<{revision:Revision}>('/revisions/'+encodeURIComponent(container.project.latest_successful_revision_id))).revision;
        scene=(await api<{manifest:Manifest}>('/revisions/'+encodeURIComponent(saved.id)+'/manifest')).manifest;
        if(scene.revision_id!==saved.id)throw new Error('The saved model and revision do not agree. Generate this revision again.');
      }
      if(sequence!==navigation.current)return;
      setGenerationConnectionIssue(false);
      setProject(container.project);setAccepted(revision.revision);setShown(saved);setManifest(scene);
      const serverJob=revision.jobs?.find(j=>j.kind==='generate');
      if(serverJob&&(!preserveDraft||job?.revision_id!==revision.revision.id))setJob(serverJob);
      if(!preserveDraft){
        validation.current++;setValidated(null);setFindings([]);setChecking(true);
        setAdvancedOpen(false);
        let localDraft=localDrafts.current[id];if(!localDraft)try{localDraft=JSON.parse(cachedValue('woodwork-local-draft-'+id)||'null');}catch{/* A malformed recovery record does not replace a valid revision. */}
        const draft=localDraft||container.draft;
        const restored=restoreForm(draft?.raw);
        const next=restored||formFrom(revision.revision.spec);
        setUnsupportedDraft(!!container.draft&&!restored);
        setForm(next);formRef.current=next;setBaseId(restored?draft!.base_revision_id:revision.revision.id);
        setJob(null);setSelected([]);setNotice(restored&&draft?.base_revision_id!==revision.revision.id?'This draft started from an older revision. Your inputs are kept; review the latest saved design before applying.':'');
        if(container.draft&&!restored)setNotice('The saved draft format could not be restored. Your accepted revision remains available; the original draft is preserved until you edit.');
        if(serverJob)setJob(serverJob);
        else try{const tracked=JSON.parse(cachedValue('woodwork-job-'+id)||'null');if(tracked?.revision_id===revision.revision.id&&typeof tracked.job_id==='string'){const savedJob=await api<{job:Job}>('/jobs/'+encodeURIComponent(tracked.job_id));if(sequence===navigation.current)setJob(savedJob.job);}}catch{setNotice('Generation status could not be restored. The accepted revision and saved outputs remain available.');}
      }
      cacheValue('woodwork-last-project',id);
      try{await refreshProjects();}catch{setNotice('Project opened. The saved-project list could not be refreshed; your revision and generation controls remain available.');}
      return revision.revision;
    }catch(value){if(sequence===navigation.current){projectRef.current=priorId;failure(value);setJob(previous=>previous?{...previous}:previous);}}
    finally{if(sequence===navigation.current)setBusy(false);}
  }
  async function connect(){setError(null);setBusy(true);try{
    const response=await api<{templates:Template[]}>('/templates');setTemplates(response.templates);
    await refreshProjects();
    const remembered=cachedValue('woodwork-last-project');
    if(remembered){await openProject(remembered);}
    else if(response.templates.length){const next={...(formRef.current||formFrom(response.templates[0].default_spec))};setForm(next);formRef.current=next;}
  }catch(value){failure(value);}finally{setBusy(false);}}
  useEffect(()=>{void connect();},[]);

  function newProject(){if(projectRef.current&&formRef.current&&baseId)keepLocalDraft(projectRef.current,formRef.current,baseId);navigation.current++;validation.current++;projectRef.current=null;forgetCachedValue('woodwork-last-project');setProject(null);setAdvancedOpen(false);setAccepted(null);setShown(null);setManifest(null);setBaseId(null);setJob(null);setSelected([]);setNotice('');setError(null);setFindings([]);setValidated(null);setBusy(false);setUnsupportedDraft(false);if(templates[0]){const next=formFrom(templates[0].default_spec);setForm(next);formRef.current=next;}}
  function edit(next:Form){validation.current++;setForm(next);formRef.current=next;setValidated(null);setFindings([]);setChecking(true);setDraftSaved(false);setUnsupportedDraft(false);setError(null);setNotice('');}
  useEffect(()=>{
    if(!form)return;
    const sequence=++validation.current;
    setChecking(true);
    const timer=window.setTimeout(async()=>{try{const result=await validateForm(form);if(sequence===validation.current){setValidated(result);setFindings([]);}}
      catch(value){if(sequence===validation.current){setValidated(null);if(value instanceof ApiError){setFindings(value.findings.length?value.findings:[{field:'project',message:value.message}]);}else failure(value);}}
      finally{if(sequence===validation.current)setChecking(false);}},350);
    return()=>clearTimeout(timer);
  },[form]);
  useEffect(()=>{
    if(!form||!project||!baseId||unsupportedDraft)return;
    const id=project.id,raw=form,base=baseId;
    const timer=setTimeout(()=>{void api('/projects/'+encodeURIComponent(id)+'/draft',{base_revision_id:base,raw},'PUT').then(()=>{if(projectRef.current===id&&formRef.current===raw){forgetLocalDraft(id);setDraftSaved(true);}}).catch(value=>{if(projectRef.current===id&&formRef.current===raw){keepLocalDraft(id,raw,base);if(value instanceof ServiceUnavailableError){failure(value);setNotice('Draft kept here until the local service reconnects.');}else setNotice(value instanceof Error?'Draft could not be saved: '+value.message:'Draft could not be saved.');}});},700);
    return()=>clearTimeout(timer);
  },[form,project?.id,baseId,unsupportedDraft]);
  useEffect(()=>{setSelected(ids=>ids.filter(id=>manifest?.part_instances.some(i=>i.instance_id===id)));},[manifest]);

  async function generate(revision:Revision){
    if(generationRequest.current)return;
    generationRequest.current=true;setSubmittingGeneration(true);setBusy(true);setError(null);setNotice('');setGenerationConnectionIssue(false);
    const id=revision.project_id;
    const request=unconfirmedGeneration.current?.revisionId===revision.id?unconfirmedGeneration.current:{revisionId:revision.id,key:requestKey()};
    unconfirmedGeneration.current=request;
    async function remember(known:Job){
      unconfirmedGeneration.current=null;
      if(projectRef.current===id)setJob(known);
      cacheValue('woodwork-job-'+id,JSON.stringify({revision_id:revision.id,job_id:known.id}));
      if(known.state==='succeeded'&&projectRef.current===id)await openProject(id,true);
    }
    try{
      let known:Job;
      try{known=(await api<{job:Job}>('/revisions/'+encodeURIComponent(revision.id)+'/jobs',{kind:'generate',idempotency_key:request.key})).job;}
      catch(value){
        if(value instanceof ApiError&&value.status<500){unconfirmedGeneration.current=null;throw value;}
        // A lost response does not prove the POST failed. Reconnect by its key;
        // if the service is still unavailable, a manual retry reuses that key.
        let recovered:Job|undefined;
        try{recovered=(await api<{jobs:Job[]}>('/revisions/'+encodeURIComponent(revision.id))).jobs.find(j=>j.kind==='generate'&&j.idempotency_key===request.key);}catch{/* Retain the request identity until its outcome can be confirmed. */}
        if(recovered){await remember(recovered);return;}
        if(value instanceof ApiError)throw value;
        throw new Error('Generation request could not be confirmed. Your revision is saved. Retry to reconnect to the same request.');
      }
      await remember(known);
    }finally{generationRequest.current=false;setSubmittingGeneration(false);setBusy(false);}
  }
  async function apply(){
    if(!validated||checking||busy||active||upToDate)return;
    setBusy(true);setError(null);setNotice('');
    try{
      let revision:Revision;
      if(project&&baseId){
        if(!dirty&&accepted){revision=accepted;}
        else{revision=(await api<{revision:Revision}>('/projects/'+encodeURIComponent(project.id)+'/revisions',{base_revision_id:baseId,spec:validated.spec})).revision;}
      }else{
        const response=await api<{project:Project;revision:Revision}>('/projects',{title:validated.spec.project_name,spec:validated.spec});
        setProject(response.project);projectRef.current=response.project.id;revision=response.revision;cacheValue('woodwork-last-project',response.project.id);
      }
      forgetLocalDraft(revision.project_id);setAccepted(revision);setBaseId(revision.id);const next=formFrom(revision.spec);setForm(next);formRef.current=next;
      setProject(previous=>previous?{...previous,latest_accepted_revision_id:revision.id}:previous);
      setJob(null);await generate(revision);await refreshProjects();
    }catch(value){failure(value);if(value instanceof ApiError&&value.status===409)setNotice('This project changed since your draft began. Your draft is kept. Reopen the project to review the latest revision.');}
    finally{setBusy(false);}
  }
  useEffect(()=>{
    if(!job||terminal(job.state)||!project)return;
    const id=job.id,projectId=project.id,sequence=navigation.current;
    let stopped=false;
    let timer=setTimeout(async()=>{try{
      const response=await api<{job:Job}>('/jobs/'+encodeURIComponent(id));
      if(stopped||sequence!==navigation.current||projectRef.current!==projectId)return;
      setGenerationConnectionIssue(false);
      setJob(response.job);
      if(response.job.state==='succeeded'){const reopened=await openProject(projectId,true);if(projectRef.current===projectId&&reopened)setNotice(!response.job.revision_id||reopened.id===response.job.revision_id?`Verified model and downloads are saved for revision ${reopened.number}.`:'A previous revision finished. The latest accepted revision remains current.');}
      else if(response.job.state==='failed')setNotice('');
      else if(response.job.state==='cancelled')setNotice('Generation cancelled. The last successful model and downloads remain available.');
      else if(response.job.state==='interrupted')setNotice('Generation was interrupted. Your saved revisions are intact; retry to finish this design.');
    }catch{if(!stopped){setGenerationConnectionIssue(true);timer=setTimeout(()=>{if(!stopped)setPollTick(tick=>tick+1);},4000);}}},document.hidden?4000:1000);
    return()=>{stopped=true;clearTimeout(timer);};
  },[job,project?.id,pollTick]);

  async function cancelGeneration(){
    if(!job||!project)return;
    const sequence=navigation.current,projectId=project.id;
    try{const response=await api<{job:Job}>('/jobs/'+encodeURIComponent(job.id)+'/cancel',{});if(sequence===navigation.current&&projectRef.current===projectId)setJob(response.job);}catch(value){if(sequence===navigation.current)failure(value);}
  }

  async function applyProposalRevision(revision:Revision){
    forgetLocalDraft(revision.project_id);setAccepted(revision);setBaseId(revision.id);const next=formFrom(revision.spec);setForm(next);formRef.current=next;setValidated(null);
    setProject(previous=>previous?{...previous,latest_accepted_revision_id:revision.id}:previous);
    setJob(null);setNotice('Reviewed proposal saved as revision '+revision.number+'. The prior model remains labeled until CAD finishes.');
    await generate(revision);await refreshProjects();
  }
  async function importedProject(container:Project,revision:Revision){
    await openProject(container.id);setNotice('Imported as a new local project. Rebuilding its CAD from the installed template.');
    await generate(revision);
  }

  const urls:Record<string,string>={};for(const artifact of manifest?.artifacts||[])if(artifact.kind==='glb'&&artifact.definition_id)urls[artifact.definition_id]=artifactUrl(artifact.artifact_id);
  const promotedFiles=planDownloads&&planDownloads.revisionId===shown?.id?planDownloads.artifacts:[];
  const csv=manifest?.artifacts.find(a=>a.relative_path==='cut-list.csv');
  const canonical=manifest?.artifacts.find(a=>a.relative_path==='project.json');
  const assembly=manifest?.artifacts.find(a=>a.relative_path==='assembly.step');
  const measure=(field:string,label:string,hint?:string)=>{
    const measurement=form!.measurements[field];const fieldErrors=findings.filter(e=>e.field===field);const id=field.replaceAll('.','-');
    return <div className="field" key={field}><label htmlFor={id}>{label}</label><input id={id} aria-invalid={fieldErrors.length>0} aria-describedby={fieldErrors.length?id+'-error':hint?id+'-hint':undefined} inputMode="decimal" value={measurement?.text||''} onChange={event=>edit({...form!,measurements:{...form!.measurements,[field]:{text:event.target.value,default_unit:measurement.default_unit}}})}/>{hint&&<small id={id+'-hint'}>{hint}</small>}{fieldErrors.length>0&&<small className="field-error" id={id+'-error'}>{fieldErrors.map(e=>e.message).join(' ')}</small>}</div>;
  };
  const stockPrice=(stock:StockSheet,index:number)=>{
    const field=`manufacturing.stock_sheets.${index}.unit_price`,id='price-'+index;
    const fieldErrors=findings.filter(finding=>finding.field===field);
    return <div className="field"><label htmlFor={id}>Sheet {index+1} price (USD)</label><input id={id} aria-invalid={fieldErrors.length>0} aria-describedby={fieldErrors.length?id+'-error':undefined} inputMode="decimal" placeholder="Unknown" value={form!.prices[stock.stock_id]||''} onChange={event=>edit({...form!,prices:{...form!.prices,[stock.stock_id]:event.target.value}})}/>{fieldErrors.length>0&&<small className="field-error" id={id+'-error'}>{fieldErrors.map(finding=>finding.message).join(' ')}</small>}</div>;
  };
  function stockChange(index:number,key:'grain_axis'|'material_id',value:string){const next=structuredClone(form!);next.spec.manufacturing.stock_sheets[index][key]=value as 'length'|'none';edit(next);}
  function addStock(role:'main'|'back'){
    const next=structuredClone(form!);const stock:StockSheet={stock_id:'stock_'+requestKey().replaceAll('-','_'),material_id:next.spec.materials[role].material_id,length_mm:'2440',width_mm:'1220',grain_axis:'length',unit_price:null,currency:'USD'};
    next.spec.manufacturing.stock_sheets=[...next.spec.manufacturing.stock_sheets,stock] as ProjectSpec['manufacturing']['stock_sheets'];
    const i=next.spec.manufacturing.stock_sheets.length-1;for(const axis of ['length_mm','width_mm'] as const)next.measurements[`manufacturing.stock_sheets.${i}.${axis}`]={text:stock[axis]+' mm',default_unit:'mm'};next.prices[stock.stock_id]='';edit(next);
  }
  function removeStock(index:number){const next=structuredClone(form!);next.spec.manufacturing.stock_sheets=next.spec.manufacturing.stock_sheets.filter((_,i)=>i!==index) as ProjectSpec['manufacturing']['stock_sheets'];const old=form!.spec.manufacturing.stock_sheets;next.spec.manufacturing.stock_sheets.forEach((stock,i)=>{const previous=old.findIndex(s=>s.stock_id===stock.stock_id);for(const axis of ['length_mm','width_mm'])next.measurements[`manufacturing.stock_sheets.${i}.${axis}`]=form!.measurements[`manufacturing.stock_sheets.${previous}.${axis}`];});edit(next);}
  function chooseAssemblyMethod(){
    setAdvancedOpen(true);
    requestAnimationFrame(()=>document.getElementById('construction-recipe')?.focus());
  }
  const selectedRecipe=templates[0]?.recipes.find(recipe=>recipe.id===form?.spec.construction.recipe?.id&&recipe.version===form.spec.construction.recipe.version);
  const applyControls=<div className="apply-block"><AssemblyReadiness selected={!!form?.spec.construction.recipe} recipe={selectedRecipe} status={validated?.resolved.construction_status} checking={checking} dirty={dirty} unit={unit} precision={precision} downloadRevision={manifest?.artifacts.some(a=>a.relative_path==='design-packet.pdf')?shown?.number:undefined}/>{!form?.spec.construction.recipe&&<button type="button" onClick={chooseAssemblyMethod}>Choose assembly method</button>}<button className="primary" type="submit" aria-describedby="assembly-guide-status" disabled={!validated||checking||busy||active||upToDate}>{busy?'Saving…':active?'Updating design…':upToDate?'Up to date':project?'Update design':'Create design'}</button>{project&&dirty&&accepted&&<button className="revert-draft" type="button" onClick={()=>{const next=formFrom(accepted.spec);keepLocalDraft(project.id,next,accepted.id);edit(next);setBaseId(accepted.id);document.getElementById('dimensions-outside_width_mm')?.focus();}}>Revert draft</button>}{accepted&&baseId!==accepted.id&&<button type="button" onClick={()=>{if(project&&form)keepLocalDraft(project.id,form,accepted.id);setBaseId(accepted.id);setNotice('Draft now uses accepted revision '+accepted.number+' as its base. Review the change summary before applying.');}}>Use latest revision as base</button>}<small>{checking?'Checking your measurements…':draftSaved?'Draft saved locally.':project?'Edits are saved as a recoverable draft.':'No API key is needed.'}</small></div>;

  return <><header><span className="wordmark">Woodworking Planner</span><span className="muted">Local workshop · manual design</span></header>
    <div className="project-bar"><button onClick={newProject} disabled={!templates.length||busy}>New bookcase</button><label>Saved projects <select aria-label="Saved projects" disabled={busy} value={project?.id||''} onChange={event=>{if(event.target.value)void openProject(event.target.value);}}><option value="">Choose a project</option>{projects.map(item=><option key={item.id} value={item.id}>{item.title}</option>)}</select></label>{project&&<button disabled={busy} onClick={()=>void openProject(project.id)}>Reopen saved project</button>}<span className="service-label">AI disabled</span></div>
    <ImportProject onImported={importedProject}/>
    {shown&&<nav className="design-shortcuts" aria-label="Design sections"><a href="#measurements">Measurements</a><a href="#model-viewer">3D view</a><a href="#cut-list">Cut list</a><a href="#plans">Plans</a></nav>}
    <main className="workspace">
    {error&&<div className="error full-width" role="alert"><p>{error.message}</p><div className="button-row">{error instanceof MissingProjectError?<><button disabled={busy} onClick={()=>void openProject(error.projectId)}>Try opening project again</button><button disabled={busy||!templates.length} onClick={newProject}>Start a new bookcase</button></>:(error instanceof ServiceUnavailableError||!templates.length)&&<button disabled={busy} onClick={()=>void connect()}>Reconnect local service</button>}</div></div>}
    {!form?<section className="empty full-width"><h1>Plan a plywood bookcase</h1><p>{busy?'Connecting to the local design service…':error instanceof MissingProjectError?'Choose another saved project or start a new bookcase.':'Connect the local service to load the installed template and your saved projects.'}</p></section>:<>
    <aside id="measurements" className="parameters" aria-label="Bookcase parameters"><div className="section-heading"><h1>{project?'Edit bookcase':'New bookcase'}</h1></div>
      <form onSubmit={event=>{event.preventDefault();void apply();}}><fieldset className="editing-lock" disabled={busy}>
      <div className="field"><label htmlFor="project-name">Project name</label><input id="project-name" maxLength={100} value={form.spec.project_name} onChange={event=>edit({...form,spec:{...form.spec,project_name:event.target.value}})}/></div>
      <fieldset><legend>Outside dimensions</legend><p className="help">Depth includes the applied back. Enter units or use the selected default.</p>
      <div className="field"><label htmlFor="display-unit">Display units</label><select id="display-unit" disabled={checking} value={form.spec.display.preferred_unit} onChange={event=>edit(displayUnit(form,event.target.value as Unit,validated?.spec))}><option value="in">Inches</option><option value="mm">Millimeters</option></select></div>
      <div className="measurement-grid">{measure('dimensions.outside_width_mm','Outside width','Examples: 30 in, 30 1/2 in, 762 mm')}
      {measure('dimensions.outside_height_mm','Outside height')}{measure('dimensions.outside_depth_mm','Outside depth')}
      <div className="field"><label htmlFor="shelves">Fixed shelves</label><select id="shelves" value={form.spec.dimensions.fixed_shelf_count} onChange={event=>edit({...form,spec:{...form.spec,dimensions:{...form.spec.dimensions,fixed_shelf_count:Number(event.target.value)}}})}>{[0,1,2,3,4].map(n=><option key={n} value={n}>{n}</option>)}</select><small>Equal space between shelves.</small></div></div></fieldset>
      <fieldset><legend>Measured plywood</legend>
        <p className="help">Measure your panels; nominal stock labels do not set their thickness.</p>
        <div className="measurement-grid">{(['main','back'] as const).map(role=>measure(`materials.${role}.actual_thickness_mm`,`Actual ${role} thickness (mm)`))}</div>
      </fieldset>
      {applyControls}
      <details className="advanced-settings" open={advancedOpen} onToggle={event=>setAdvancedOpen(event.currentTarget.open)}>
        <summary>Advanced settings</summary><div className="details-body">
      <fieldset><legend>Material details</legend>{(['main','back'] as const).map(role=><div key={role} className="material-section">
        <div className="field"><label htmlFor={'nominal-'+role}>{role==='main'?'Main':'Back'} nominal label</label><input id={'nominal-'+role} maxLength={80} value={form.spec.materials[role].nominal_label} onChange={event=>{const next=structuredClone(form);next.spec.materials[role].nominal_label=event.target.value;edit(next);}}/><small>Label only; measured thickness stays unchanged.</small></div>
        <div className="field"><label htmlFor={'grain-'+role}>{role==='main'?'Main':'Back'} face grain</label><select id={'grain-'+role} value={form.spec.materials[role].face_grain} onChange={event=>{const next=structuredClone(form);next.spec.materials[role].face_grain=event.target.value as 'along_L'|'none';edit(next);}}><option value="along_L">Along part length</option><option value="none">No grain restriction</option></select></div>
      </div>)}</fieldset>
      <fieldset><legend>Construction method</legend><div className="field"><label htmlFor="construction-recipe">Installed recipe</label><select id="construction-recipe" value={form.spec.construction.recipe?form.spec.construction.recipe.id+'@'+form.spec.construction.recipe.version:''} onChange={event=>{const option=templates[0]?.recipes.find(r=>r.id+'@'+r.version===event.target.value);const next=structuredClone(form);next.spec.construction.recipe=option?{id:option.id,version:option.version}:null;edit(next);}}><option value="">Unselected · design packet only</option>{templates[0]?.recipes.map(recipe=><option key={recipe.id+'@'+recipe.version} value={recipe.id+'@'+recipe.version}>{recipe.title}</option>)}</select><small>Choosing a method does not change measured material or outside dimensions.</small></div></fieldset>
      <fieldset><legend>Manufacturing settings</legend>{measure('manufacturing.saw_kerf_mm','Saw kerf (mm)')}{measure('manufacturing.rough_allowance_per_edge_mm','Rough allowance per edge (mm)')}{measure('manufacturing.sheet_edge_trim_mm','Sheet edge trim (mm)')}<p className="help">Allowances enlarge rough blanks. Kerf consumes stock space. Finished panel sizes stay separate.</p></fieldset>
      <fieldset><legend>Stock sheets and prices</legend>{form.spec.manufacturing.stock_sheets.map((stock,i)=><fieldset key={stock.stock_id} className="stock-row"><legend>Stock sheet {i+1}</legend><div className="field"><label htmlFor={'stock-material-'+i}>Sheet {i+1} material</label><select id={'stock-material-'+i} value={stock.material_id} onChange={event=>stockChange(i,'material_id',event.target.value)}>{(['main','back'] as const).map(role=><option key={role} value={form.spec.materials[role].material_id}>{role==='main'?'Main':'Back'} · {form.spec.materials[role].actual_thickness_mm} mm</option>)}</select></div>{measure(`manufacturing.stock_sheets.${i}.length_mm`,`Sheet ${i+1} length (mm)`)}{measure(`manufacturing.stock_sheets.${i}.width_mm`,`Sheet ${i+1} width (mm)`)}<div className="field"><label htmlFor={'stock-grain-'+i}>Sheet {i+1} grain</label><select id={'stock-grain-'+i} value={stock.grain_axis} onChange={event=>stockChange(i,'grain_axis',event.target.value)}><option value="length">Along sheet length</option><option value="none">No grain restriction</option></select></div>{stockPrice(stock,i)}<button type="button" onClick={()=>removeStock(i)}>Remove sheet {i+1}</button></fieldset>)}<div className="button-row"><button type="button" disabled={form.spec.manufacturing.stock_sheets.length>=12} onClick={()=>addStock('main')}>Add main stock</button><button type="button" disabled={form.spec.manufacturing.stock_sheets.length>=12} onClick={()=>addStock('back')}>Add back stock</button></div><p className="help">Empty prices remain unknown. Stock layout is generated separately from panel geometry.</p></fieldset>
      <fieldset><legend>Output preferences</legend><div className="field"><label htmlFor="paper">Project paper size</label><select id="paper" value={form.spec.documents.paper_size} onChange={event=>{const next=structuredClone(form);next.spec.documents.paper_size=event.target.value as 'letter'|'a4';edit(next);}}><option value="letter">US Letter</option><option value="a4">A4</option></select></div><div className="field"><label htmlFor="schedule-units">Schedule units</label><select id="schedule-units" value={form.spec.documents.schedule_units} onChange={event=>{const next=structuredClone(form);next.spec.documents.schedule_units=event.target.value as 'dual'|'mm';edit(next);}}><option value="dual">Inches and millimeters</option><option value="mm">Millimeters</option></select><small>Native part drawings stay explicitly metric.</small></div></fieldset>
        </div></details>
      </fieldset>
      </form>
    </aside>
    <section className="design-area" aria-label="Project design"><div className="design-heading"><div><h2>{project?.title||form.spec.project_name}</h2><div className="revision-strip">{accepted?<span>Accepted revision {accepted.number}</span>:<span>New project</span>}{dirty&&<strong>Changes not applied</strong>}{active&&<span>Building revision {accepted?.number}</span>}</div></div></div>
      {findings.length>0&&<div className="error" role="alert"><strong>Check the highlighted fields</strong><ul>{findings.map((item,i)=><li key={i}>{item.message}</li>)}</ul></div>}
      {notice&&<p className="notice" role="status">{notice}</p>}
      <section className={'draft-summary '+(!dirty&&project?'summary-accepted':'')} data-testid="draft-summary" aria-label="Draft change summary"><h3>{dirty?'Draft preview':'Accepted design'}</h3>{validated?(dirty||!project?changeSummary(accepted?.resolved,validated.resolved,unit,precision):[`${validated.resolved.part_instance_count} panels · ${validated.resolved.openings.length} clear openings`]).map(line=><p key={line}>{line}</p>):<p>{checking?'Checking dimensions…':error instanceof ServiceUnavailableError?'Reconnect the local service to check these measurements.':'Correct the measurements to see the resulting parts.'}</p>}</section>
      {job&&accepted&&<GenerationStatus job={job} revision={accepted.number} submitting={submittingGeneration} connectionIssue={generationConnectionIssue} onCancel={()=>void cancelGeneration()} onRetry={()=>void generate(accepted).catch(failure)}/>}
      {shown&&manifest?<><div id="saved-model" className="model-label"><strong data-testid="model-revision">Last successful model · revision {shown.number}</strong><span className="model-size" data-testid="model-size"><span>{dimension(shown.spec.dimensions.outside_width_mm)} W × {dimension(shown.spec.dimensions.outside_height_mm)} H × {dimension(shown.spec.dimensions.outside_depth_mm)} D</span>{unit==='in'&&<small>{shown.spec.dimensions.outside_width_mm} × {shown.spec.dimensions.outside_height_mm} × {shown.spec.dimensions.outside_depth_mm} mm (W × H × D)</small>}</span></div>
        <div className="model-with-plans"><Plans key={shown.id} revision={shown} manifest={manifest} disabled={active||busy||outputActivity===shown.id} onDownloadsChange={files=>setPlanDownloads(previous=>files.length?{revisionId:shown.id,artifacts:files}:previous?.revisionId===shown.id?null:previous)} onActiveChange={value=>setPlansActivity(previous=>value?shown.id:previous===shown.id?null:previous)} onCompleted={async()=>{if(project)await openProject(project.id,true);}}/>
        <div className="inspection"><div id="model-viewer" className="model-space" role="group" aria-label={'3D view · revision '+shown.number} aria-describedby="saved-model" tabIndex={-1}>{manifest.part_definitions.every(d=>urls[d.definition_id])?<Viewer key={manifest.artifact_set_id} manifest={manifest} urls={urls} selected={selected} onSelect={setSelected}/>:<div className="error">The saved preview assets are incomplete. Generate this revision again.</div>}
          <div className="part-picker" aria-label="Select a physical panel">{manifest.part_instances.map(instance=><button key={instance.instance_id} aria-label={'Select '+(partLabel[instance.instance_id]||instance.instance_id)+' ('+instance.instance_id+')'} aria-pressed={selected.includes(instance.instance_id)} onClick={()=>setSelected([instance.instance_id])}><span>{partLabel[instance.instance_id]||instance.instance_id}</span><small>{instance.instance_id}</small></button>)}</div>
        </div><details className="revision-details"><summary>Measurement details</summary><dl><dt>Physical panels</dt><dd>{shown.resolved.part_instance_count}</dd><dt>Inside width</dt><dd>{dualDimension(shown.resolved.inside_width_mm)}</dd><dt>Carcass depth</dt><dd>{dualDimension(shown.resolved.carcass_depth_mm)}</dd><dt>Clear height target</dt><dd>{dualDimension(shown.resolved.rounded_clear_height_target_mm)}</dd></dl><h3>Openings</h3><ol>{shown.resolved.openings.map(opening=><li key={opening.opening_index}>{dualDimension(opening.resolved_clear_height_mm)} clear</li>)}</ol><p className="help">Dimensions checked. {manifest.construction.status==='recipe_unselected'?'Construction method needed.':manifest.construction.status==='complete'?'Technical fabrication instructions available; physical review and site installation pending.':'Construction method '+manifest.construction.status+'.'}</p><p className="help">Model, cut list, and downloads below describe revision {shown.number}. View controls only change the presentation.</p></details></div>
        </div>
        <section id="cut-list" className="cut-schedule"><div className="section-heading"><h2>Cut list <small>revision {shown.number}</small></h2>{csv&&<a className="download" href={artifactUrl(csv.artifact_id)} download>Download cut list · revision {shown.number}</a>}</div><div className="table-scroll" tabIndex={0} aria-label="Scrollable cut list"><table data-testid="cut-list"><caption>Finished panel sizes are length × width × thickness. Inch labels are approximate where marked; exact millimeters remain available. Rough blanks and grain are separate.</caption><thead><tr><th scope="col">Part group</th><th scope="col">Qty</th><th scope="col">Finished L × W × T</th><th scope="col">Rough L × W</th><th scope="col">Grain</th></tr></thead><tbody>{shown.resolved.cut_groups.map(group=>{const label=group.definition_ids.length>1?'Interchangeable panels':groupLabel(group.definition_id);return <tr key={group.group_id} className={group.member_instance_ids.some(id=>selected.includes(id))?'selected-row':''}><th scope="row"><button aria-label={'Select '+label} aria-pressed={group.member_instance_ids.every(id=>selected.includes(id))} onClick={()=>setSelected(group.member_instance_ids)}>{label}</button><small>{group.member_instance_ids.join(', ')}</small></th><td>{group.quantity}</td><td><span>{dimension(group.finished_mm.length_mm)} × {dimension(group.finished_mm.width_mm)} × {dimension(group.finished_mm.thickness_mm)}</span>{unit==='in'&&<small className="exact-measurement">{group.finished_mm.length_mm} × {group.finished_mm.width_mm} × {group.finished_mm.thickness_mm} mm</small>}</td><td><span>{dimension(group.rough_mm.length_mm)} × {dimension(group.rough_mm.width_mm)}</span>{unit==='in'&&<small className="exact-measurement">{group.rough_mm.length_mm} × {group.rough_mm.width_mm} mm</small>}</td><td>{group.grain_axis==='L'?'Along length':'Unrestricted'}</td></tr>;})}</tbody></table></div></section>
        <section className="downloads"><h2>Saved design files</h2><p>Every download belongs to revision {shown.number}.</p><div className="button-row">{canonical&&<a className="download" href={artifactUrl(canonical.artifact_id)} download>Project specification</a>}{assembly&&<a className="download" href={artifactUrl(assembly.artifact_id)} download>Assembly STEP</a>}</div><details><summary>Additional revision files</summary><ul>{additionalRevisionFiles(manifest,promotedFiles).map(artifact=><li key={artifact.artifact_id}><a href={artifactUrl(artifact.artifact_id)} download>{artifact.relative_path}</a></li>)}</ul></details></section>
        <ProjectOutputs key={shown.id} revision={shown} manifest={manifest} promotedFiles={promotedFiles} disabled={active||busy||plansActivity===shown.id} onActiveChange={value=>setOutputActivity(previous=>value?shown.id:previous===shown.id?null:previous)} onCompleted={async()=>{if(project)await openProject(project.id,true);}}/>
      </>:<section className="empty-model"><h2>{active?'Building your first model':'Review the dimensions, then generate'}</h2><p>{active?'The model appears after genuine CAD files pass their checks.':'The installed template creates full-height sides, fixed shelves, and an applied back.'}</p><p className="help">Your cut list and panel selection will also work without operating the 3D viewport.</p></section>}
      {project&&accepted&&<OfflineProposals key={project.id} project={project} revision={accepted} disabled={busy||active||dirty} onApplied={applyProposalRevision}/>}
    </section></>}
    </main></>;
}
