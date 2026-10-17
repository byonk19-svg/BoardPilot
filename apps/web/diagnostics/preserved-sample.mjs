import {chromium} from 'playwright';
import {mkdir,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';

const browser=await chromium.launch();
try{
  const page=await browser.newPage({viewport:{width:1440,height:1000},baseURL:'http://127.0.0.1:8777'});
  await page.goto('http://127.0.0.1:8777/');
  await page.getByLabel('Saved projects',{exact:true}).selectOption('project_26ad37413dc040deb6b0d479c438e8a3');
  await page.getByRole('heading',{name:'Sample bookcase walkthrough',exact:true}).waitFor();
  await page.getByTestId('asset-loaded').filter({hasText:'7 part instances loaded'}).waitFor();
  assert.equal(await page.getByLabel('Outside width',{exact:true}).inputValue(),'36 in');
  assert.equal(await page.getByLabel('Outside height',{exact:true}).inputValue(),'36 in');
  assert.equal(await page.getByLabel('Outside depth',{exact:true}).inputValue(),'12 in');
  assert.match(await page.getByTestId('model-revision').innerText(),/revision 2/);
  assert(await page.getByRole('link',{name:'Stock layout and cut sequence PDF · revision 2',exact:true}).isVisible());
  const shell=await page.request.get('/');
  assert.equal(shell.headers()['cache-control'],'no-cache');
  const scripts=await page.locator('script[src]').evaluateAll(nodes=>nodes.map(node=>node.getAttribute('src')));
  const html=await shell.text();
  assert(scripts.length>0&&scripts.every(script=>html.includes(`src="${script}"`)));
  await mkdir('../../output/playwright',{recursive:true});
  const screenshot='../../output/playwright/regeneration-user-project-preserved.png';
  await page.screenshot({path:screenshot,fullPage:false});
  await writeFile('../../evidence/m2/preserved-walkthrough-ui.json',JSON.stringify({status:'passed',project_id:'project_26ad37413dc040deb6b0d479c438e8a3',revision:2,dimensions_in:{width:36,height:36,depth:12},physical_panels_loaded:7,stock_pdf_available:true,html_cache_control:shell.headers()['cache-control'],scripts,screenshot},null,2)+'\n');
}finally{await browser.close();}
