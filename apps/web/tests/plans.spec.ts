import {test,expect,type Page} from '@playwright/test';
import {mkdir,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import type {Job,Manifest} from '../src/api';

async function sample(page:Page){
  const {projects}=await (await page.request.get('/api/v1/projects')).json();
  const project=projects.find((p:{title:string})=>p.title==='Recovery diagnostic');
  expect(project,'Use an isolated store seeded with genuine geometry').toBeTruthy();
  const container=await (await page.request.get('/api/v1/revisions/'+project.latest_successful_revision_id)).json();
  const {manifest}=await (await page.request.get('/api/v1/revisions/'+container.revision.id+'/manifest')).json();
  return {project,container,manifest:manifest as Manifest};
}
async function open(page:Page,id:string){
  await page.goto('/');await page.getByLabel('Saved projects').selectOption(id);
  await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
  await expect(page.getByRole('button',{name:'Get plans · revision 1',exact:true})).toBeEnabled();
}

// Protocol tests inject transport/job outcomes at HTTP boundaries. They do not
// certify generated files; the final native case below inspects actual output.
async function protocol(page:Page,options:{failStock?:boolean;wrongRevision?:boolean;unplaceable?:boolean;holdDocuments?:boolean;cancelLag?:boolean}={}){
  const {project,container,manifest}=await sample(page);
  const jobs:Job[]=[];const requests:{kind:string;source:string;key:string}[]=[];
  const sets=new Map<string,Manifest>();
  let released=!options.holdDocuments;
  let cancellingPolls=0;
  await page.route('**/api/v1/revisions/'+container.revision.id,route=>route.fulfill({json:{...container,jobs:[...jobs].reverse().concat(container.jobs)}}));
  await page.route('**/api/v1/revisions/'+container.revision.id+'/manifest?*',route=>{
    const id=new URL(route.request().url()).searchParams.get('artifact_set_id')!;
    return route.fulfill({json:{artifact_set_id:id,manifest:sets.get(id)||manifest}});
  });
  await page.route('**/api/v1/revisions/'+container.revision.id+'/jobs',async route=>{
    const body=route.request().postDataJSON();const kind=body.kind;
    requests.push({kind,source:body.source_artifact_set_id,key:body.idempotency_key});
    const failed=kind==='stock'&&options.failStock&&requests.filter(r=>r.kind==='stock').length===1;
    const job:Job={id:'plans-job-'+jobs.length,revision_id:options.wrongRevision?'other-revision':container.revision.id,kind,state:failed?'failed':kind==='documents'&&!released?'running':'succeeded',stage:kind==='documents'?'generating_documents':'publishing',idempotency_key:body.idempotency_key,source_artifact_set_id:body.source_artifact_set_id,result_artifact_set_id:'plans-'+kind,diagnostic_code:failed?'WORKER_TIMEOUT':null};
    jobs.push(job);
    const derived=structuredClone(manifest);derived.artifact_set_id='plans-'+kind;
    derived.capabilities.push('documents');derived.validation.documents='passed';
    derived.artifacts.push({artifact_id:'plans-pdf',kind:'pdf',relative_path:'design-packet.pdf',definition_id:null});
    if(kind==='stock'){
      derived.capabilities.push('stock_layout');derived.validation.stock_layout=options.unplaceable?'unplaceable':'passed';
      derived.artifacts.push({artifact_id:'plans-stock-pdf',kind:'pdf',relative_path:'stock-layout.pdf',definition_id:null});
    }
    sets.set(derived.artifact_set_id,derived);
    await route.fulfill({json:{job}});
  });
  await page.route('**/api/v1/revisions/'+container.revision.id+'/package',async route=>{
    const body=route.request().postDataJSON();requests.push({kind:'package',source:body.artifact_set_id,key:body.idempotency_key});
    const job:Job={id:'plans-zip',kind:'package',revision_id:container.revision.id,state:'succeeded',stage:'publishing',idempotency_key:body.idempotency_key,source_artifact_set_id:body.artifact_set_id,result_artifact_id:'plans-zip-artifact'};
    jobs.push(job);await route.fulfill({json:{job}});
  });
  await page.route('**/api/v1/jobs/plans-*',route=>{
    const job=jobs.find(job=>route.request().url().endsWith('/'+job.id))!;
    if(job.state==='cancelling'){if(++cancellingPolls>=2)job.state='cancelled';}
    else if(job.kind==='documents'&&released&&job.state==='running')job.state='succeeded';
    return route.fulfill({json:{job}});
  });
  await page.route('**/api/v1/jobs/plans-*/cancel',route=>{
    const job=jobs.find(job=>route.request().url().endsWith('/'+job.id+'/cancel'))!;
    job.state=options.cancelLag?'cancelling':'cancelled';return route.fulfill({json:{job}});
  });
  return {project,container,manifest,jobs,requests,release:()=>{released=true;}};
}

test('Get plans is the primary packet action and individual tools remain available',async({page})=>{
  const {project}=await sample(page);await open(page,project.id);
  await expect(page.getByRole('button',{name:/^Generate measured PDF/})).toBeHidden();
  await page.getByText('Individual output tools',{exact:true}).click();
  await expect(page.getByRole('button',{name:/^Generate measured PDF/})).toBeVisible();
});

test('Get plans retries the failed stock step and packages its exact cumulative result',async({page})=>{
  const flow=await protocol(page,{failStock:true});await open(page,flow.project.id);
  await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('WORKER_TIMEOUT');
  await expect(page.getByRole('link',{name:/Download cut list/})).toBeVisible();
  await page.getByRole('button',{name:'Retry plans · revision 1',exact:true}).click();
  await expect(page.getByRole('link',{name:'Download plans ZIP · revision 1',exact:true})).toBeVisible();
  expect(flow.requests.map(r=>r.kind)).toEqual(['documents','stock','stock','package']);
  expect(flow.requests.map(r=>r.source)).toEqual([flow.manifest.artifact_set_id,'plans-documents','plans-documents','plans-stock']);
  expect(flow.requests[1].key).not.toBe(flow.requests[2].key);
  await expect(page.getByRole('link',{name:'Plans measured PDF · revision 1',exact:true})).toHaveAttribute('href','/api/v1/artifacts/plans-pdf/download');
});

test('reload resumes the same run without duplicating drawings or switching source sets',async({page})=>{
  const flow=await protocol(page,{holdDocuments:true});await open(page,flow.project.id);
  await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).dblclick();
  await expect(page.getByRole('status',{name:'Plans progress'})).toContainText('Measured drawings');
  await page.reload();
  await expect(page.getByRole('status',{name:'Plans progress'})).toContainText('Measured drawings');
  flow.release();
  await expect(page.getByRole('link',{name:'Download plans ZIP · revision 1',exact:true})).toBeVisible();
  expect(flow.requests.map(r=>r.kind)).toEqual(['documents','stock','package']);
});

