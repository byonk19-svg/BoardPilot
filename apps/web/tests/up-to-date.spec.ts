import {test,expect,type Page} from '@playwright/test';
import type {Job,Project,Revision} from '../src/api';

async function sample(page:Page){
  const projects:Project[]=(await (await page.request.get('/api/v1/projects')).json()).projects;
  const project=projects.find(entry=>entry.title==='Recovery diagnostic');
  expect(project,'Use the isolated genuine geometry fixture').toBeTruthy();
  const container:{revision:Revision;jobs:Job[]} = await (await page.request.get('/api/v1/revisions/'+project!.latest_accepted_revision_id)).json();
  return {project:project!,container};
}

async function openSample(page:Page,project:Project){
  await page.goto('/');await page.getByLabel('Saved projects').selectOption(project.id);
  await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
  const revert=page.getByRole('button',{name:'Revert draft',exact:true});
  if(await revert.count())await revert.click();
  await expect(page.getByTestId('draft-summary')).toContainText('Accepted design');
}

test.beforeEach(async({page})=>{
  await page.route('**/*',route=>['127.0.0.1','localhost','[::1]'].includes(new URL(route.request().url()).hostname)?route.continue():route.abort());
});

for(const width of [1280,320,390]){
  test(`an unchanged verified design stays Up to date without submitting at ${width}px`,async({page})=>{
    await page.setViewportSize({width,height:900});
    const {project,container}=await sample(page);
    let submissions=0;
    page.on('request',request=>{if(request.method()==='POST'&&(request.url().endsWith('/jobs')||request.url().endsWith('/revisions')))submissions++;});
    await openSample(page,project);
    const current=page.getByRole('button',{name:'Up to date',exact:true});
    await expect(current).toBeDisabled();
    await expect(page.getByRole('button',{name:'Update design',exact:true})).toHaveCount(0);
    const csv=page.getByRole('link',{name:'Download cut list · revision 1',exact:true});
    const href=(await csv.getAttribute('href'))!;
    const bytes=await (await page.request.get(href)).body();
    const input=page.getByLabel('Outside width',{exact:true});
    await input.press('Enter');await page.locator('form').dispatchEvent('submit');
    await input.fill('762 mm');await expect(current).toBeDisabled();
    await input.fill('36 in');
    await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
    await expect(page.getByText('Changes not applied',{exact:true})).toBeVisible();
    await page.getByRole('button',{name:'Revert draft',exact:true}).click();
    await expect(current).toBeDisabled();
    await page.reload();await expect(current).toBeDisabled();
    await page.getByRole('button',{name:'Reopen saved project',exact:true}).click();
    await expect(current).toBeDisabled();
    expect(submissions).toBe(0);
    await expect(csv).toHaveAttribute('href',href);
    expect(await (await page.request.get(href)).body()).toEqual(bytes);
    const after=await (await page.request.get('/api/v1/revisions/'+container.revision.id)).json();
    expect(after.revision).toEqual(container.revision);
    expect(after.jobs).toEqual(container.jobs);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  });
}

for(const state of ['failed','cancelled','interrupted']){
  test(`Retry remains available after ${state} generation even with an unchanged verified model`,async({page})=>{
    const {project,container}=await sample(page);
    let job:Job={id:'retry-current-'+state,kind:'generate',revision_id:container.revision.id,state,stage:'generating_geometry',diagnostic_code:state==='failed'?'CAD_TIMEOUT':null};
    const submissions:{kind:string;idempotency_key:string}[]=[];
    await page.route('**/api/v1/revisions/'+container.revision.id,route=>route.fulfill({json:{...container,jobs:[job]}}));
    await page.route('**/api/v1/jobs/'+job.id,route=>route.fulfill({json:{job}}));
    await page.route('**/api/v1/revisions/'+container.revision.id+'/jobs',route=>{
      submissions.push(route.request().postDataJSON());
      job={...job,state:'running',stage:'generating_side_panels',diagnostic_code:null};
      return route.fulfill({status:202,json:{job}});
    });
    await page.route('**/api/v1/jobs/'+job.id+'/cancel',route=>{job={...job,state:'cancelled'};return route.fulfill({json:{job}});});
    await openSample(page,project);
    const current=page.getByRole('button',{name:'Up to date',exact:true});
    const retry=page.getByRole('button',{name:'Retry revision 1',exact:true});
    await expect(current).toBeDisabled();await expect(retry).toBeEnabled();
    const csv=page.getByRole('link',{name:'Download cut list · revision 1',exact:true});
    const href=(await csv.getAttribute('href'))!;
    await retry.press('Enter');
    await expect(page.getByText('Building side panels',{exact:true})).toBeVisible();
    await expect(current).toHaveCount(0);
    await expect(page.getByRole('button',{name:'Updating design…',exact:true})).toBeDisabled();
    expect(submissions).toHaveLength(1);expect(submissions[0].kind).toBe('generate');
    expect(submissions[0].idempotency_key).toBeTruthy();
    await page.getByRole('button',{name:'Cancel generation',exact:true}).click();
    await expect(current).toBeDisabled();await expect(retry).toBeEnabled();
    await expect(csv).toHaveAttribute('href',href);
    expect((await (await page.request.get('/api/v1/revisions/'+container.revision.id)).json()).jobs).toEqual(container.jobs);
  });
}

