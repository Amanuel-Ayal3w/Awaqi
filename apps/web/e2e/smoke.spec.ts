import { expect, test } from '@playwright/test';

test.describe('Public site', () => {
    test('landing page loads with navigation', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByRole('navigation')).toBeVisible();
        await expect(page.getByRole('link', { name: 'Features' })).toBeVisible();
    });

    test('locale prefix works', async ({ page }) => {
        await page.goto('/en');
        await expect(page).toHaveURL(/\/en/);
        await expect(page.getByRole('navigation')).toBeVisible();
    });
});

test.describe('API (via Playwright request context)', () => {
    test('health endpoint returns ok', async ({ request }) => {
        const apiBase = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';
        const response = await request.get(`${apiBase}/health`);
        expect(response.ok()).toBeTruthy();
        const body = await response.json();
        expect(body).toEqual({ status: 'ok', service: 'api' });
    });
});
