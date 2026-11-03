import { test, expect } from '@playwright/test';
test('authenticated investigation exposes quality, provenance and isolated replay', async ({page}) => {
  await page.goto('/');
  await page.getByLabel('API key').fill(process.env.RISKRADAR_API_KEY);
  await page.getByRole('button',{name:'Connect / refresh'}).click();
  const equipment=page.getByRole('button',{name:/degradation.*Telemetry/});
  await expect(equipment).toBeVisible();
  await equipment.click();
  await expect(page.getByRole('heading',{name:'Predictions and append-only revisions'})).toBeVisible();
  const provenance = page.locator('details').filter({hasText:'Provenance / alternatives'}).first();
  await provenance.locator('summary').click();
  await expect(provenance.locator('pre')).toContainText('input_refs');
  await expect(provenance.locator('pre')).toContainText('causal-v2');
  await page.getByRole('button',{name:/^arrival/}).click();
  await expect(page.getByRole('columnheader',{name:'Identical input hash'})).toBeVisible();
  await page.getByRole('button',{name:/^corrected/}).click();
  await expect(page.getByRole('columnheader',{name:'Identical input hash'})).toBeVisible();
  await page.screenshot({path:'test-results/investigation.png',fullPage:true});
});
test('invalid credential produces a visible error',async ({page})=>{
  await page.goto('/');await page.getByLabel('API key').fill('invalid');
  await page.getByRole('button',{name:'Connect / refresh'}).click();
  await expect(page.getByRole('alert')).toContainText('invalid credentials');
});

test('operators can cancel and resume a pinned replay',async ({page,request})=>{
  const headers={Authorization:`Bearer ${process.env.RISKRADAR_API_KEY}`};
  const existing=await (await request.get('http://localhost:8000/api/replays',{headers})).json();
  const units={temperature:'degC',vibration:'mm/s',pressure:'kPa',current:'A',rpm:'rpm'};
  const event={event_id:'browser:replay-control',equipment_id:'degradation',lifecycle_id:'original',session_id:'browser-control',sequence:1,cycle:1,observed_at:new Date().toISOString(),schema_version:1,values:{temperature:65,vibration:2,pressure:100,current:40,rpm:1500},units,quality:Object.fromEntries(Object.keys(units).map(s=>[s,'good']))};
  expect((await request.post('http://localhost:8000/api/events',{headers,data:event})).status()).toBe(202);
  const created=await request.post('http://localhost:8000/api/replays',{headers,data:{models:existing[0].manifest.models,mode:'arrival'}});
  expect(created.status()).toBe(201);
  const {run_id}=await created.json();
  await page.goto('/');await page.getByLabel('API key').fill(process.env.RISKRADAR_API_KEY);
  await page.getByRole('button',{name:'Connect / refresh'}).click();
  await page.getByRole('button',{name:new RegExp(`^arrival · ${run_id.slice(7,15)}`)}).click();
  await page.getByRole('button',{name:'Cancel replay'}).click();
  await expect(page.getByRole('button',{name:'Resume replay'})).toBeVisible();
  await page.getByRole('button',{name:'Resume replay'}).click();
  await expect(page.getByRole('button',{name:'Cancel replay'})).toBeVisible();
});
