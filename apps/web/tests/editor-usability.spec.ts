import {test,expect,type Page} from '@playwright/test';

async function openVerifiedSample(page:Page){
  const projects=(await (await page.request.get('/api/v1/projects')).json()).projects;
  const sample=projects.find((project:{title:string})=>project.title==='Recovery diagnostic');
  expect(sample,'Use the isolated genuine geometry fixture').toBeTruthy();
  await page.goto('/');
  await page.getByLabel('Saved projects').selectOption(sample.id);
  await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
  const revert=page.getByRole('button',{name:'Revert draft',exact:true});
  if(await revert.count())await revert.click({timeout:5000});
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
}

test('basic measurements stay visible while specialist controls are disclosed on demand',async({page})=>{
  await openVerifiedSample(page);
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
  for(const label of ['Outside width','Outside height','Outside depth','Fixed shelves','Actual main thickness (mm)','Actual back thickness (mm)']){
    await expect(page.getByLabel(label,{exact:true})).toBeVisible();
  }
  await expect(page.getByLabel('Main nominal label',{exact:true})).toBeHidden();
  await expect(page.getByLabel('Main face grain',{exact:true})).toBeHidden();
  await expect(page.getByLabel('Installed recipe',{exact:true})).toBeHidden();
  await expect(page.getByTestId('recipe-state')).toContainText('Assembly method still needed');
  await page.getByText('Advanced settings',{exact:true}).click();
  for(const label of ['Main nominal label','Main face grain','Installed recipe','Saw kerf (mm)','Sheet 1 price (USD)','Project paper size']){
    await expect(page.getByLabel(label,{exact:true})).toBeVisible();
  }
  await page.getByText('Advanced settings',{exact:true}).click();
  await expect(page.getByLabel('Saw kerf (mm)',{exact:true})).toBeHidden();
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeVisible();
});

test('invalid measurements remain recoverable and errors in Advanced reveal their controls',async({page})=>{
  await openVerifiedSample(page);
  await page.getByLabel('Outside width',{exact:true}).fill('1/3');
  await expect(page.getByRole('alert')).toContainText('denominator');
  await expect(page.getByTestId('recipe-state')).toContainText('Assembly method still needed');
  await page.getByLabel('Display units').selectOption('mm');
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('1/3 in');
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeDisabled();
  await page.getByRole('button',{name:'Revert draft',exact:true}).click();
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
  await page.getByText('Advanced settings',{exact:true}).click();
  await page.getByLabel('Saw kerf (mm)',{exact:true}).fill('-2 mm');
  await page.getByText('Advanced settings',{exact:true}).click();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByLabel('Saw kerf (mm)',{exact:true})).toBeVisible();
  await expect(page.getByLabel('Saw kerf (mm)',{exact:true})).toHaveAttribute('aria-invalid','true');
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeDisabled();
  await page.getByLabel('Saw kerf (mm)',{exact:true}).fill('3.2 mm');
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
  await page.getByLabel('Installed recipe',{exact:true}).selectOption({index:1});
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
  await page.getByLabel('Outside width',{exact:true}).fill('1/3');
  await expect(page.getByRole('alert')).toContainText('denominator');
  await expect(page.getByTestId('recipe-state')).toHaveText('Assembly method selected; correct measurements to recheck fabrication readiness.');
  await page.getByRole('button',{name:'Revert draft',exact:true}).click();
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
});

test('a recovered draft uses its own precision without relabeling the saved cut list',async({page})=>{
  await openVerifiedSample(page);
  await expect(page.getByText('Draft saved locally.',{exact:true})).toBeVisible();
  const projectId=await page.getByLabel('Saved projects').inputValue();
  const container=await (await page.request.get('/api/v1/projects/'+projectId)).json();
  expect(container.draft).toBeTruthy();
  container.draft.raw.spec.display.fraction_denominator=16;
  await page.route('**/api/v1/projects/'+projectId,route=>route.request().method()==='GET'?route.fulfill({json:container}):route.continue());
  await page.reload();
  await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
  await expect(page.getByTestId('cut-list')).toContainText('28 37/64 in');
  await page.getByText('Measurement details',{exact:true}).click();
  await expect(page.locator('.revision-details')).toContainText('28 37/64 in');
  await page.getByLabel('Outside width',{exact:true}).fill('36 in');
  await expect(page.getByTestId('draft-summary')).toContainText('34 9/16 in');
  await expect(page.getByTestId('cut-list')).toContainText('28 37/64 in');
  await page.unroute('**/api/v1/projects/'+projectId);
  await page.getByRole('button',{name:'Revert draft',exact:true}).click();
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
});