test('a job for another revision cannot advance the plans workflow',async({page})=>{
  const flow=await protocol(page,{wrongRevision:true});await open(page,flow.project.id);
  await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('does not match');
  expect(flow.requests.map(r=>r.kind)).toEqual(['documents']);
  await expect(page.getByRole('link',{name:/Download plans ZIP/})).toHaveCount(0);
});

test('an incomplete stock layout is reported before any ready package is offered',async({page})=>{
  const flow=await protocol(page,{unplaceable:true});await open(page,flow.project.id);
  await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Stock layout is incomplete');
  expect(flow.requests.map(r=>r.kind)).toEqual(['documents','stock']);
  await expect(page.getByRole('link',{name:/Download plans ZIP/})).toHaveCount(0);
});

test('retry after a failed recovery lookup reconnects to the existing run',async({page})=>{
  const flow=await protocol(page,{holdDocuments:true});await open(page,flow.project.id);
  await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
  await expect(page.getByRole('status',{name:'Plans progress'})).toContainText('Measured drawings');
  let reads=0;
  await page.route('**/api/v1/revisions/'+flow.container.revision.id,route=>{
    if(++reads===2)return route.fulfill({status:503,json:{error:{message:'Recovery lookup unavailable'}}});
    return route.fallback();
  });
  await page.reload();
  await expect(page.getByRole('alert')).toContainText('Recovery lookup unavailable');
  flow.release();await page.getByRole('button',{name:'Retry plans · revision 1',exact:true}).click();
  await expect(page.getByRole('link',{name:'Download plans ZIP · revision 1',exact:true})).toBeVisible();
  expect(flow.requests.map(r=>r.kind)).toEqual(['documents','stock','package']);
});

