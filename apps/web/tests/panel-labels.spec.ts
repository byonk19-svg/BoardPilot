import {test,expect} from '@playwright/test';

for(const width of [1280,320,390]){
  test(`panel accessible names include their visible names and IDs at ${width}px`,async({page})=>{
    await page.route('**/*',route=>['127.0.0.1','localhost','[::1]'].includes(new URL(route.request().url()).hostname)?route.continue():route.abort());
    await page.setViewportSize({width,height:900});
    const projects=(await (await page.request.get('/api/v1/projects')).json()).projects;
    const project=projects.find((entry:{title:string})=>entry.title==='Recovery diagnostic');
    expect(project,'Use the isolated genuine model fixture').toBeTruthy();
    await page.goto('/');await page.getByLabel('Saved projects').selectOption(project.id);
    await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
    const csv=page.getByRole('link',{name:/Download cut list/});
    const href=(await csv.getAttribute('href'))!;
    const bytes=await (await page.request.get(href)).body();
    const panels=page.locator('.part-picker button');
    await expect(panels).toHaveCount(7);
    for(const panel of await panels.all()){
      const visibleName=await panel.locator('span').innerText();
      const instanceId=await panel.locator('small').innerText();
      const name=`Select ${visibleName} (${instanceId})`;
      await expect(panel).toHaveAccessibleName(name);
      const namedButton=page.getByRole('button',{name,exact:true});
      if(width===1280)await namedButton.press('Enter');
      else await namedButton.click();
      await expect(namedButton).toHaveAttribute('aria-pressed','true');
      await expect(page.getByTestId('selected-ids')).toHaveText(instanceId);
      await expect(page.locator('tbody tr.selected-row')).toContainText(instanceId);
      await expect(page.locator('.part-picker button[aria-pressed="true"]')).toHaveCount(1);
    }
    await page.getByRole('button',{name:'Select Horizontal panels',exact:true}).press('Enter');
    await expect(page.getByTestId('selected-ids')).toHaveText('bottom, shelf_01, shelf_02, top');
    await expect(page.locator('.part-picker button[aria-pressed="true"]')).toHaveCount(4);
    for(const name of ['Select Bottom (bottom)','Select Shelf 1 (shelf_01)','Select Shelf 2 (shelf_02)','Select Top (top)']){
      await expect(page.getByRole('button',{name,exact:true})).toHaveAttribute('aria-pressed','true');
    }
    await page.getByRole('button',{name:'Hide selected',exact:true}).press('Enter');
    await expect(page.getByTestId('visible-instances')).toHaveText('3 panels visible');
    await page.getByRole('button',{name:'Restore',exact:true}).press('Space');
    await expect(page.getByTestId('visible-instances')).toHaveText('7 panels visible');
    await page.getByRole('button',{name:'Select Left side (side_left)',exact:true}).press('Enter');
    await expect(page.getByRole('button',{name:'Select Left side (side_left)',exact:true})).toBeFocused();
    await expect(csv).toHaveAttribute('href',href);
    expect(await (await page.request.get(href)).body()).toEqual(bytes);
    expect((await (await page.request.get('/api/v1/projects/'+project.id)).json()).project.latest_accepted_revision_id).toBe(project.latest_accepted_revision_id);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:test.info().outputPath(`panel-labels-${width}.png`)});
  });
}
