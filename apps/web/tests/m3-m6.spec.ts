import {test,expect,type APIRequestContext,type Page} from '@playwright/test';
import {readFile} from 'node:fs/promises';

test.setTimeout(720_000);

async function mutate(request:APIRequestContext,path:string,data:unknown){
  const session=await (await request.get('/api/v1/session')).json();
  const response=await request.post('/api/v1'+path,{data,headers:{'X-Woodwork-CSRF':session.csrf_token}});
  expect(response.ok(),await response.text()).toBe(true);
  return response.json();
}
async function waitJob(request:APIRequestContext,jobId:string){
  let record:{job:{state:string;diagnostic_code?:string}};
  await expect.poll(async()=>{record=await (await request.get('/api/v1/jobs/'+jobId)).json();return record.job.state;},{timeout:180_000,intervals:[1000,1500]}).toMatch(/succeeded|failed|cancelled|interrupted/);
  record=await (await request.get('/api/v1/jobs/'+jobId)).json();
  expect(record.job.state,record.job.diagnostic_code).toBe('succeeded');
}
async function authoredProject(page:Page){
  const sample=process.env.WOODWORK_AUTHORED_SAMPLE_PATH;
  if(sample){
    const record=JSON.parse(await readFile(sample,'utf8'));
    const current=await page.request.get('/api/v1/projects/'+record.project.id);
    if(current.ok())return (await current.json()).project;
  }
  const template=(await (await page.request.get('/api/v1/templates')).json()).templates[0];
  expect(template.recipes.length,'Install the authored recipe before running its browser acceptance').toBeGreaterThan(0);
  const spec=structuredClone(template.default_spec);
  spec.project_name='Browser authored '+Date.now();
  spec.dimensions.outside_depth_mm='355.6';spec.materials.main.actual_thickness_mm='19.05';spec.materials.back.actual_thickness_mm='6.35';
  spec.documents.paper_size='a4';spec.construction.recipe={id:template.recipes[0].id,version:template.recipes[0].version};
  const created=await mutate(page.request,'/projects',{title:spec.project_name,spec});
  const generated=await mutate(page.request,'/revisions/'+created.revision.id+'/jobs',{kind:'generate',idempotency_key:crypto.randomUUID()});
  await waitJob(page.request,generated.job.id);
  const manifest=(await (await page.request.get('/api/v1/revisions/'+created.revision.id+'/manifest')).json()).manifest;
  const documents=await mutate(page.request,'/revisions/'+created.revision.id+'/jobs',{kind:'documents',source_artifact_set_id:manifest.artifact_set_id,idempotency_key:crypto.randomUUID()});
  await waitJob(page.request,documents.job.id);
  return created.project;
}
async function showAuthored(page:Page,projectId:string){
  await page.goto('/');await page.getByLabel('Saved projects').selectOption(projectId);
  await expect(page.getByTestId('model-revision')).toBeVisible();
  // Reopening first revalidates the form. Its temporary Revert control can
  // disappear when validation finishes, so wait for actionable form controls.
  await expect(page.getByRole('button',{name:/^Update design$/})).toBeEnabled();
  const revert=page.getByRole('button',{name:'Revert draft',exact:true});
  if(await revert.count())await revert.click({timeout:5000});
  // The accepted summary intentionally hides its redundant heading. Verify the
  // accepted state and visible summary instead of requiring that hidden title.
  await expect(page.getByTestId('draft-summary')).toBeVisible();
  await expect(page.getByTestId('draft-summary')).toContainText('Accepted design');
  await expect(page.getByText('Changes not applied',{exact:true})).toHaveCount(0);
  if(await page.locator('details.individual-outputs').getAttribute('open')===null)await page.getByText('Individual output tools',{exact:true}).click();
}

