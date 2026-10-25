import {test,expect,type Page} from '@playwright/test';
import {mkdir,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';

async function compatibleDraft(page:Page){
  const templates=await (await page.request.get('/api/v1/templates')).json();
  const spec=structuredClone(templates.templates[0].default_spec);
  spec.dimensions.outside_width_mm='914.4';
  spec.construction.recipe={id:'beginner_screws_18_6_36in_bookcase',version:'1.0.0'};
  const {csrf_token}=await (await page.request.get('/api/v1/session')).json();
  const response=await page.request.post('/api/v1/projects',{data:{title:'Resize warning '+Date.now(),spec},headers:{'X-Woodwork-CSRF':csrf_token}});
  expect(response.ok()).toBe(true);
  const created=await response.json();
  await page.goto('/');
  await page.getByLabel('Saved projects').selectOption(created.project.id);
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeEnabled();
  return created;
}

test('resizing explains guide limits beside Update design and keyboard revert preserves the accepted revision',async({page})=>{
  await page.setViewportSize({width:1280,height:900});
  const created=await compatibleDraft(page);
  await page.getByLabel('Outside width',{exact:true}).fill('40 in');
  const status=page.getByRole('status',{name:'Assembly guide availability',exact:true});
  await expect(status).toContainText("Build guide won't apply to this draft");
  await expect(status).toContainText('36 in W × 36 in H × 12 in D');
  await expect(status).toContainText('18 mm main');
  await expect(status).toContainText('6 mm back');
  await expect(status).toContainText('2 fixed shelves');
  await expect(status).toContainText('update the model and cut list');
  await expect(status).toContainText('Get plans for measured drawings');
  const update=page.getByRole('button',{name:'Update design',exact:true});
  const revert=page.getByRole('button',{name:'Revert draft',exact:true});
  await expect(update).toBeEnabled();
  await expect(update).toHaveAttribute('aria-describedby','assembly-guide-status');
  const warningBox=await status.boundingBox(),updateBox=await update.boundingBox();
  expect(warningBox&&updateBox&&updateBox.y>=warningBox.y+warningBox.height&&updateBox.y-warningBox.y-warningBox.height<30).toBe(true);
  await update.focus();await page.keyboard.press('Tab');
  await expect(revert).toBeFocused();await expect(revert).toBeInViewport();
  await page.screenshot({path:'tests/evidence/resize-warning-desktop.png',fullPage:true});
  await page.keyboard.press('Enter');
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('36 in');
  await expect(page.getByLabel('Outside width',{exact:true})).toBeFocused();
  await expect(status).toContainText('Technical fabrication method complete');
  expect((await (await page.request.get('/api/v1/projects/'+created.project.id)).json()).project.latest_accepted_revision_id).toBe(created.revision.id);
});

test('mobile changes show measured thickness and shelf limits with reachable revert controls',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await compatibleDraft(page);
  const status=page.getByRole('status',{name:'Assembly guide availability',exact:true});
  const update=page.getByRole('button',{name:'Update design',exact:true});
  const revert=page.getByRole('button',{name:'Revert draft',exact:true});
  await page.getByLabel('Actual main thickness (mm)',{exact:true}).fill('19 mm');
  await expect(status).toContainText("Build guide won't apply");
  await expect(status).toContainText('18 mm main / 6 mm back');
  await update.focus();await page.keyboard.press('Tab');
  await expect(revert).toBeFocused();await expect(revert).toBeInViewport();
  expect(await revert.evaluate(el=>getComputedStyle(el).outlineStyle)).not.toBe('none');
  await page.keyboard.press('Space');
  await expect(page.getByLabel('Actual main thickness (mm)',{exact:true})).toHaveValue('18 mm');
  await page.getByLabel('Fixed shelves',{exact:true}).selectOption('3');
  await expect(status).toContainText('2 fixed shelves');
  await expect(update).toBeEnabled();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await status.scrollIntoViewIfNeeded();
  await page.screenshot({path:'tests/evidence/resize-warning-mobile.png',fullPage:true});
  await revert.click();
  await page.getByLabel('Display units').selectOption('mm');
  await page.getByLabel('Outside width',{exact:true}).fill('1016 mm');
  await expect(status).toContainText('914.4 mm W × 914.4 mm H × 304.8 mm D');
  await revert.click();
  await expect(status).toContainText('Technical fabrication method complete');
});