test('display units preserve a pending measurement while the model and cut list retain their saved dimensions',async({page})=>{
  await openVerifiedSample(page);
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
  await expect(page.getByTestId('model-size')).toContainText('30 in W × 36 in H × 12 in D');
  const csvLink=page.getByRole('link',{name:/Download cut list/});
  const href=(await csvLink.getAttribute('href'))!;
  const before=await (await page.request.get(href)).text();
  await expect(page.getByTestId('cut-list')).toContainText('28 37/64 in');
  await page.getByLabel('Display units').selectOption('mm');
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('762 mm');
  await expect(page.getByTestId('model-size')).toContainText('762 mm W × 914.4 mm H × 304.8 mm D');
  await page.getByLabel('Outside width',{exact:true}).fill('914.4 mm');
  await expect(page.getByTestId('draft-summary')).toContainText('878.4');
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
  await page.getByLabel('Display units').selectOption('in');
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('36 in');
  await expect(page.getByTestId('model-size')).toContainText('30 in W × 36 in H × 12 in D');
  await expect(page.getByTestId('cut-list')).toContainText('28 37/64 in');
  await expect(page.getByTestId('cut-list')).toContainText('726');
  await expect(csvLink).toHaveAttribute('href',href);
  expect(await (await page.request.get(href)).text()).toBe(before);
  await expect(page.getByText('Draft saved locally.',{exact:true})).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('36 in');
  await expect(page.getByTestId('model-size')).toContainText('30 in W');
});

test('the basic editor creates coherent genuine CAD and reaches the model and cut list on narrow screens',async({page})=>{
  test.setTimeout(180000);
  await page.goto('/');
  await page.getByRole('button',{name:'New bookcase',exact:true}).click();
  await page.getByLabel('Project name').fill('Simple editor acceptance '+Date.now());
  await page.getByLabel('Outside width',{exact:true}).fill('36 in');
  await page.getByLabel('Outside height',{exact:true}).fill('42 in');
  await page.getByLabel('Outside depth',{exact:true}).fill('14 in');
  await page.getByLabel('Fixed shelves',{exact:true}).selectOption('3');
  await page.getByLabel('Actual main thickness (mm)',{exact:true}).fill('19 mm');
  await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Create design',exact:true}).click();
  await expect(page.getByTestId('asset-loaded')).toHaveText('8 part instances loaded',{timeout:120000});
  await expect(page.getByTestId('model-size')).toContainText('36 in W × 42 in H × 14 in D');
  const csv=await (await page.request.get((await page.getByRole('link',{name:/Download cut list/}).getAttribute('href'))!)).text();
  expect(csv).toContain(',876.4,349.6,');
  const projectId=await page.getByLabel('Saved projects').inputValue();
  const {project}=await (await page.request.get('/api/v1/projects/'+projectId)).json();
  expect(project.latest_successful_revision_id).toBe(project.latest_accepted_revision_id);
  const {revision,jobs}=await (await page.request.get('/api/v1/revisions/'+project.latest_accepted_revision_id)).json();
  expect(csv).toContain(revision.id);
  expect(revision.spec.materials.main.actual_thickness_mm).toBe('19');
  expect(revision.resolved.part_instance_count).toBe(8);
  expect(jobs.find((job:{kind:string})=>job.kind==='generate').metrics.elapsed_seconds).toBeLessThan(120);
  await expect(page.getByTestId('cut-list')).toContainText('876.4 × 349.6 × 19 mm');
  await expect(page.getByLabel('Main nominal label',{exact:true})).toBeHidden();
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Update design',exact:true}).hover();
  await page.screenshot({path:'tests/evidence/simple-editor-desktop.png',fullPage:true});
  for(const width of [535,390]){
    await page.setViewportSize({width,height:844});
    await page.getByRole('link',{name:'3D view',exact:true}).press('Enter');
    await expect(page.getByTestId('model-size')).toBeInViewport();
    await page.getByRole('link',{name:'Cut list',exact:true}).press('Enter');
    await expect(page.getByRole('heading',{name:'Cut list revision 1',exact:true})).toBeInViewport();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  }
  await page.screenshot({path:'tests/evidence/simple-editor-narrow.png',fullPage:true});
});