test('authored method, genuine PDF, offline incompatible recipe, proposals and ZIP import rebuild',async({page})=>{
  const authored=await authoredProject(page);
  await showAuthored(page,authored.id);
  await expect(page.getByText('Technical fabrication method complete',{exact:true})).toBeVisible();
  const pdfLink=page.getByRole('link',{name:/^Measured design PDF/});
  await expect(pdfLink).toBeVisible();
  const pdf=await page.request.get((await pdfLink.getAttribute('href'))!);
  expect(pdf.ok()).toBe(true);expect((await pdf.body()).subarray(0,5).toString()).toBe('%PDF-');
  await page.getByRole('button',{name:/^Export project ZIP/}).click();
  await expect(page.getByTestId('project-zip')).toBeVisible({timeout:30_000});
  const download=await page.request.get((await page.getByTestId('project-zip').getAttribute('href'))!);
  const zip=await download.body();expect(zip.subarray(0,2).toString()).toBe('PK');
  await page.getByRole('checkbox',{name:'Enable offline proposal demo'}).check();
  await page.getByLabel('Describe a supported change').fill('What about drawers?');
  await page.getByRole('button',{name:'Review demo proposal',exact:true}).click();
  await expect(page.getByTestId('proposal-explanation')).toContainText('supports an open-front');
  await expect(page.getByRole('button',{name:'Apply reviewed proposal and generate'})).toHaveCount(0);

  await page.getByRole('button',{name:'New bookcase',exact:true}).click();
  await page.getByLabel('Project name').fill('Offline incompatible '+Date.now());
  const recipe=(await (await page.request.get('/api/v1/templates')).json()).templates[0].recipes[0];
  await page.getByText('Advanced settings',{exact:true}).click();
  await page.getByLabel('Installed recipe').selectOption(recipe.id+'@'+recipe.version);
  await expect(page.getByTestId('recipe-state')).toContainText('incompatible');
  await expect(page.getByLabel('Actual main thickness (mm)',{exact:true})).toHaveValue('18 mm');
  await page.getByLabel('Sheet 1 price (USD)',{exact:true}).fill('70.00');
  await page.getByLabel('Sheet 2 price (USD)',{exact:true}).fill('25.00');
  await page.route('**/*',route=>{const host=new URL(route.request().url()).hostname;return ['127.0.0.1','localhost','[::1]'].includes(host)?route.continue():route.abort();});
  await page.getByRole('button',{name:'Create design',exact:true}).click();
  await expect(page.getByTestId('model-revision')).toContainText('revision 1',{timeout:150_000});
  await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
  await expect(page.getByText('Construction incompatible',{exact:true})).toBeVisible();
  await page.getByText('Individual output tools',{exact:true}).click();
  await page.getByRole('button',{name:/^Generate measured PDF/}).click();
  await expect(page.getByRole('link',{name:/^Measured design PDF/})).toBeVisible({timeout:60_000});
  await expect(page.getByRole('link',{name:/^Measured design PDF/})).toHaveAttribute('href',/\/artifacts\//);
  await page.getByRole('button',{name:/^Plan stock and cost/}).click();
  await expect(page.getByTestId('sheet-subtotal')).toHaveText('Sheet purchase subtotal: USD 95.00',{timeout:60_000});
  await expect(page.getByRole('link',{name:/^Stock layout and cut sequence PDF/})).toBeVisible();
  await page.getByRole('checkbox',{name:'Enable offline proposal demo'}).check();
  await page.getByLabel('Describe a supported change').fill('Make the width 36 in');
  await page.getByRole('button',{name:'Review demo proposal',exact:true}).click();
  await expect(page.getByTestId('proposal-review')).toContainText('762 → 914.4 mm');
  await page.getByRole('button',{name:'Apply reviewed proposal and generate'}).click();
  await expect(page.getByTestId('model-revision')).toContainText('revision 2',{timeout:150_000});
  await expect(page.getByTestId('cut-list')).toContainText('878.4');
  await expect(page.getByRole('button',{name:'Apply reviewed proposal and generate'})).toBeDisabled();

  await page.getByRole('button',{name:'New bookcase',exact:true}).click();
  await page.getByText('Import a saved project ZIP',{exact:true}).click();
  await page.getByLabel('Project ZIP file').setInputFiles({name:'genuine-authored.zip',mimeType:'application/zip',buffer:zip});
  await page.getByRole('button',{name:'Validate project ZIP',exact:true}).click();
  await expect(page.getByTestId('import-review')).toContainText('Package checked');
  await page.getByLabel('Imported project name').fill('Imported browser recipe '+Date.now());
  await page.getByRole('button',{name:'Import and rebuild as new local project',exact:true}).click();
  await expect(page.getByTestId('model-revision')).toContainText('revision 1',{timeout:150_000});
  await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
  await expect(page.getByTestId('cut-list')).toContainText('723.9');
  await page.screenshot({path:'tests/evidence/m3-m6-imported-rebuilt.png',fullPage:true});
});

test('hostile proposal text is inert and a stale review cannot apply',async({page})=>{
  const authored=await authoredProject(page);
  await showAuthored(page,authored.id);
  await page.getByRole('checkbox',{name:'Enable offline proposal demo'}).check();
  let injectedResponses=0;
  // The panel refreshes the returned proposal by ID. Keep hostile text present
  // in both responses so the actual reviewed content reaches the XSS checks.
  for(const pattern of ['**/api/v1/projects/*/proposals','**/api/v1/proposals/*'])await page.route(pattern,async route=>{
    const response=await route.fetch();const data=await response.json();
    if(data.proposal?.proposal?.response){data.proposal.proposal.response.explanation='<img src=x onerror="window.__proposalExecuted=true">';injectedResponses++;}
    await route.fulfill({response,json:data});
  });
  await page.getByLabel('Describe a supported change').fill('Make the width 36 in');
  await page.getByRole('button',{name:'Review demo proposal',exact:true}).click();
  await expect.poll(()=>injectedResponses).toBeGreaterThanOrEqual(2);
  await expect(page.getByTestId('proposal-explanation')).toContainText('<img src=x');
  expect(await page.evaluate(()=>!!(window as unknown as {__proposalExecuted?:boolean}).__proposalExecuted)).toBe(false);
  await expect(page.getByTestId('proposal-explanation').locator('img')).toHaveCount(0);
  const current=(await (await page.request.get('/api/v1/projects/'+authored.id)).json()).project;
  const revision=(await (await page.request.get('/api/v1/revisions/'+current.latest_accepted_revision_id)).json()).revision;
  const changed=structuredClone(revision.spec);changed.materials.main.nominal_label='Nominal metadata revised for stale proposal check';
  await mutate(page.request,'/projects/'+authored.id+'/revisions',{base_revision_id:revision.id,spec:changed});
  await page.getByRole('button',{name:'Reopen saved project',exact:true}).click();
  await expect(page.getByText('This proposal is stale.',{exact:false})).toBeVisible();
  await expect(page.getByRole('button',{name:'Apply reviewed proposal and generate'})).toBeDisabled();
  await page.getByLabel('Describe a supported change').fill('timeout');
  await page.getByRole('button',{name:'Revert draft',exact:true}).click();
  await expect(page.getByRole('button',{name:'Review demo proposal',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Review demo proposal',exact:true}).click();
  await expect(page.getByText('The demo timed out.',{exact:false})).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:'tests/evidence/m5-inert-stale-narrow.png',fullPage:true});
});

test('stale draft recovery preserves edits and explicit choices survive immediate reload',async({page})=>{
  const template=(await (await page.request.get('/api/v1/templates')).json()).templates[0];
  const spec=structuredClone(template.default_spec);spec.project_name='Draft recovery '+Date.now();
  const created=await mutate(page.request,'/projects',{title:spec.project_name,spec});
  await page.goto('/');await page.getByLabel('Saved projects').selectOption(created.project.id);
  await page.getByLabel('Outside width',{exact:true}).fill('36 in');
  await expect(page.getByText('Draft saved locally.',{exact:true})).toBeVisible();
  const changed=structuredClone(spec);changed.materials.main.nominal_label='Latest accepted material label';
  const next=await mutate(page.request,'/projects/'+created.project.id+'/revisions',{base_revision_id:created.revision.id,spec:changed});
  await page.getByRole('button',{name:'Reopen saved project',exact:true}).click();
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('36 in');
  await expect(page.getByRole('button',{name:'Use latest revision as base',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Revert draft',exact:true}).click();
  await page.reload();
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('30 in');
  await expect(page.getByText('Accepted revision 2',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Use latest revision as base',exact:true})).toHaveCount(0);
  await expect(page.getByText('Draft saved locally.',{exact:true})).toBeVisible();
  expect(await page.evaluate(id=>localStorage.getItem('woodwork-local-draft-'+id),created.project.id)).toBeNull();
  await page.getByLabel('Outside width',{exact:true}).fill('36 in');
  await expect(page.getByText('Draft saved locally.',{exact:true})).toBeVisible();
  changed.materials.main.nominal_label='Another accepted material label';
  await mutate(page.request,'/projects/'+created.project.id+'/revisions',{base_revision_id:next.revision.id,spec:changed});
  await page.getByRole('button',{name:'Reopen saved project',exact:true}).click();
  await page.getByRole('button',{name:'Use latest revision as base',exact:true}).click();
  await page.reload();
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('36 in');
  await expect(page.getByText('Accepted revision 3',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Use latest revision as base',exact:true})).toHaveCount(0);
});

test('production port serves coherent PDF and stock outputs at desktop and narrow widths',async({page})=>{
  const production=process.env.WOODWORK_PRODUCTION_URL||'http://127.0.0.1:8777';
  const projects=(await (await page.request.get(production+'/api/v1/projects')).json()).projects;
  const project=projects.find((p:{title:string;latest_successful_revision_id:string;latest_accepted_revision_id:string})=>/^Offline incompatible \d+$/.test(p.title)&&p.latest_successful_revision_id===p.latest_accepted_revision_id);
  expect(project,'Run the full browser suite first to create the genuine priced width-proposal project').toBeTruthy();
  await page.route('**/*',route=>{const host=new URL(route.request().url()).hostname;return ['127.0.0.1','localhost','[::1]'].includes(host)?route.continue():route.abort();});
  await page.goto(production);await page.getByLabel('Saved projects').selectOption(project.id);
  await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
  await expect(page.getByTestId('model-revision')).toContainText('revision 2');
  const pdf=page.getByRole('link',{name:/^Measured design PDF/});
  await page.getByText('Individual output tools',{exact:true}).click();
  if(!await pdf.count())await page.getByRole('button',{name:/^Generate measured PDF/}).click();
  await expect(pdf).toBeVisible({timeout:60_000});
  if(!await page.getByTestId('sheet-subtotal').count())await page.getByRole('button',{name:/^Plan stock and cost/}).click();
  await expect(page.getByTestId('sheet-subtotal')).toHaveText('Sheet purchase subtotal: USD 95.00',{timeout:60_000});
  await expect(page.getByRole('link',{name:/^Stock layout and cut sequence PDF/})).toBeVisible();
  const pdfBytes=await (await page.request.get(production+(await pdf.getAttribute('href'))!)).body();
  expect(pdfBytes.subarray(0,5).toString()).toBe('%PDF-');
  const csv=await (await page.request.get(production+(await page.getByRole('link',{name:/Download cut list/}).getAttribute('href'))!)).text();
  expect(csv).toContain(',878.4,298.8,');
  expect(new URL(page.url()).origin).toBe(new URL(production).origin);
  await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
  await page.getByRole('button',{name:'Isometric',exact:true}).click();
  await page.screenshot({path:'tests/evidence/production-outputs-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.getByTestId('sheet-subtotal').scrollIntoViewIfNeeded();
  await page.screenshot({path:'tests/evidence/production-outputs-narrow.png',fullPage:true});
});
