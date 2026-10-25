import {test,expect,type Page} from '@playwright/test';
import {fileURLToPath} from 'node:url';
import type {Project} from '../src/api';

test.beforeEach(async({page})=>{
  await page.route('**/*',route=>['127.0.0.1','localhost','[::1]'].includes(new URL(route.request().url()).hostname)?route.continue():route.abort());
});

async function sample(page:Page){
  const {projects}=await (await page.request.get('/api/v1/projects')).json();
  const project=projects.find((entry:Project)=>entry.title==='Recovery diagnostic') as Project|undefined;
  expect(project,'Use an isolated store seeded with genuine geometry').toBeTruthy();
  return project!;
}

async function openSample(page:Page){
  const project=await sample(page);
  await page.goto('/');
  await page.getByLabel('Saved projects').selectOption(project.id);
  await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
  const revert=page.getByRole('button',{name:'Revert draft',exact:true});
  if(await revert.count())await revert.click();
  await expect(page.getByRole('button',{name:'Up to date',exact:true})).toBeDisabled();
  return project;
}

test('a missing remembered project offers a new bookcase without discarding its cached draft',async({page})=>{
  const missingId='missing-recovery-project';
  const draft=JSON.stringify({base_revision_id:'preserved-base',raw:{measurements:{outside_width:'keep this draft'}}});
  const before=(await (await page.request.get('/api/v1/projects')).json()).projects;
  await page.addInitScript(({id,draft})=>{
    localStorage.setItem('woodwork-last-project',id);
    localStorage.setItem('woodwork-local-draft-'+id,draft);
  },{id:missingId,draft});
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('This saved project is not available in this local store.');
  await expect(page.getByText('Connect the local service to load the installed template and your saved projects.',{exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Reconnect local service',exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'Try opening project again',exact:true}).focus();
  await page.keyboard.press('Tab');
  const start=page.getByRole('button',{name:'Start a new bookcase',exact:true});
  await expect(start).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('30 in');
  await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeEnabled();
  expect(await page.evaluate(id=>localStorage.getItem('woodwork-local-draft-'+id),missingId)).toBe(draft);
  expect((await (await page.request.get('/api/v1/projects')).json()).projects).toEqual(before);
});

test('retrying a missing project opens it once its record is available again',async({page})=>{
  const project=await sample(page);
  let missing=true;
  await page.addInitScript(id=>localStorage.setItem('woodwork-last-project',id),project.id);
  await page.route('**/api/v1/projects/'+project.id,route=>missing?route.fulfill({status:404,json:{error:{code:'NOT_FOUND',message:'The requested record was not found.'}}}):route.continue());
  await page.goto('/');
  await expect(page.getByRole('button',{name:'Try opening project again',exact:true})).toBeVisible();
  missing=false;
  await page.getByRole('button',{name:'Try opening project again',exact:true}).click();
  await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
  await expect(page.getByRole('alert')).toHaveCount(0);
  expect((await (await page.request.get('/api/v1/projects/'+project.id)).json()).project.latest_accepted_revision_id).toBe(project.latest_accepted_revision_id);
});

test('a project that disappears while open keeps its unsaved draft through retry',async({page})=>{
  const project=await openSample(page);
  await page.getByLabel('Outside width',{exact:true}).fill('35 in');
  let missing=true;
  for(const path of ['/api/v1/projects/'+project.id,'/api/v1/projects/'+project.id+'/draft']){
    await page.route('**'+path,route=>missing?route.fulfill({status:404,json:{error:{code:'NOT_FOUND',message:'The requested record was not found.'}}}):route.continue());
  }
  await page.getByRole('button',{name:'Reopen saved project',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('This saved project is not available in this local store.');
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('35 in');
  await expect(page.getByTestId('model-size')).toContainText('30 in W');
  missing=false;
  await page.getByRole('button',{name:'Try opening project again',exact:true}).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('35 in');
  expect((await (await page.request.get('/api/v1/projects/'+project.id)).json()).project.latest_accepted_revision_id).toBe(project.latest_accepted_revision_id);
  await page.getByRole('button',{name:'Revert draft',exact:true}).click();
});

for(const failure of ['empty gateway','HTML gateway','malformed JSON'] as const){
  test(`${failure} responses show service recovery instead of parser errors`,async({page})=>{
    let unavailable=true;
    await page.route('**/api/v1/templates',route=>unavailable?route.fulfill({status:failure==='malformed JSON'?200:503,contentType:failure==='HTML gateway'?'text/html':'application/json',body:failure==='HTML gateway'?'<html>Gateway unavailable</html>':failure==='malformed JSON'?'{':''}):route.continue());
    await page.goto('/');
    await expect(page.getByRole('alert')).toContainText('The local service is unavailable.');
    await expect(page.getByRole('alert')).not.toContainText(/Unexpected|JSON|Failed to fetch/);
    const reconnect=page.getByRole('button',{name:'Reconnect local service',exact:true});
    await expect(reconnect).toBeEnabled();
    unavailable=false;
    await reconnect.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeEnabled();
    await expect(page.getByRole('alert')).toHaveCount(0);
  });
}

for(const failure of ['network','invalid token response'] as const){
  test(`${failure} during session setup reconnects without resetting a new design`,async({page})=>{
    let unavailable=true;
    await page.route('**/api/v1/session',route=>unavailable?failure==='network'?route.abort('failed'):route.fulfill({json:{}}):route.continue());
    await page.goto('/');
    await expect(page.getByLabel('Outside width',{exact:true})).toBeVisible();
    await page.getByLabel('Project name').fill('Unsaved recovery design');
    await page.getByLabel('Outside width',{exact:true}).fill('35 1/2 in');
    await expect(page.getByRole('alert')).toContainText('The local service is unavailable.');
    unavailable=false;
    await page.getByRole('button',{name:'Reconnect local service',exact:true}).click();
    await expect(page.getByLabel('Project name')).toHaveValue('Unsaved recovery design');
    await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('35 1/2 in');
    await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeEnabled();
    await expect(page.getByRole('alert')).toHaveCount(0);
  });
}

for(const failure of ['empty gateway','HTML gateway','network'] as const){
  test(`a saved project's ${failure} outage preserves its draft model and downloads`,async({page})=>{
    const project=await openSample(page);
    const before=await (await page.request.get('/api/v1/revisions/'+project.latest_successful_revision_id)).json();
    const csv=page.getByRole('link',{name:/Download cut list/});
    const url=(await csv.getAttribute('href'))!;
    const bytes=await (await page.request.get(url)).body();
    let unavailable=true;
    await page.route('**/api/v1/**',route=>unavailable?failure==='network'?route.abort('failed'):route.fulfill({status:503,contentType:'text/html',body:failure==='HTML gateway'?'<html>Service offline</html>':''}):route.continue());
    await page.getByLabel('Outside width',{exact:true}).fill('40 in');
    await expect(page.getByRole('alert')).toContainText('The local service is unavailable.');
    await expect(page.getByText(/Draft kept here until the local service reconnects/)).toBeVisible();
    await expect(page.getByRole('region',{name:'Draft change summary'})).toContainText('Reconnect the local service to check these measurements.');
    await expect(page.getByText('Correct the measurements to see the resulting parts.',{exact:true})).toHaveCount(0);
    await expect(page.getByTestId('model-size')).toContainText('30 in W');
    await expect(csv).toHaveAttribute('href',url);
    await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('40 in');
    expect(await (await page.request.get(url)).body()).toEqual(bytes);
    unavailable=false;
    await page.getByRole('button',{name:'Reconnect local service',exact:true}).click();
    await expect(page.getByRole('alert')).toHaveCount(0);
    await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('40 in');
    await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
    await expect(page.getByTestId('model-size')).toContainText('30 in W');
    expect((await (await page.request.get('/api/v1/revisions/'+project.latest_successful_revision_id)).json()).jobs).toEqual(before.jobs);
    expect((await (await page.request.get('/api/v1/projects/'+project.id)).json()).project.latest_accepted_revision_id).toBe(project.latest_accepted_revision_id);
    expect(await (await page.request.get(url)).body()).toEqual(bytes);
    await page.getByRole('button',{name:'Revert draft',exact:true}).click();
  });
}

test('a temporary project lookup outage keeps the remembered project and retries it',async({page})=>{
  const project=await sample(page);
  let unavailable=true;
  await page.addInitScript(id=>localStorage.setItem('woodwork-last-project',id),project.id);
  await page.route('**/api/v1/projects/'+project.id,route=>unavailable?route.fulfill({status:503,body:''}):route.continue());
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('The local service is unavailable.');
  await expect(page.getByRole('button',{name:'Start a new bookcase',exact:true})).toHaveCount(0);
  expect(await page.evaluate(()=>localStorage.getItem('woodwork-last-project'))).toBe(project.id);
  unavailable=false;
  await page.getByRole('button',{name:'Reconnect local service',exact:true}).click();
  await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
  await expect(page.getByLabel('Saved projects')).toHaveValue(project.id);
});

test('a missing revision is not misreported as a missing project',async({page})=>{
  const project=await sample(page);
  await page.addInitScript(id=>localStorage.setItem('woodwork-last-project',id),project.id);
  await page.route('**/api/v1/revisions/'+project.latest_accepted_revision_id,route=>route.fulfill({status:404,json:{error:{code:'NOT_FOUND',message:'The requested record was not found.'}}}));
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('The requested record was not found.');
  await expect(page.getByRole('button',{name:'Start a new bookcase',exact:true})).toHaveCount(0);
  expect(await page.evaluate(()=>localStorage.getItem('woodwork-last-project'))).toBe(project.id);
});

test('non-JSON upload failures keep the selected ZIP available for validation retry',async({page})=>{
  await page.goto('/');
  await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeEnabled();
  await page.getByText('Import a saved project ZIP',{exact:true}).click();
  await page.getByLabel('Project ZIP file').setInputFiles(fileURLToPath(new URL('../../../samples/reference-bookcase/project.zip',import.meta.url)));
  let unavailable=true;
  await page.route('**/api/v1/imports/validate',route=>unavailable?route.fulfill({status:503,contentType:'text/html',body:'<html>Service offline</html>'}):route.continue());
  await page.getByRole('button',{name:'Validate project ZIP',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('The local service is unavailable.');
  await expect(page.getByRole('alert')).not.toContainText(/Unexpected|JSON/);
  unavailable=false;
  const validation=page.waitForResponse(response=>response.url().endsWith('/api/v1/imports/validate')&&response.request().method()==='POST');
  await page.getByRole('button',{name:'Validate project ZIP',exact:true}).click();
  expect((await validation).status()).toBe(200);
  await expect(page.getByRole('heading',{name:'Package checked',exact:true})).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
});

test('structured validation errors retain their field feedback and do not claim an outage',async({page})=>{
  await page.route('**/api/v1/specs/validate',route=>route.fulfill({status:422,json:{error:{code:'OUTSIDE_WIDTH_INVALID',message:'Outside width must leave room for the side panels.',details:{findings:[{field:'dimensions.outside_width_mm',message:'Outside width must leave room for the side panels.'}]}}}}));
  await page.goto('/');
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveAttribute('aria-invalid','true');
  await expect(page.getByRole('alert')).toContainText('Outside width must leave room for the side panels.');
  await expect(page.getByRole('button',{name:'Reconnect local service',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeDisabled();
});
