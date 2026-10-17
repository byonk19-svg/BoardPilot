import { test, expect } from '@playwright/test';
test('shared genuine GLB copies can be selected independently', async ({page}) => {
  await page.goto('/?probe=m0');
  await expect(page.getByRole('button',{name:'panel_left',exact:true})).toBeVisible();
  await expect(page.getByTestId('asset-loaded')).toHaveText('2 part instances loaded');
  const canvas = page.locator('canvas');
  const box = await canvas.boundingBox();
  if (!box) throw new Error('Viewer missing');
  await canvas.click({position:{x:box.width*0.417,y:box.height*0.5}});
  await expect(page.getByTestId('selected-ids')).toHaveText('panel_left');
  await canvas.click({position:{x:box.width*0.583,y:box.height*0.5}});
  await expect(page.getByTestId('selected-ids')).toHaveText('panel_right');
  await page.screenshot({path:'test-results/m0-selection.png',fullPage:true});
});
