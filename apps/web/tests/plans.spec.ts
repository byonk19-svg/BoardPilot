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
async function protocol(page:Page,options:{failStock?:boolean;wrongRevision?:boolean;unplaceable?:boolean;holdDocuments?:boolean;cancelLag?:boolean;illustrated?:boolean;publishPreferred?:boolean;methodStatus?:string;loseIndividualAck?:boolean}={}){
  const {project,container,manifest}=await sample(page);
  const jobs:Job[]=[];const requests:{kind:string;source:string;key:string}[]=[];
  const sets=new Map<string,Manifest>();
  let released=!options.holdDocuments;
  let cancellingPolls=0;
  let lostIndividualAck=false;
  if(options.publishPreferred)await page.route('**/api/v1/revisions/'+container.revision.id+'/manifest',route=>{
    const published=sets.get('plans-stock')||manifest;
    return route.fulfill({json:{artifact_set_id:published.artifact_set_id,manifest:published}});
  });
  await page.route('**/api/v1/revisions/'+container.revision.id,route=>route.fulfill({json:{...container,jobs:[...jobs].reverse().concat(container.jobs)}}));
  await page.route('**/api/v1/revisions/'+container.revision.id+'/manifest?*',route=>{
    const id=new URL(route.request().url()).searchParams.get('artifact_set_id')!;
    return route.fulfill({json:{artifact_set_id:id,manifest:sets.get(id)||manifest}});
  });
  await page.route('**/api/v1/revisions/'+container.revision.id+'/jobs',async route=>{
    const body=route.request().postDataJSON();const kind=body.kind;
    requests.push({kind,source:body.source_artifact_set_id,key:body.idempotency_key});
    const existing=jobs.find(j=>j.idempotency_key===body.idempotency_key);
    if(existing){await route.fulfill({json:{job:existing}});return;}
    const failed=kind==='stock'&&options.failStock&&requests.filter(r=>r.kind==='stock').length===1;
    const job:Job={id:'plans-job-'+jobs.length,revision_id:options.wrongRevision?'other-revision':container.revision.id,kind,state:failed?'failed':kind==='documents'&&!released?'running':'succeeded',stage:kind==='documents'?'generating_documents':'publishing',idempotency_key:body.idempotency_key,source_artifact_set_id:body.source_artifact_set_id,result_artifact_set_id:'plans-'+kind,diagnostic_code:failed?'WORKER_TIMEOUT':null};
    jobs.push(job);
    const derived=structuredClone(manifest);derived.artifact_set_id='plans-'+kind;
    derived.capabilities.push('documents');derived.validation.documents='passed';
    derived.artifacts.push({artifact_id:'plans-pdf',kind:'pdf',relative_path:'design-packet.pdf',definition_id:null});
    if(options.illustrated){
      derived.construction={...derived.construction,status:'complete'};
      derived.artifacts.push({artifact_id:'plans-guide',kind:'json',relative_path:'beginner-guide.json',definition_id:null});
    }
    if(options.methodStatus)derived.construction.status=options.methodStatus;
    if(kind==='stock'){
      derived.capabilities.push('stock_layout');derived.validation.stock_layout=options.unplaceable?'unplaceable':'passed';
      derived.artifacts.push({artifact_id:'plans-stock-pdf',kind:'pdf',relative_path:'stock-layout.pdf',definition_id:null});
    }
    sets.set(derived.artifact_set_id,derived);
    if(options.loseIndividualAck&&!lostIndividualAck&&!body.idempotency_key.startsWith('plans:')){
      lostIndividualAck=true;await route.abort('failed');return;
    }
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
  return {project,container,manifest,jobs,requests,sets,release:()=>{released=true;}};
}

test('Get plans stays beside the desktop model and is keyboard reachable above the narrow viewer',async({page})=>{
  await page.setViewportSize({width:1280,height:900});
  const {project}=await sample(page);await open(page,project.id);
  const plans=page.getByRole('region',{name:'Get plans',exact:true});
  const viewer=page.getByRole('region',{name:'3D model viewer',exact:true});
  const p=(await plans.boundingBox())!,v=(await viewer.boundingBox())!;
  expect(p.x).toBeGreaterThanOrEqual(v.x+v.width-1);
  expect(Math.abs(p.y-v.y)).toBeLessThan(50);
  await expect(page.getByRole('button',{name:'Get plans · revision 1',exact:true})).toBeInViewport();
  await expect(page.getByRole('button',{name:/^Generate measured PDF/})).toBeHidden();
  await page.getByText('Individual output tools',{exact:true}).click();
  await expect(page.getByRole('button',{name:/^Generate measured PDF/})).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  const shortcut=page.getByRole('link',{name:'Plans',exact:true});
  await shortcut.focus();await shortcut.press('Enter');
  await expect(page).toHaveURL(/#plans$/);
  await page.keyboard.press('Tab');
  const action=page.getByRole('button',{name:'Get plans · revision 1',exact:true});
  await expect(action).toBeFocused();await expect(action).toBeInViewport();
  const narrowPlans=(await plans.boundingBox())!,narrowViewer=(await viewer.boundingBox())!;
  expect(narrowPlans.y+narrowPlans.height).toBeLessThanOrEqual(narrowViewer.y+1);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

for(const width of [320,390]){
  test(`phone 3D shortcut reaches the actual viewer with ready plans at ${width}px`,async({page})=>{
    await page.setViewportSize({width,height:844});
    const flow=await protocol(page,{illustrated:true,publishPreferred:true});await open(page,flow.project.id);
    await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
    const download=page.getByRole('link',{name:'Download plans ZIP · revision 1',exact:true});
    await expect(download).toBeVisible();
    await expect(page.getByRole('button',{name:'Check plans · revision 1',exact:true})).toBeEnabled();
    const shortcut=page.getByRole('link',{name:'3D view',exact:true});
    const destination=page.getByRole('group',{name:'3D view · revision 1',exact:true});
    const viewer=page.getByRole('region',{name:'3D model viewer',exact:true});
    for(const activation of ['keyboard','pointer']){
      if(activation==='keyboard'){await shortcut.focus();await shortcut.press('Enter');}
      else await shortcut.click();
      await expect(viewer.locator('canvas')).toBeInViewport({ratio:.8});
      await expect(destination).toBeFocused();
      await expect(destination).toHaveAccessibleDescription(/Last successful model · revision 1/);
      await page.keyboard.press('Tab');
      await expect(viewer.getByRole('button',{name:'Front',exact:true})).toBeFocused();
      const plans=page.getByRole('region',{name:'Get plans',exact:true});
      const plansBounds=(await plans.boundingBox())!,viewerBounds=(await viewer.boundingBox())!;
      expect(plansBounds.y+plansBounds.height).toBeLessThanOrEqual(viewerBounds.y+1);
      await page.getByRole('link',{name:'Plans',exact:true}).press('Enter');
      await expect(plans).toBeFocused();await page.keyboard.press('Tab');
      await expect(download).toBeFocused();await expect(download).toBeInViewport();
    }
    await shortcut.press('Enter');
    await expect(destination).toBeFocused();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    expect(flow.requests.map(request=>request.kind)).toEqual(['documents','stock','package']);
    await page.screenshot({path:test.info().outputPath(`viewer-shortcut-${width}.png`)});
  });
}

test('the illustrated guide is named once and promoted downloads are not repeated in additional files',async({page})=>{
  const flow=await protocol(page,{illustrated:true,publishPreferred:true});await open(page,flow.project.id);
  await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
  const guide=page.getByRole('link',{name:'Build guide PDF · revision 1',exact:true});
  await expect(guide).toHaveCount(1);
  await expect(guide).toHaveAttribute('href','/api/v1/artifacts/plans-pdf/download');
  await expect(page.getByRole('region',{name:'Documents and project package'})).toContainText('Technical fabrication method complete');
  await expect(page.getByRole('link',{name:/Download cut list|Plans cut list CSV/})).toHaveCount(1);
  await page.getByText(/^(All|Additional) revision files$/).click();
  const hrefs=await page.getByRole('link').evaluateAll(links=>links.map(a=>a.getAttribute('href')!).filter(href=>href.includes('/api/v1/artifacts/')));
  expect(hrefs.length).toBeGreaterThan(4);
  expect(new Set(hrefs).size).toBe(hrefs.length);
});

test('ready plans lead with the frozen ZIP and keep rechecking secondary',async({page})=>{
  await page.setViewportSize({width:1280,height:900});
  const flow=await protocol(page,{illustrated:true,publishPreferred:true});await open(page,flow.project.id);
  const action=page.getByRole('button',{name:'Get plans · revision 1',exact:true});
  await page.mouse.move(0,0);
  const primaryColor=await action.evaluate(element=>getComputedStyle(element).backgroundColor);
  await action.click();
  await page.mouse.move(0,0);
  const download=page.getByRole('link',{name:'Download plans ZIP · revision 1',exact:true});
  await expect(download).toHaveCount(1);
  await expect(download).toHaveAttribute('href','/api/v1/artifacts/plans-zip-artifact/download');
  expect(await download.evaluate(element=>getComputedStyle(element).backgroundColor)).toBe(primaryColor);
  const check=page.getByRole('button',{name:'Check plans · revision 1',exact:true});
  await expect(check).toBeEnabled();
  expect(await check.evaluate(element=>getComputedStyle(element).backgroundColor)).not.toBe(primaryColor);
  await expect(page.getByRole('button',{name:'Get plans · revision 1',exact:true})).toHaveCount(0);
  await page.getByRole('region',{name:'Get plans',exact:true}).focus();
  await page.keyboard.press('Tab');await expect(download).toBeFocused();
  await page.keyboard.press('Tab');await expect(check).toBeFocused();
  const requestCount=flow.requests.length;
  const checked=page.waitForResponse(response=>response.url().endsWith('/manifest?artifact_set_id=plans-stock')&&response.request().method()==='GET');
  await check.press('Enter');
  expect((await checked).status()).toBe(200);
  await expect(page.getByRole('status',{name:'Plans progress'})).toHaveText('Plans ready · revision 1');
  await expect(download).toHaveCount(1);
  await expect(download).toHaveAttribute('href','/api/v1/artifacts/plans-zip-artifact/download');
  expect(flow.requests).toHaveLength(requestCount);
});

for(const width of [320,390]){
  test(`phone controls have comfortable targets and preserve view operations at ${width}px`,async({page})=>{
    await page.setViewportSize({width,height:844});
    const flow=await protocol(page,{illustrated:true});await open(page,flow.project.id);
    const controls=[
      page.getByRole('button',{name:'New bookcase',exact:true}),
      page.getByLabel('Saved projects'),page.getByLabel('Project name'),
      page.getByLabel('Outside width',{exact:true}),page.getByLabel('Display units'),
      page.getByRole('button',{name:'Get plans · revision 1',exact:true}),
      ...['Front','Side','Top','Isometric','Fit','Hide selected','Isolate','Restore'].map(name=>page.getByRole('button',{name,exact:true})),
      page.getByLabel('Explode view'),page.getByRole('button',{name:'Select Left side (side_left)',exact:true}),
      page.getByRole('link',{name:'Download cut list · revision 1',exact:true}),
      page.getByRole('link',{name:'Plans',exact:true}),
    ];
    for(const control of controls){
      const bounds=await control.boundingBox();
      expect(bounds).not.toBeNull();
      expect(bounds!.height).toBeGreaterThanOrEqual(44);
      expect(bounds!.width).toBeGreaterThanOrEqual(44);
    }
    expect(await page.getByLabel('Outside width',{exact:true}).evaluate(element=>Number.parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThanOrEqual(16);
    expect(await page.getByRole('button',{name:'Fit',exact:true}).evaluate(element=>Number.parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThanOrEqual(14);
    await page.getByRole('button',{name:'Select Left side (side_left)',exact:true}).press('Enter');
    await expect(page.getByTestId('selected-ids')).toHaveText('side_left');
    await page.getByRole('button',{name:'Hide selected',exact:true}).press('Enter');
    await expect(page.getByTestId('visible-instances')).toHaveText('6 panels visible');
    await page.getByRole('button',{name:'Restore',exact:true}).press('Space');
    await expect(page.getByTestId('visible-instances')).toHaveText('7 panels visible');
    await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
    const download=page.getByRole('link',{name:'Download plans ZIP · revision 1',exact:true});
    await expect(download).toBeVisible();
    for(const name of ['Download plans ZIP','Build guide PDF','Stock layout and cut sequence PDF']){
      const link=page.getByRole('link',{name:name+' · revision 1',exact:true});
      const bounds=await link.boundingBox();
      expect(bounds!.height).toBeGreaterThanOrEqual(44);
      expect(bounds!.width).toBeGreaterThanOrEqual(44);
    }
    await page.getByRole('link',{name:'Plans',exact:true}).press('Enter');
    await page.keyboard.press('Tab');
    await expect(download).toBeFocused();await expect(download).toBeInViewport();
    expect(await download.evaluate(element=>getComputedStyle(element).outlineStyle)).not.toBe('none');
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  });
}

for(const [illustrated,methodStatus] of [[false,'complete'],[true,'incompatible'],[true,'recipe_unselected']] as const){
  test(`a ${methodStatus} packet with illustrated marker ${illustrated} keeps an honest design-PDF label`,async({page})=>{
    const flow=await protocol(page,{illustrated,methodStatus,publishPreferred:true});await open(page,flow.project.id);
    await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
    await expect(page.getByRole('link',{name:'Measured design PDF · revision 1',exact:true})).toHaveAttribute('href','/api/v1/artifacts/plans-pdf/download');
    await expect(page.getByRole('link',{name:/Build guide PDF/})).toHaveCount(0);
  });
}

test('plans and individual outputs lock each other while requests or jobs are pending',async({page})=>{
  const flow=await protocol(page,{holdDocuments:true});await open(page,flow.project.id);
  await page.getByText('Individual output tools',{exact:true}).click();
  await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
  await expect(page.getByRole('button',{name:/^Generate measured PDF/})).toBeDisabled();
  await expect(page.getByRole('button',{name:/^Plan stock and cost/})).toBeDisabled();
  await page.getByRole('button',{name:'Cancel plans',exact:true}).click();
  const retry=page.getByRole('button',{name:'Retry plans · revision 1',exact:true});
  await expect(retry).toBeEnabled();
  let release!:()=>void;const acknowledgement=new Promise<void>(resolve=>{release=resolve;});
  await page.route('**/api/v1/revisions/'+flow.container.revision.id+'/jobs',async route=>{
    if(!route.request().postDataJSON().idempotency_key.startsWith('plans:'))await acknowledgement;
    await route.fallback();
  });
  try{
    await page.getByRole('button',{name:/^Generate measured PDF/}).click();
    await expect(retry).toBeDisabled();
  }finally{release();}
  await expect(page.getByRole('button',{name:'Cancel output job',exact:true})).toBeVisible();
  await expect(retry).toBeDisabled();
  await page.getByRole('button',{name:'Cancel output job',exact:true}).click();
  await expect(retry).toBeEnabled();
});

test('checking saved plans locks individual output submission until recovery finishes',async({page})=>{
  const flow=await protocol(page);await open(page,flow.project.id);
  let release!:()=>void;const recovery=new Promise<void>(resolve=>{release=resolve;});let reads=0;
  await page.route('**/api/v1/revisions/'+flow.container.revision.id,async route=>{
    if(++reads>1)await recovery;
    await route.fallback();
  });
  try{
    await page.reload();await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
    await page.getByText('Individual output tools',{exact:true}).click();
    await expect(page.getByRole('button',{name:/^Generate measured PDF/})).toBeDisabled();
  }finally{release();}
  await expect(page.getByRole('button',{name:/^Generate measured PDF/})).toBeEnabled();
});

test('reopening during an individual output restores its lock and cancel control',async({page})=>{
  const flow=await protocol(page,{holdDocuments:true});await open(page,flow.project.id);
  await page.getByText('Individual output tools',{exact:true}).click();
  await page.getByRole('button',{name:/^Generate measured PDF/}).click();
  await expect(page.getByRole('button',{name:'Cancel output job',exact:true})).toBeVisible();
  await page.reload();await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
  await expect(page.getByRole('button',{name:'Get plans · revision 1',exact:true})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Cancel output job',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Cancel output job',exact:true}).click();
  await expect(page.getByRole('button',{name:'Get plans · revision 1',exact:true})).toBeEnabled();
});

test('a lost individual acknowledgement retains the lock and reconnects with the same request',async({page})=>{
  const flow=await protocol(page,{holdDocuments:true,loseIndividualAck:true});await open(page,flow.project.id);
  await page.getByText('Individual output tools',{exact:true}).click();
  await page.getByRole('button',{name:/^Generate measured PDF/}).click();
  await expect(page.getByRole('alert')).toBeVisible();
  const action=page.getByRole('button',{name:'Get plans · revision 1',exact:true});
  await expect(action).toBeDisabled();
  await page.getByRole('button',{name:'Reconnect output',exact:true}).click();
  await expect(page.getByRole('button',{name:'Cancel output job',exact:true})).toBeVisible();
  expect(flow.jobs).toHaveLength(1);expect(flow.requests).toHaveLength(2);
  expect(flow.requests[1]).toEqual(flow.requests[0]);
  await expect(action).toBeDisabled();
  await page.getByRole('button',{name:'Cancel output job',exact:true}).click();
  await expect(action).toBeEnabled();
});

test('a newer same-revision output stays additional while plans keep their exact bundled PDF',async({page})=>{
  const flow=await protocol(page,{illustrated:true,publishPreferred:true});await open(page,flow.project.id);
  await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
  await expect(page.getByRole('link',{name:'Download plans ZIP · revision 1',exact:true})).toBeVisible();
  const newer=structuredClone(flow.sets.get('plans-stock')!);newer.artifact_set_id='newer-individual-output';
  newer.artifacts=newer.artifacts.map(a=>a.relative_path==='design-packet.pdf'?{...a,artifact_id:'newer-pdf'}:a);
  await page.route('**/api/v1/revisions/'+flow.container.revision.id+'/manifest',route=>route.fulfill({json:{artifact_set_id:newer.artifact_set_id,manifest:newer}}));
  await page.reload();
  const guide=page.getByRole('link',{name:'Build guide PDF · revision 1',exact:true});
  await expect(guide).toHaveCount(1);await expect(guide).toHaveAttribute('href','/api/v1/artifacts/plans-pdf/download');
  await page.getByText('Additional revision files',{exact:true}).click();
  await expect(page.getByRole('link',{name:'design-packet.pdf',exact:true})).toHaveAttribute('href','/api/v1/artifacts/newer-pdf/download');
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
  await expect(page.getByRole('link',{name:'Measured design PDF · revision 1',exact:true})).toHaveAttribute('href','/api/v1/artifacts/plans-pdf/download');
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
  await expect(page.getByRole('button',{name:'Up to date',exact:true})).toBeDisabled();
  for(const [label,value] of [['Outside width','36 in'],['Outside height','42 in'],['Outside depth','14 in'],['Actual main thickness (mm)','19 mm']])await page.getByLabel(label,{exact:true}).fill(value);
  await page.getByLabel('Fixed shelves',{exact:true}).selectOption('3');
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Update design',exact:true}).click();
  await expect(page.getByTestId('model-revision')).toContainText('revision 2',{timeout:120000});
  await expect(page.getByTestId('asset-loaded')).toHaveText('8 part instances loaded');
  await expect(page.getByRole('button',{name:'Up to date',exact:true})).toBeDisabled();
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
  for(const [path,label] of [['design-packet.pdf','Measured design PDF'],['stock-layout.pdf','Stock layout and cut sequence PDF'],['cut-list.csv','Download cut list']]){
    const artifact=manifest.artifacts.find((a:{relative_path:string})=>a.relative_path===path);
    await expect(page.getByRole('link',{name:label+' · revision 2',exact:true})).toHaveAttribute('href','/api/v1/artifacts/'+artifact.artifact_id+'/download');
  }
  expect(await (await page.request.get((await page.getByRole('link',{name:'Download cut list · revision 2',exact:true}).getAttribute('href'))!)).text()).toBe(csvBefore);
  await page.reload();
  // Reopening verifies saved manifest hashes before exposing the frozen bundle.
  await expect(page.getByRole('status',{name:'Plans progress'})).toHaveText('Plans ready · revision 2',{timeout:30000});
  await expect(download).toBeVisible();
  expect((await (await page.request.get('/api/v1/revisions/'+revisionId)).json()).jobs.filter((job:Job)=>job.idempotency_key?.startsWith('plans:'))).toHaveLength(3);
  await expect(page.getByRole('button',{name:'Up to date',exact:true})).toBeDisabled();
  const jobIds=(await (await page.request.get('/api/v1/revisions/'+revisionId)).json()).jobs.map((job:Job)=>job.id);
  await page.getByLabel('Outside width',{exact:true}).press('Enter');await page.locator('form').dispatchEvent('submit');
  expect((await (await page.request.get('/api/v1/revisions/'+revisionId)).json()).jobs.map((job:Job)=>job.id)).toEqual(jobIds);
  await download.scrollIntoViewIfNeeded();await page.screenshot({path:'tests/evidence/get-plans-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});await download.focus();await expect(download).toBeFocused();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:'tests/evidence/get-plans-narrow.png',fullPage:true});
});