test('retry waits for a cancelling job before restarting only that step',async({page})=>{
  const flow=await protocol(page,{holdDocuments:true,cancelLag:true});await open(page,flow.project.id);
  await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
  await page.getByRole('button',{name:'Cancel plans',exact:true}).click();
  await expect(page.getByRole('button',{name:'Retry plans · revision 1',exact:true})).toBeVisible();
  flow.release();await page.getByRole('button',{name:'Retry plans · revision 1',exact:true}).click();
  await expect(page.getByRole('link',{name:'Download plans ZIP · revision 1',exact:true})).toBeVisible();
  expect(flow.requests.map(r=>r.kind)).toEqual(['documents','documents','stock','package']);
});

test('leaving the displayed revision suspends subsequent plans steps',async({page})=>{
  const flow=await protocol(page,{holdDocuments:true});await open(page,flow.project.id);
  await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
  await expect(page.getByRole('status',{name:'Plans progress'})).toContainText('Measured drawings');
  await page.getByRole('button',{name:'New bookcase',exact:true}).click();flow.release();
  await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeVisible();
  // Wait beyond the controller's polling boundary, not a native worker deadline.
  await page.waitForTimeout(1300);
  expect(flow.requests.map(r=>r.kind)).toEqual(['documents']);
  await expect(page.getByRole('link',{name:/Download plans ZIP/})).toHaveCount(0);
});

test('cancel intent pauses advancement while its acknowledgement is delayed',async({page})=>{
  const flow=await protocol(page,{holdDocuments:true});await open(page,flow.project.id);
  await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
  await expect(page.getByRole('button',{name:'Cancel plans',exact:true})).toBeVisible();
  let release!:()=>void;
  const acknowledgement=new Promise<void>(resolve=>{release=resolve;});
  await page.route('**/api/v1/jobs/plans-*/cancel',async route=>{
    await acknowledgement;await route.fulfill({json:{job:flow.jobs[0]}});
  });
  try{
    await page.getByRole('button',{name:'Cancel plans',exact:true}).click();flow.release();
    await page.waitForTimeout(1600);
    expect(flow.requests.map(r=>r.kind)).toEqual(['documents']);
    await expect(page.getByRole('button',{name:/^(Get|Retry) plans · revision 1$/})).toBeDisabled();
  }finally{release();}
  await expect(page.getByRole('button',{name:'Retry plans · revision 1',exact:true})).toBeEnabled();
});

