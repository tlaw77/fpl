import { expect, test } from '@playwright/test';

test('shell stays inside a 390px viewport', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'I Fought the Law' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Decision Centre views' })).toBeVisible();

  const dimensions = await page.evaluate(() => ({
    documentWidth: document.documentElement.scrollWidth,
    viewportWidth: document.documentElement.clientWidth,
  }));

  expect(dimensions.documentWidth).toBeLessThanOrEqual(dimensions.viewportWidth);
});

test('primary navigation switches the placeholder without a page reload', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Transfer' }).click();

  await expect(page.getByRole('heading', { name: 'One coherent transfer decision' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Transfer' })).toHaveAttribute('aria-current', 'page');
});