test('new designs and accepted designs without a successful model still offer generation',async({page})=>{
  const session=await (await page.request.get('/api/v1/session')).json();
  const spec=(await (await page.request.get('/api/v1/templates')).json()).templates[0].default_spec;
  await page.goto('/');await page.getByRole('button',{name:'New bookcase',exact:true}).click();
  await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeEnabled();
  await expect(page.getByRole('button',{name:'Up to date',exact:true})).toHaveCount(0);
  const response=await page.request.post('/api/v1/projects',{data:{title:'Unbuilt up-to-date regression '+Date.now(),spec},headers:{'X-Woodwork-CSRF':session.csrf_token}});
  expect(response.ok()).toBe(true);
  const created=await response.json();
  let submissions=0;
  const job:Job={id:'unbuilt-current-job',kind:'generate',revision_id:created.revision.id,state:'running',stage:'generating_geometry'};
  await page.route('**/api/v1/revisions/'+created.revision.id+'/jobs',route=>{submissions++;return route.fulfill({status:202,json:{job}});});
  await page.route('**/api/v1/jobs/'+job.id,route=>route.fulfill({json:{job}}));
  await page.reload();await page.getByLabel('Saved projects').selectOption(created.project.id);
  const update=page.getByRole('button',{name:'Update design',exact:true});
  await expect(update).toBeEnabled();await update.click();
  await expect(page.getByText('Generating CAD',{exact:true})).toBeVisible();
  expect(submissions).toBe(1);
});

test('an older verified model does not make a newer accepted revision Up to date and Retry targets the newer revision',async({page})=>{
  const {project,container}=await sample(page);
  const revision={...container.revision,id:'pending-current-revision',number:2,parent_id:container.revision.id,preferred_artifact_set_id:null};
  let job:Job={id:'pending-current-job',kind:'generate',revision_id:revision.id,state:'failed',stage:'generating_geometry',diagnostic_code:'CAD_TIMEOUT'};
  let submissions=0;
  await page.route('**/api/v1/projects/'+project.id,route=>route.request().method()==='GET'?route.fulfill({json:{project:{...project,latest_accepted_revision_id:revision.id},draft:null}}):route.continue());
  await page.route('**/api/v1/revisions/'+revision.id,route=>route.fulfill({json:{revision,jobs:[job]}}));
  await page.route('**/api/v1/jobs/'+job.id,route=>route.fulfill({json:{job}}));
  await page.route('**/api/v1/revisions/'+revision.id+'/jobs',route=>{submissions++;job={...job,state:'running',stage:'generating_side_panels'};return route.fulfill({status:202,json:{job}});});
  await openSample(page,project);
  await expect(page.getByTestId('model-revision')).toContainText('revision 1');
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
  await expect(page.getByRole('button',{name:'Up to date',exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'Retry revision 2',exact:true}).click();
  await expect(page.getByText('Building side panels',{exact:true})).toBeVisible();
  expect(submissions).toBe(1);
});

test('a manifest without passed geometry does not claim the design is Up to date',async({page})=>{
  const {project,container}=await sample(page);
  const saved=await (await page.request.get('/api/v1/revisions/'+container.revision.id+'/manifest')).json();
  saved.manifest.validation.geometry='not_run';
  await page.route('**/api/v1/revisions/'+container.revision.id+'/manifest',route=>route.fulfill({json:saved}));
  await openSample(page,project);
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
  await expect(page.getByRole('button',{name:'Up to date',exact:true})).toHaveCount(0);
});