test('pending and invalid checks never retain a stale compatibility result',async({page})=>{
  await compatibleDraft(page);
  let release=()=>{};
  const held=new Promise<void>(resolve=>{release=resolve;});
  await page.route('**/api/v1/specs/validate',async route=>{await held;await route.continue();});
  const validating=page.waitForRequest(request=>request.url().endsWith('/api/v1/specs/validate'));
  try{
    await page.getByLabel('Outside width',{exact:true}).fill('40 in');await validating;
    const status=page.getByRole('status',{name:'Assembly guide availability',exact:true});
    await expect(status).toContainText('Checking whether the assembly method applies');
    await expect(status).not.toContainText('Technical fabrication method complete');
    await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeDisabled();
    release();
    await expect(status).toContainText("Build guide won't apply");
    await page.getByLabel('Outside width',{exact:true}).fill('1/3');
    await expect(page.getByRole('alert')).toContainText('denominator');
    await expect(status).toHaveText('Assembly method selected; correct measurements to recheck fabrication readiness.');
    await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeDisabled();
  }finally{release();}
});

test('missing optional catalog limits do not invent requirements or promise a guide',async({page})=>{
  const template=await (await page.request.get('/api/v1/templates')).json();
  template.templates[0].recipes.forEach((recipe:{modeling_bounds?:unknown;shelf_count?:unknown})=>{delete recipe.modeling_bounds;delete recipe.shelf_count;});
  await page.route('**/api/v1/templates',route=>route.fulfill({json:template}));
  await compatibleDraft(page);
  await page.getByLabel('Outside width',{exact:true}).fill('40 in');
  const status=page.getByRole('status',{name:'Assembly guide availability',exact:true});
  await expect(status).toContainText("Build guide won't apply");
  await expect(status).toContainText('supported limits could not be loaded');
  await expect(status).not.toContainText('Selected method supports');
});

test('switching saved projects clears the previous guide result until the new draft is checked',async({page})=>{
  const first=await compatibleDraft(page);
  const status=page.getByRole('status',{name:'Assembly guide availability',exact:true});
  await page.getByLabel('Outside width',{exact:true}).fill('40 in');
  await expect(status).toContainText("Build guide won't apply");
  await expect(page.getByText('Draft saved locally.',{exact:true})).toBeVisible();
  const second=await compatibleDraft(page);
  let release=()=>{};
  let held=new Promise<void>(resolve=>{release=resolve;});
  await page.route('**/api/v1/specs/validate',async route=>{await held;await route.continue();});
  try{
    let validating=page.waitForRequest(request=>request.url().endsWith('/api/v1/specs/validate'));
    await page.getByLabel('Saved projects').selectOption(first.project.id);await validating;
    await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('40 in');
    await expect(status).toContainText('Checking whether the assembly method applies');
    await expect(status).not.toContainText('Technical fabrication method complete');
    release();await expect(status).toContainText("Build guide won't apply");
    held=new Promise<void>(resolve=>{release=resolve;});
    validating=page.waitForRequest(request=>request.url().endsWith('/api/v1/specs/validate'));
    await page.getByLabel('Saved projects').selectOption(second.project.id);await validating;
    await expect(status).toContainText('Checking whether the assembly method applies');
    await expect(status).not.toContainText("Build guide won't apply");
    release();await expect(status).toContainText('Technical fabrication method complete');
  }finally{release();}
});

