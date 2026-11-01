import { test, expect } from '@playwright/test';
test('authenticated investigation exposes quality, provenance and isolated replay', async ({page}) => {
  await page.goto('/');
  await page.getByLabel('API key').fill(process.env.RISKRADAR_API_KEY);
  await page.getByRole('button',{name:'Connect / refresh'}).click();
  const equipment=page.getByRole('button',{name:/degradation.*Telemetry/});
  await expect(equipment).toBeVisible();
  await equipment.click();
  await expect(page.getByRole('heading',{name:'Predictions and append-only revisions'})).toBeVisible();
  await page.locator('summary').filter({hasText:'Provenance / alternatives'}).first().click();
  await expect(page.locator('pre').first()).toContainText('input_refs');
  await expect(page.locator('pre').first()).toContainText('causal-v2');
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
