import { test, expect } from '@playwright/test';
import { disableMotion, portals, signIn, type PortalRole } from './helpers';

const roles = Object.keys(portals) as PortalRole[];

for (const role of roles) {
  test.describe(`${role} visual regression`, () => {
    test('secure sign-in visual baseline', async ({ page }) => {
      const portal = portals[role];
      await page.goto(`${portal.baseUrl}/login`);
      await disableMotion(page);
      await expect(page).toHaveScreenshot(`${role}-login.png`, {
        fullPage: true,
        animations: 'disabled',
        caret: 'hide',
      });
    });

    test('authenticated dashboard visual baseline', async ({ page }) => {
      await signIn(page, role);
      await disableMotion(page);
      await expect(page).toHaveScreenshot(`${role}-dashboard.png`, {
        fullPage: true,
        animations: 'disabled',
        caret: 'hide',
        mask: [page.locator('time'), page.locator('[role="status"]')],
      });
    });
  });
}
