import {test,expect} from '@playwright/test';

test('project-list refresh failure does not detach the opened project from generation',async({page})=>{
  const session=await (await page.request.get('/api/v1/session')).json();
  const spec=(await (await page.request.get('/api/v1/templates')).json()).templates[0].default_spec;
  const title='Checkpoint navigation '+Date.now();
  const createdResponse=await page.request.post('/api/v1/projects',{data:{title,spec},headers:{'X-Woodwork-CSRF':session.csrf_token}});
  expect(createdResponse.ok()).toBe(true);
  const created=await createdResponse.json();
  const primary=(await (await page.request.get('/api/v1/projects')).json()).projects.find((p:{title:string})=>p.title==='Recovery diagnostic');
  expect(primary).toBeTruthy();
  await page.goto('/');
  await page.getByLabel('Saved projects').selectOption(primary.id);
  await expect(page.getByTestId('model-revision')).toBeVisible();
  let failed=false;
  await page.route('**/api/v1/projects',route=>{
    if(route.request().method()==='GET'){failed=true;return route.abort('failed');}
    return route.continue();
  });
  const job={id:'checkpoint-navigation-job',revision_id:created.revision.id,kind:'generate',state:'running',stage:'generating_side_panels',started_at:new Date().toISOString()};
  await page.route('**/api/v1/revisions/'+created.revision.id+'/jobs',route=>route.fulfill({json:{job}}));
  await page.route('**/api/v1/jobs/'+job.id,route=>route.fulfill({json:{job}}));
  await page.getByLabel('Saved projects').selectOption(created.project.id);
  await expect(page.getByRole('heading',{name:title,exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
  expect(failed).toBe(true);
  await page.getByRole('button',{name:'Update design',exact:true}).click();
  await expect(page.getByText('Building side panels',{exact:true})).toBeVisible();
});

test('manual editing and generation remain available when browser storage is disabled',async({page})=>{
  await page.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Storage disabled','SecurityError');}}));
  const job={id:'checkpoint-storage-job',kind:'generate',state:'running',stage:'generating_side_panels',started_at:new Date().toISOString()};
  await page.route('**/api/v1/revisions/*/jobs',route=>route.fulfill({json:{job}}));
  await page.route('**/api/v1/jobs/'+job.id,route=>route.fulfill({json:{job}}));
  await page.goto('/');
  await expect(page.getByLabel('Project name')).toBeVisible();
  await page.getByLabel('Project name').fill('Checkpoint storage '+Date.now());
  await page.getByRole('button',{name:'Create design',exact:true}).click();
  await expect(page.getByText('Building side panels',{exact:true})).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
});