test('an unconfirmed cancellation stays paused until an explicit reconnect',async({page})=>{
  const flow=await protocol(page,{holdDocuments:true});await open(page,flow.project.id);
  await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
  await page.route('**/api/v1/jobs/plans-*/cancel',route=>route.abort('failed'));
  await page.getByRole('button',{name:'Cancel plans',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Cancellation could not be confirmed');
  await expect(page.getByRole('button',{name:'Retry plans · revision 1',exact:true})).toBeEnabled();
  expect(flow.requests.map(r=>r.kind)).toEqual(['documents']);
  flow.release();await page.getByRole('button',{name:'Retry plans · revision 1',exact:true}).click();
  await expect(page.getByRole('link',{name:'Download plans ZIP · revision 1',exact:true})).toBeVisible();
  expect(flow.requests.map(r=>r.kind)).toEqual(['documents','stock','package']);
});

test('offline measurements to Update design to Get plans survives reload and lost acknowledgement with genuine files',async({page})=>{
  test.setTimeout(480000);
  await page.route('**/*',route=>['127.0.0.1','localhost','[::1]'].includes(new URL(route.request().url()).hostname)?route.continue():route.abort());
  await page.goto('/');await page.getByRole('button',{name:'New bookcase',exact:true}).click();
  await page.getByLabel('Project name').fill('Get plans acceptance '+Date.now());
  await page.getByRole('button',{name:'Create design',exact:true}).click();
  await expect(page.getByTestId('model-revision')).toContainText('revision 1',{timeout:120000});
  for(const [label,value] of [['Outside width','36 in'],['Outside height','42 in'],['Outside depth','14 in'],['Actual main thickness (mm)','19 mm']])await page.getByLabel(label,{exact:true}).fill(value);
  await page.getByLabel('Fixed shelves',{exact:true}).selectOption('3');
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Update design',exact:true}).click();
  await expect(page.getByTestId('model-revision')).toContainText('revision 2',{timeout:120000});
  await expect(page.getByTestId('asset-loaded')).toHaveText('8 part instances loaded');
  const projectId=await page.getByLabel('Saved projects').inputValue();
  const {project}=await (await page.request.get('/api/v1/projects/'+projectId)).json();
  const revisionId=project.latest_successful_revision_id;
  const before=(await (await page.request.get('/api/v1/revisions/'+revisionId+'/manifest')).json()).manifest;
  const csvBefore=await (await page.request.get((await page.getByRole('link',{name:/Download cut list/}).getAttribute('href'))!)).text();
  let dropped=false,stockKey='';
  await page.route('**/api/v1/revisions/'+revisionId+'/jobs',async route=>{
    const body=route.request().postDataJSON();
    if(body.kind==='stock'&&!dropped){
      stockKey=body.idempotency_key;dropped=true;const response=await route.fetch();expect(response.status()).toBe(202);await route.abort('failed');
    }else await route.continue();
  });
  const drawingQueued=page.waitForResponse(response=>response.request().method()==='POST'&&response.url().endsWith('/revisions/'+revisionId+'/jobs')&&response.request().postDataJSON().kind==='documents');
  await page.getByRole('button',{name:'Get plans · revision 2',exact:true}).click();
  expect((await drawingQueued).status()).toBe(202);
  await page.reload();
  await expect(page.getByRole('status',{name:'Plans progress'})).toContainText('Measured drawings');
  await expect(page.getByRole('button',{name:'Retry plans · revision 2',exact:true})).toBeVisible({timeout:120000});
  await expect(page.getByRole('alert')).toContainText('local service');
  await page.getByRole('button',{name:'Retry plans · revision 2',exact:true}).click();
  const download=page.getByRole('link',{name:'Download plans ZIP · revision 2',exact:true});
  await expect(download).toBeVisible({timeout:120000});
  await expect(page.getByRole('status',{name:'Plans progress'})).toContainText('Plans ready · revision 2');
  const {jobs}=await (await page.request.get('/api/v1/revisions/'+revisionId)).json();
  const planJobs=jobs.filter((job:Job)=>job.idempotency_key?.startsWith('plans:'));
  expect(planJobs).toHaveLength(3);expect(planJobs.every((job:Job)=>job.state==='succeeded'&&job.revision_id===revisionId)).toBe(true);
  const documents=planJobs.find((job:Job)=>job.kind==='documents');
  const stock=planJobs.find((job:Job)=>job.kind==='stock');
  const pack=planJobs.find((job:Job)=>job.kind==='package');
  expect(documents.source_artifact_set_id).toBe(before.artifact_set_id);
  expect(stock.source_artifact_set_id).toBe(documents.result_artifact_set_id);expect(stock.idempotency_key).toBe(stockKey);
  expect(pack.source_artifact_set_id).toBe(stock.result_artifact_set_id);
  const {manifest}=await (await page.request.get('/api/v1/revisions/'+revisionId+'/manifest?artifact_set_id='+pack.source_artifact_set_id)).json();
  expect(manifest.revision_id).toBe(revisionId);expect(manifest.validation.documents).toBe('passed');expect(manifest.validation.stock_layout).toBe('passed');
  const zip=await (await page.request.get((await download.getAttribute('href'))!)).body();
  const repo=fileURLToPath(new URL('../../../',import.meta.url));
  const evidenceRoot=process.env.WOODWORK_PLANS_EVIDENCE_ROOT||join(repo,'.verification/get-plans-20261017');
  await mkdir(evidenceRoot,{recursive:true});
  const zipPath=join(evidenceRoot,'accepted-project.zip');
  const manifestPath=join(evidenceRoot,'accepted-manifest.json');
  await writeFile(zipPath,zip);await writeFile(manifestPath,JSON.stringify(manifest));
  const inspected=JSON.parse(execFileSync(join(repo,'.venv/Scripts/python.exe'),['-c',`
import sys,json,zipfile,hashlib,io
from pypdf import PdfReader
expected=json.load(open(sys.argv[2],encoding='utf-8'))
with zipfile.ZipFile(sys.argv[1]) as z:
 names=z.namelist(); m=json.loads(z.read('manifest.json'))
 assert m==expected
 assert len(names)==len(set(names)) and set(names)=={'manifest.json',*[a['relative_path'] for a in m['artifacts']]}
 for a in m['artifacts']:
  data=z.read(a['relative_path']); assert len(data)==a['size_bytes'] and hashlib.sha256(data).hexdigest()==a['sha256']
  assert a['revision_id']==m['revision_id'] and a['spec_sha256']==m['spec_sha256']
 csv=z.read('cut-list.csv').decode(); assert m['revision_id'] in csv and ',876.4,349.6,' in csv
 stock=json.loads(z.read('stock-layout.json')); assert stock['revision_id']==m['revision_id'] and stock['plan']['status']=='complete' and not stock['plan']['unplaced_instance_ids']
 pdfs={name:len(PdfReader(io.BytesIO(z.read(name))).pages) for name in names if name.endswith('.pdf')}
 assert 'design-packet.pdf' in pdfs and 'stock-layout.pdf' in pdfs and len(pdfs)>=5
 print(json.dumps({'status':'passed','revision_id':m['revision_id'],'artifact_set_id':m['artifact_set_id'],'payload_count':len(m['artifacts']),'zip_sha256':hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest(),'pdf_pages':pdfs,'every_payload_hash_and_revision_checked':True}))
`,zipPath,manifestPath],{encoding:'utf8'}));
  await mkdir('tests/evidence',{recursive:true});
  await writeFile('tests/evidence/get-plans-acceptance.json',JSON.stringify({project_id:projectId,revision_id:revisionId,jobs:planJobs,inspection:inspected,reload_during_drawings:true,lost_stock_acknowledgement_recovered:true},null,2)+'\n');
  for(const [path,label] of [['design-packet.pdf','Plans measured PDF'],['stock-layout.pdf','Plans stock layout PDF'],['cut-list.csv','Plans cut list CSV']]){
    const artifact=manifest.artifacts.find((a:{relative_path:string})=>a.relative_path===path);
    await expect(page.getByRole('link',{name:label+' · revision 2',exact:true})).toHaveAttribute('href','/api/v1/artifacts/'+artifact.artifact_id+'/download');
  }
  expect(await (await page.request.get((await page.getByRole('link',{name:'Plans cut list CSV · revision 2',exact:true}).getAttribute('href'))!)).text()).toBe(csvBefore);
  await page.reload();await expect(download).toBeVisible();
  expect((await (await page.request.get('/api/v1/revisions/'+revisionId)).json()).jobs.filter((job:Job)=>job.idempotency_key?.startsWith('plans:'))).toHaveLength(3);
  await download.scrollIntoViewIfNeeded();await page.screenshot({path:'tests/evidence/get-plans-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});await download.focus();await expect(download).toBeFocused();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:'tests/evidence/get-plans-narrow.png',fullPage:true});
});
