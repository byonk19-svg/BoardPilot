import {test,expect,type Page} from '@playwright/test';

const measurementLabels=['Outside width','Outside height','Outside depth','Fixed shelves','Actual main thickness (mm)','Actual back thickness (mm)'];

async function measurements(page:Page){
  const values:string[]=[];
  for(const label of measurementLabels)values.push(await page.getByLabel(label,{exact:true}).inputValue());
  return values;
}

test.beforeEach(async({page})=>{
  await page.route('**/*',route=>['127.0.0.1','localhost','[::1]'].includes(new URL(route.request().url()).hostname)?route.continue():route.abort());
});

for(const width of [1280,320,390]){
  test(`Choose assembly method opens and focuses Advanced without changing a new draft at ${width}px`,async({page})=>{
    await page.setViewportSize({width,height:900});
    let submissions=0;
    page.on('request',request=>{if(request.method()==='POST'&&request.url().endsWith('/api/v1/projects'))submissions++;});
    await page.goto('/');await page.getByRole('button',{name:'New bookcase',exact:true}).click();
    await expect(page.getByRole('button',{name:'Create design',exact:true})).toBeEnabled();
    await page.getByLabel('Project name',{exact:true}).fill('Unsubmitted method draft');
    await page.getByLabel('Outside width',{exact:true}).fill('35 1/2 in');
    await page.getByLabel('Actual main thickness (mm)',{exact:true}).fill('19.3 mm');
    const before=await measurements(page);
    const action=page.getByRole('button',{name:'Choose assembly method',exact:true});
    const recipe=page.getByLabel('Installed recipe',{exact:true});
    const advanced=page.locator('.advanced-settings');
    await expect(page.getByTestId('recipe-state')).toHaveText('Assembly method still needed; checked dimensions are not assembly instructions.');
    await expect(action).toBeVisible();await expect(recipe).toBeHidden();
    await expect(action).toHaveAttribute('type','button');
    for(const activation of ['keyboard','already-open','pointer']){
      if(activation==='pointer'){
        await page.getByText('Advanced settings',{exact:true}).click();
        await expect(recipe).toBeHidden();await action.click();
      }else await action.press('Enter');
      await expect(advanced).toHaveAttribute('open','');
      await expect(recipe).toBeFocused();await expect(recipe).toBeInViewport();
      expect(await measurements(page)).toEqual(before);
      await expect(page.getByLabel('Project name',{exact:true})).toHaveValue('Unsubmitted method draft');
      await expect(recipe).toHaveValue('');
    }
    await recipe.selectOption('beginner_screws_18_6_36in_bookcase@1.0.0');
    await expect(page.getByTestId('recipe-state')).toContainText("Build guide won't apply");
    await expect(action).toHaveCount(0);
    expect(await measurements(page)).toEqual(before);
    await recipe.selectOption('');
    await expect(action).toBeVisible();
    expect(submissions).toBe(0);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  });
}

test('Choose assembly method preserves a saved model and invalid raw measurements',async({page})=>{
  const projects=(await (await page.request.get('/api/v1/projects')).json()).projects;
  const project=projects.find((entry:{title:string})=>entry.title==='Recovery diagnostic');
  expect(project).toBeTruthy();
  await page.goto('/');await page.getByLabel('Saved projects').selectOption(project.id);
  await expect(page.getByTestId('asset-loaded')).toHaveText('7 part instances loaded');
  const revert=page.getByRole('button',{name:'Revert draft',exact:true});
  if(await revert.count())await revert.click();
  await expect(page.getByRole('button',{name:'Up to date',exact:true})).toBeDisabled();
  const csv=page.getByRole('link',{name:/Download cut list/});
  const href=(await csv.getAttribute('href'))!;
  const bytes=await (await page.request.get(href)).body();
  const action=page.getByRole('button',{name:'Choose assembly method',exact:true});
  const recipe=page.getByLabel('Installed recipe',{exact:true});
  await page.getByLabel('Outside width',{exact:true}).fill('35 in');
  await action.press('Enter');await expect(recipe).toBeFocused();
  await page.getByText('Advanced settings',{exact:true}).click();
  await page.getByLabel('Outside width',{exact:true}).fill('not a measurement');
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveAttribute('aria-invalid','true');
  await action.click();await expect(recipe).toBeFocused();
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('not a measurement');
  await expect(page.getByRole('button',{name:'Update design',exact:true})).toBeDisabled();
  await expect(page.getByTestId('model-size')).toContainText('30 in W');
  await expect(csv).toHaveAttribute('href',href);
  expect(await (await page.request.get(href)).body()).toEqual(bytes);
  expect((await (await page.request.get('/api/v1/projects/'+project.id)).json()).project.latest_accepted_revision_id).toBe(project.latest_accepted_revision_id);
});

test('Choose assembly method is only offered when no method is selected',async({page})=>{
  await page.goto('/');await page.getByRole('button',{name:'New bookcase',exact:true}).click();
  await page.getByLabel('Outside width',{exact:true}).fill('36 in');
  await page.getByRole('button',{name:'Choose assembly method',exact:true}).click();
  const recipe=page.getByLabel('Installed recipe',{exact:true});
  const before=await measurements(page);
  await recipe.selectOption('beginner_screws_18_6_36in_bookcase@1.0.0');
  await expect(page.getByTestId('recipe-state')).toContainText('Technical fabrication method complete');
  await expect(page.getByRole('button',{name:'Choose assembly method',exact:true})).toHaveCount(0);
  expect(await measurements(page)).toEqual(before);
  await page.getByLabel('Outside width',{exact:true}).fill('40 in');
  await expect(page.getByTestId('recipe-state')).toContainText("Build guide won't apply");
  await expect(page.getByRole('button',{name:'Choose assembly method',exact:true})).toHaveCount(0);
  await recipe.selectOption('');
  await expect(page.getByRole('button',{name:'Choose assembly method',exact:true})).toBeVisible();
  await expect(page.getByLabel('Outside width',{exact:true})).toHaveValue('40 in');
});
