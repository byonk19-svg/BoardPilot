import {test,expect,type Page} from '@playwright/test';
import {writeFile} from 'node:fs/promises';

test.use({actionTimeout:15000});

async function seedProject(page:Page){
  const projects=(await (await page.request.get('/api/v1/projects')).json()).projects;
  const project=projects.find((p:{title:string})=>p.title==='Recovery diagnostic');
  expect(project,'Use the isolated seeded regeneration verification store').toBeTruthy();
  const container=await (await page.request.get('/api/v1/revisions/'+project.latest_accepted_revision_id)).json();
  return {project,container};
}

test('timeout retry clears stale failure, shows live stages and preserves prior files',async({page})=>{
  const {project,container}=await seedProject(page);
  const revision=container.revision;
  let job={id:'job-ui-regression',kind:'generate',revision_id:revision.id,state:'failed',stage:'generating_geometry',diagnostic_code:'CAD_TIMEOUT',started_at:new Date(Date.now()-65000).toISOString()};
  await page.route('**/api/v1/revisions/'+revision.id,route=>route.fulfill({json:{...container,jobs:[job]}}));
  await page.route('**/api/v1/jobs/'+job.id,route=>route.fulfill({json:{job}}));
  let release!:()=>void;
  const released=new Promise<void>(resolve=>release=resolve);
  await page.route('**/api/v1/revisions/'+revision.id+'/jobs',async route=>{
    await released;job={...job,state:'running',stage:'generating_side_panels',diagnostic_code:''};
    await route.fulfill({json:{job}});
  });
  await page.route('**/api/v1/jobs/'+job.id+'/cancel',async route=>{
    job={...job,state:'cancelling'};await route.fulfill({json:{job}});
    job={...job,state:'cancelled'};
  });
  await page.goto('/');await page.getByLabel('Saved projects').selectOption(project.id);
  await expect(page.getByText('Generation timed out',{exact:true})).toBeVisible();
  await page.screenshot({path:'tests/evidence/regeneration-timeout.png',fullPage:false});
  const csv=await page.getByRole('link',{name:/Download cut list/}).getAttribute('href');
  const model=await page.getByTestId('model-revision').innerText();
  const retry=page.getByRole('button',{name:'Retry revision '+revision.number,exact:true});
  try{await retry.click();await expect(retry).toBeDisabled();}finally{release();}
  await expect(page.getByText('Building side panels',{exact:true})).toBeVisible();
  await expect(page.getByText('Generation timed out',{exact:true})).toHaveCount(0);
  await expect(page.getByTestId('generation-elapsed')).toContainText('Elapsed');
  await page.screenshot({path:'tests/evidence/regeneration-progress.png',fullPage:false});
  await page.reload();
  await expect(page.getByText('Building side panels',{exact:true})).toBeVisible();
  job={...job,stage:'generating_horizontal_panels'};
  await expect(page.getByText('Building shelves, top and bottom',{exact:true})).toBeVisible();
  job={...job,stage:'assembling_geometry'};
  await expect(page.getByText('Assembling panels',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Cancel generation',exact:true}).click();
  await expect(page.getByText('Generation cancelled',{exact:true})).toBeVisible();
  await expect(page.getByTestId('model-revision')).toHaveText(model);
  await expect(page.getByRole('link',{name:/Download cut list/})).toHaveAttribute('href',csv!);
});

test('temporary polling failure reconnects without reporting a failed generation',async({page})=>{
  const {project,container}=await seedProject(page);
  const job={id:'job-poll-regression',kind:'generate',revision_id:container.revision.id,state:'running',stage:'generating_back_panel',started_at:new Date().toISOString()};
  await page.route('**/api/v1/revisions/'+container.revision.id,route=>route.fulfill({json:{...container,jobs:[job]}}));
  let requests=0;
  await page.route('**/api/v1/jobs/'+job.id,async route=>{
    if(++requests===1)await route.abort('failed');
    else await route.fulfill({json:{job:{...job,stage:'inspecting_geometry'}}});
  });
  await page.goto('/');await page.getByLabel('Saved projects').selectOption(project.id);
  await expect(page.getByText(/Reconnecting to generation status/)).toBeVisible();
  await expect(page.getByText('Generation failed',{exact:true})).toHaveCount(0);
  await expect(page.getByText('Checking saved geometry',{exact:true})).toBeVisible({timeout:12000});
  await expect(page.getByText(/Reconnecting to generation status/)).toHaveCount(0);
});

test('retry after a lost submission response reuses the same request identity',async({page})=>{
  const {project,container}=await seedProject(page);
  const revision=container.revision;
  let job={id:'job-uncertain-submit',kind:'generate',revision_id:revision.id,state:'failed',stage:'generating_geometry',diagnostic_code:'CAD_TIMEOUT'};
  const keys:string[]=[];
  await page.route('**/api/v1/revisions/'+revision.id,async route=>{
    if(keys.length===1)await route.abort('failed');
    else await route.fulfill({json:{...container,jobs:[job]}});
  });
  await page.route('**/api/v1/jobs/'+job.id,route=>route.fulfill({json:{job}}));
  await page.route('**/api/v1/revisions/'+revision.id+'/jobs',async route=>{
    keys.push(route.request().postDataJSON().idempotency_key);
    if(keys.length===1)await route.abort('failed');
    else {job={...job,state:'running',stage:'generating_side_panels',diagnostic_code:''};await route.fulfill({json:{job}});}
  });
  await page.goto('/');await page.getByLabel('Saved projects').selectOption(project.id);
  const retry=page.getByRole('button',{name:'Retry revision '+revision.number,exact:true});
  await retry.click();await expect(page.getByRole('alert')).toBeVisible();
  await retry.click();await expect(page.getByText('Building side panels',{exact:true})).toBeVisible();
  expect(keys).toHaveLength(2);expect(keys[1]).toBe(keys[0]);
});

for(const state of ['running','succeeded'])test('lost submission acknowledgement reconnects to the '+state+' job',async({page})=>{
  const {project,container}=await seedProject(page);
  const revision=container.revision;
  let job={id:'job-ack-'+state,kind:'generate',revision_id:revision.id,state:'failed',stage:'generating_geometry',diagnostic_code:'CAD_TIMEOUT',idempotency_key:''};
  let submissions=0,manifestRequests=0;
  page.on('request',request=>{if(request.url().endsWith('/api/v1/revisions/'+revision.id+'/manifest'))manifestRequests++;});
  await page.route('**/api/v1/revisions/'+revision.id,route=>route.fulfill({json:{...container,jobs:[job]}}));
  await page.route('**/api/v1/jobs/'+job.id,route=>route.fulfill({json:{job}}));
  await page.route('**/api/v1/revisions/'+revision.id+'/jobs',async route=>{
    submissions++;job={...job,state,stage:'generating_side_panels',diagnostic_code:'',idempotency_key:route.request().postDataJSON().idempotency_key};
    await route.abort('failed');
  });
  await page.goto('/');await page.getByLabel('Saved projects').selectOption(project.id);
  await page.getByRole('button',{name:'Retry revision '+revision.number,exact:true}).click();
  await expect(page.getByText(state==='running'?'Building side panels':'Generation complete',{exact:true})).toBeVisible();
  if(state==='succeeded')await expect.poll(()=>manifestRequests).toBeGreaterThan(1);
  expect(submissions).toBe(1);await expect(page.getByRole('alert')).toHaveCount(0);
});

test('a structured runtime refusal retains its setup guidance',async({page})=>{
  const {project,container}=await seedProject(page);
  const revision=container.revision;
  const job={id:'job-runtime-refusal',kind:'generate',revision_id:revision.id,state:'failed',stage:'generating_geometry',diagnostic_code:'CAD_TIMEOUT'};
  await page.route('**/api/v1/revisions/'+revision.id,route=>route.fulfill({json:{...container,jobs:[job]}}));
  await page.route('**/api/v1/revisions/'+revision.id+'/jobs',route=>route.fulfill({status:503,json:{error:{code:'RUNTIME_UNAVAILABLE',message:'Install the locked runtime and run preflight.'}}}));
  await page.goto('/');await page.getByLabel('Saved projects').selectOption(project.id);
  await page.getByRole('button',{name:'Retry revision '+revision.number,exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Install the locked runtime and run preflight.');
});

test('genuine width height depth edits and cancel retry keep CAD CSV and stock on one revision',async({page})=>{
  test.skip(process.env.WOODWORK_RUN_REGENERATION_FLOW!=='1','Explicit opt-in for five genuine native builds');
  test.setTimeout(900000);
  const evidence:{revision:number;revision_id:string;artifact_set_id:string;generation_job_id:string;generation_artifact_set_id:string;stock_job_id:string;dimensions:unknown;generation_seconds:number;observed_stages:string[]}[]=[];
  const stages=new Map<string,Set<string>>();
  page.on('response',async response=>{
    if(!/\/api\/v1\/jobs\/[^/]+$/.test(response.url())||!response.ok())return;
    try{const {job}=await response.json();const values=stages.get(job.id)||new Set<string>();values.add(job.stage);stages.set(job.id,values);}catch{/* Navigation can dispose a completed response body. */}
  });
  await page.goto('/');await page.getByRole('button',{name:'New bookcase',exact:true}).click();
  await page.getByLabel('Project name').fill('Regeneration acceptance '+Date.now());
  await page.getByRole('button',{name:'Create design',exact:true}).click();
  async function verified(revisionNumber:number){
    await expect(page.getByTestId('model-revision')).toContainText('revision '+revisionNumber,{timeout:120000});
    await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
    await expect(page.getByRole('heading',{name:'Cut list revision '+revisionNumber,exact:true})).toBeVisible();
    const projectId=await page.getByLabel('Saved projects').inputValue();
    const {project}=await (await page.request.get('/api/v1/projects/'+projectId)).json();
    expect(project.latest_successful_revision_id).toBe(project.latest_accepted_revision_id);
    const record=await (await page.request.get('/api/v1/revisions/'+project.latest_accepted_revision_id)).json();
    const job=record.jobs.find((j:{kind:string})=>j.kind==='generate');
    expect(job.state,job.diagnostic_code).toBe('succeeded');
    expect(job.metrics.elapsed_seconds).toBeLessThan(120);
    expect([...(stages.get(job.id)||[])]).toContain('generating_side_panels');
    const csv=await (await page.request.get((await page.getByRole('link',{name:/Download cut list/}).getAttribute('href'))!)).text();
    expect(csv).toContain(record.revision.id);
    const horizontal=record.revision.resolved.part_definitions.find((d:{definition_id:string})=>d.definition_id==='panel_horizontal');
    expect(csv).toContain(','+horizontal.finished_mm.length_mm+','+horizontal.finished_mm.width_mm+',');
    const queued=page.waitForResponse(response=>response.request().method()==='POST'&&response.url().endsWith('/api/v1/revisions/'+record.revision.id+'/jobs'));
    await page.getByRole('button',{name:'Plan stock and cost · revision '+revisionNumber,exact:true}).click();
    const {job:stockJob}=await (await queued).json();
    // A prior same-revision PDF stays usable during a retry. Wait for this job,
    // then require its new PDF identity instead of accepting that earlier link.
    await expect.poll(async()=>{
      const {job:current}=await (await page.request.get('/api/v1/jobs/'+stockJob.id)).json();
      return current.state;
    },{timeout:30000}).toBe('succeeded');
    const published=await (await page.request.get('/api/v1/revisions/'+record.revision.id+'/manifest')).json();
    const finishedStock=(await (await page.request.get('/api/v1/jobs/'+stockJob.id)).json()).job;
    expect(published.artifact_set_id).toBe(finishedStock.result_artifact_set_id);
    const stockPdf=published.manifest.artifacts.find((a:{relative_path:string})=>a.relative_path==='stock-layout.pdf');
    await expect(page.getByRole('link',{name:'Stock layout and cut sequence PDF · revision '+revisionNumber,exact:true})).toHaveAttribute('href','/api/v1/artifacts/'+stockPdf.artifact_id+'/download');
    const stockLink=page.getByRole('link',{name:'Stock layout data',exact:true});
    const stock=await (await page.request.get((await stockLink.getAttribute('href'))!)).json();
    expect(stock.revision_id).toBe(record.revision.id);expect(stock.plan.status).toBe('complete');
    expect(stock.plan.unplaced_instance_ids).toEqual([]);
    const parts=stock.plan.sheets.flatMap((s:{leaf_regions:{kind:string;instance_id:string}[]})=>s.leaf_regions.filter(p=>p.kind==='part'));
    expect(parts.map((p:{instance_id:string})=>p.instance_id).sort()).toEqual(['back','bottom','shelf_01','shelf_02','side_left','side_right','top']);
    const {manifest}=await (await page.request.get('/api/v1/revisions/'+record.revision.id+'/manifest')).json();
    expect(manifest.revision_number).toBe(revisionNumber);expect(manifest.revision_id).toBe(record.revision.id);
    expect(manifest.versions.adapter).toBe('1.1.0');expect(manifest.validation.stock_layout).toBe('passed');
    await expect(page.getByTestId('sheet-subtotal')).toContainText('unknown');
    evidence.push({revision:revisionNumber,revision_id:record.revision.id,artifact_set_id:manifest.artifact_set_id,generation_job_id:job.id,generation_artifact_set_id:job.result_artifact_set_id,stock_job_id:stockJob.id,dimensions:record.revision.spec.dimensions,generation_seconds:job.metrics.elapsed_seconds,observed_stages:[...(stages.get(job.id)||[])]});
    await writeFile('tests/evidence/regeneration-acceptance.json',JSON.stringify(evidence,null,2)+'\n');
  }
  await verified(1);
  const changes=[['Outside width','36 in','878.4'],['Outside height','42 in','1066.8'],['Outside depth','14 in','349.6']];
  for(const [index,[field,value,expected]] of changes.entries()){
    await page.getByLabel(field,{exact:true}).fill(value);
    await expect(page.getByTestId('draft-summary')).toContainText(expected);
    if(field==='Outside width')await expect(page.getByTestId('draft-summary')).toContainText('Applied back width');
    await page.getByRole('button',{name:'Update design',exact:true}).click();
    await verified(index+2);
  }
  const priorCsv=await (await page.request.get((await page.getByRole('link',{name:/Download cut list/}).getAttribute('href'))!)).text();
  const priorStock=await page.getByRole('link',{name:/Stock layout and cut sequence PDF/}).getAttribute('href');
  await page.getByRole('button',{name:'Update design',exact:true}).click();
  await expect(page.getByText('Building side panels',{exact:true})).toBeVisible({timeout:30000});
  const cancellationStarted=Date.now();
  await page.getByRole('button',{name:'Cancel generation',exact:true}).click();
  await expect(page.getByText('Generation cancelled',{exact:true})).toBeVisible({timeout:10000});
  const cancellationMs=Date.now()-cancellationStarted;
  expect(cancellationMs).toBeLessThan(5000);
  await expect(page.getByTestId('model-revision')).toContainText('revision 4');
  await expect(page.getByRole('link',{name:/Stock layout and cut sequence PDF/})).toHaveAttribute('href',priorStock!);
  expect(await (await page.request.get((await page.getByRole('link',{name:/Download cut list/}).getAttribute('href'))!)).text()).toBe(priorCsv);
  await writeFile('tests/evidence/regeneration-cancel.json',JSON.stringify({cancellation_ms:cancellationMs,prior_model_revision:4,prior_csv_unchanged:true,prior_stock_link_preserved:true},null,2)+'\n');
  await page.getByRole('button',{name:'Retry revision 4',exact:true}).click();
  await expect(page.getByRole('button',{name:'Cancel generation',exact:true})).toBeVisible();
  await expect(page.getByText('Generation complete',{exact:true})).toBeVisible({timeout:120000});
  await verified(4);
  await page.screenshot({path:'tests/evidence/regeneration-final.png',fullPage:true});
});
