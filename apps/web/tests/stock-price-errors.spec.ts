import {test,expect,type Page} from '@playwright/test';
import type {ProjectSpec} from '../src/contracts';
import type {Project} from '../src/api';

const correction='Enter a nonnegative USD price with at most two decimal places.';

async function expectPriceError(page:Page,index:number){
  const price=page.getByLabel(`Sheet ${index+1} price (USD)`,{exact:true});
  const message=`Sheet ${index+1} price: ${correction}`;
  await expect(price).toHaveAttribute('aria-invalid','true');
  await expect(price).toHaveAttribute('aria-describedby',`price-${index}-error`);
  await expect(page.locator(`#price-${index}-error`)).toBeVisible();
  await expect(page.locator(`#price-${index}-error`)).toHaveText(message);
  await expect(price).toHaveAccessibleDescription(message);
  await expect(page.getByRole('alert')).toContainText(message);
}

async function newBookcase(page:Page){
  await page.goto('/');
  await page.getByRole('button',{name:'New bookcase',exact:true}).click();
  await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeEnabled();
  await page.getByText('Advanced settings',{exact:true}).click();
}

test.beforeEach(async({page})=>{
  await page.route('**/*',route=>['127.0.0.1','localhost','[::1]'].includes(new URL(route.request().url()).hostname)?route.continue():route.abort());
});

for(const width of [1280,320,390]){
  test(`stock-price errors identify each field and blank prices stay unknown at ${width}px`,async({page})=>{
    await page.setViewportSize({width,height:900});
    const submittedSpecs:ProjectSpec[]=[];
    let projectSubmissions=0;
    page.on('request',request=>{
      if(request.method()!=='POST')return;
      if(request.url().endsWith('/api/v1/specs/validate'))submittedSpecs.push(request.postDataJSON());
      if(request.url().endsWith('/projects')||request.url().endsWith('/jobs')||request.url().endsWith('/revisions'))projectSubmissions++;
    });
    await newBookcase(page);
    const first=page.getByLabel('Sheet 1 price (USD)',{exact:true});
    const second=page.getByLabel('Sheet 2 price (USD)',{exact:true});
    await first.fill('abc');await second.fill('1.234');
    await expectPriceError(page,0);await expectPriceError(page,1);
    await expect(second).toBeFocused();
    await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeDisabled();
    await second.press('Enter');
    expect(projectSubmissions).toBe(0);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await first.fill('12.3');await second.fill('');
    await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeEnabled();
    await expect(first).toHaveAttribute('aria-invalid','false');
    await expect(second).toHaveAttribute('aria-invalid','false');
    await expect(first).not.toHaveAttribute('aria-describedby',/./);
    await expect(second).not.toHaveAttribute('aria-describedby',/./);
    await expect(page.locator('[id^="price-"][id$="-error"]')).toHaveCount(0);
    await expect(page.getByRole('alert')).toHaveCount(0);
    await expect.poll(()=>submittedSpecs.at(-1)?.manufacturing.stock_sheets.map(stock=>stock.unit_price)).toEqual(['12.30',null]);
    await first.fill('0');
    await expect.poll(()=>submittedSpecs.at(-1)?.manufacturing.stock_sheets.map(stock=>stock.unit_price)).toEqual(['0.00',null]);
    await first.fill('   ');
    await expect.poll(()=>submittedSpecs.at(-1)?.manufacturing.stock_sheets.map(stock=>stock.unit_price)).toEqual([null,null]);
    await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeEnabled();
    expect(projectSubmissions).toBe(0);
  });
}

test('saved invalid prices reopen with associated errors without replacing the saved model or files',async({page})=>{
  const projects:Project[]=(await (await page.request.get('/api/v1/projects')).json()).projects;
  const project=projects.find(entry=>entry.title==='Recovery diagnostic');
  expect(project,'Use an isolated genuine model fixture').toBeTruthy();
  await page.goto('/');await page.getByLabel('Saved projects').selectOption(project!.id);
  await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
  const revert=page.getByRole('button',{name:'Revert draft',exact:true});
  if(await revert.count())await revert.click();
  await expect(page.getByRole('button',{name:'Up to date',exact:true})).toBeDisabled();
  const csv=page.getByRole('link',{name:'Download cut list · revision 1',exact:true});
  const href=(await csv.getAttribute('href'))!;
  const bytes=await (await page.request.get(href)).body();
  const before=await (await page.request.get('/api/v1/revisions/'+project!.latest_accepted_revision_id)).json();
  if(!await page.getByLabel('Sheet 1 price (USD)',{exact:true}).isVisible())await page.getByText('Advanced settings',{exact:true}).click();
  await page.getByLabel('Sheet 1 price (USD)',{exact:true}).fill('abc');
  await page.getByLabel('Sheet 2 price (USD)',{exact:true}).fill('-2');
  await expectPriceError(page,0);await expectPriceError(page,1);
  await expect(page.getByText('Draft saved locally.',{exact:true})).toBeVisible();
  await page.reload();
  await expectPriceError(page,0);await expectPriceError(page,1);
  await expect(page.getByLabel('Sheet 1 price (USD)',{exact:true})).toHaveValue('abc');
  await expect(page.getByLabel('Sheet 2 price (USD)',{exact:true})).toHaveValue('-2');
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeDisabled();
  await expect(csv).toHaveAttribute('href',href);
  expect(await (await page.request.get(href)).body()).toEqual(bytes);
  await page.getByLabel('Sheet 1 price (USD)',{exact:true}).fill('');
  await page.getByLabel('Sheet 2 price (USD)',{exact:true}).fill('');
  await expect(page.getByRole('button',{name:'Up to date',exact:true})).toBeDisabled();
  await expect(page.getByRole('alert')).toHaveCount(0);
  const after=await (await page.request.get('/api/v1/revisions/'+project!.latest_accepted_revision_id)).json();
  expect(after.revision).toEqual(before.revision);
  expect(after.jobs.map((job:{id:string})=>job.id)).toEqual(before.jobs.map((job:{id:string})=>job.id));
  expect(after.revision.spec.manufacturing.stock_sheets.map((stock:{unit_price:string|null})=>stock.unit_price)).toEqual([null,null]);
});

test('removing an earlier stock sheet keeps error names and descriptions on the remaining prices',async({page})=>{
  await newBookcase(page);
  await page.getByRole('button',{name:'Add main stock',exact:true}).click();
  await page.getByLabel('Sheet 2 price (USD)',{exact:true}).fill('abc');
  await page.getByLabel('Sheet 3 price (USD)',{exact:true}).fill('1.234');
  await expectPriceError(page,1);await expectPriceError(page,2);
  await page.getByRole('button',{name:'Remove sheet 1',exact:true}).click();
  await expectPriceError(page,0);await expectPriceError(page,1);
  await expect(page.getByLabel('Sheet 1 price (USD)',{exact:true})).toHaveValue('abc');
  await expect(page.getByLabel('Sheet 2 price (USD)',{exact:true})).toHaveValue('1.234');
  await expect(page.locator('#price-2-error')).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeDisabled();
  await page.getByLabel('Sheet 1 price (USD)',{exact:true}).fill('');
  await page.getByLabel('Sheet 2 price (USD)',{exact:true}).fill('');
  await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeEnabled();
  await expect(page.locator('[id^="price-"][id$="-error"]')).toHaveCount(0);
});