test('genuine resized plans keep the old guide intact and bind new CAD CSV and measured PDF to the new revision',async({page})=>{
  test.setTimeout(600000);
  const external:string[]=[];
  await page.route('**/*',route=>{
    if(['127.0.0.1','localhost','[::1]'].includes(new URL(route.request().url()).hostname))return route.continue();
    external.push(route.request().url());return route.abort();
  });
  const created=await compatibleDraft(page);
  await page.getByRole('button',{name:'Update design',exact:true}).click();
  await expect(page.getByTestId('model-revision')).toContainText('revision 1',{timeout:125000});
  await page.getByRole('button',{name:'Get plans · revision 1',exact:true}).click();
  const oldGuide=page.getByRole('link',{name:'Build guide PDF · revision 1',exact:true});
  await expect(oldGuide).toBeVisible({timeout:240000});
  const oldGuideUrl=(await oldGuide.getAttribute('href'))!;
  const oldBytes=await (await page.request.get(oldGuideUrl)).body();
  const csvUrl=(await page.getByRole('link',{name:'Download cut list · revision 1',exact:true}).getAttribute('href'))!;
  const oldCsv=await (await page.request.get(csvUrl)).text();
  const status=page.getByRole('status',{name:'Assembly guide availability',exact:true});
  await expect(page.getByRole('button',{name:'Up to date',exact:true})).toBeDisabled();
  await page.getByLabel('Outside width',{exact:true}).fill('40 in');
  await expect(status).toContainText('Existing downloads for revision 1 still describe that revision.');
  await expect(page.getByTestId('model-size')).toContainText('36 in W');
  await expect(oldGuide).toHaveAttribute('href',oldGuideUrl);
  expect(await (await page.request.get(csvUrl)).text()).toBe(oldCsv);
  await page.screenshot({path:'tests/evidence/resize-warning-saved-guide.png',fullPage:true});
  await page.getByRole('button',{name:'Revert draft',exact:true}).click();
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('36 in');
  expect((await (await page.request.get('/api/v1/projects/'+created.project.id)).json()).project.latest_accepted_revision_id).toBe(created.revision.id);
  await page.getByLabel('Outside width',{exact:true}).fill('40 in');
  await expect(status).toContainText("Build guide won't apply to this draft");
  await page.getByRole('button',{name:'Update design',exact:true}).click();
  await expect(page.getByTestId('model-revision')).toContainText('revision 2',{timeout:125000});
  await expect(status).toContainText("Build guide won't apply to this design");
  await expect(page.getByTestId('model-size')).toContainText('40 in W');
  await page.getByRole('button',{name:'Get plans · revision 2',exact:true}).click();
  const measured=page.getByRole('link',{name:'Measured design PDF · revision 2',exact:true});
  await expect(measured).toBeVisible({timeout:240000});
  await expect(page.getByRole('link',{name:/Build guide PDF/})).toHaveCount(0);
  const project=(await (await page.request.get('/api/v1/projects/'+created.project.id)).json()).project;
  const {revision}=await (await page.request.get('/api/v1/revisions/'+project.latest_successful_revision_id)).json();
  const {manifest}=await (await page.request.get('/api/v1/revisions/'+revision.id+'/manifest')).json();
  expect(revision.spec.dimensions.outside_width_mm).toBe('1016');
  expect(revision.spec.dimensions.outside_height_mm).toBe('914.4');
  expect(revision.spec.dimensions.outside_depth_mm).toBe('304.8');
  expect(revision.spec.materials).toEqual(created.revision.spec.materials);
  expect(manifest.revision_id).toBe(revision.id);
  expect(manifest.construction.status).toBe('incompatible');
  expect(manifest.validation.geometry).toBe('passed');
  expect(manifest.validation.documents).toBe('passed');
  expect(manifest.artifacts.some((artifact:{relative_path:string})=>artifact.relative_path==='beginner-guide.json')).toBe(false);
  const csv=await (await page.request.get((await page.getByRole('link',{name:'Download cut list · revision 2',exact:true}).getAttribute('href'))!)).text();
  expect(csv).toContain(revision.id);expect(csv).toContain(',980,298.8,');
  expect(await (await page.request.get(oldGuideUrl)).body()).toEqual(oldBytes);
  const repo=fileURLToPath(new URL('../../../',import.meta.url));
  const out=process.env.WOODWORK_RESIZE_EVIDENCE_ROOT||join(repo,'.verification/resize-warning-20261020/native');
  await mkdir(out,{recursive:true});
  const pdfPath=join(out,'resized-measured-design.pdf');
  await writeFile(pdfPath,await (await page.request.get((await measured.getAttribute('href'))!)).body());
  const checked=JSON.parse(execFileSync(join(repo,'.venv/Scripts/python.exe'),['-c',`
import json,sys,hashlib
from pypdf import PdfReader
reader=PdfReader(sys.argv[1]);text=chr(10).join(page.extract_text() for page in reader.pages)
assert sys.argv[2] in text and 'incompatible' in text.lower()
assert 'Recipe hardware and source review' not in text
print(json.dumps({'pdf_revision_checked':True,'incompatible_status_printed':True,'assembly_instructions_absent':True,'pages':len(reader.pages),'pdf_sha256':hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()}))
`,pdfPath,revision.id],{encoding:'utf8'}));
  expect(external).toEqual([]);
  await writeFile(join(out,'verification.json'),JSON.stringify({status:'passed',project_id:project.id,old_revision_id:created.revision.id,new_revision_id:revision.id,old_guide_bytes_unchanged:true,csv_revision_and_dimensions_checked:true,manifest,inspection:checked,external_requests:external},null,2));
  await page.reload();
  await expect(page.getByRole('status',{name:'Plans progress'})).toHaveText('Plans ready · revision 2',{timeout:30000});
  await expect(status).toContainText("Build guide won't apply to this design");
  await expect(measured).toBeVisible();
});
