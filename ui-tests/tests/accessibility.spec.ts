import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { expectNoHorizontalOverflow, portals, signIn, type PortalRole } from './helpers';

const roles = Object.keys(portals) as PortalRole[];
const wcagTags = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

for (const role of roles) {
  test.describe(`${role} accessibility`, () => {
    test('login has labels, keyboard order, WCAG checks and no overflow', async ({ page }) => {
      const portal = portals[role];
      await page.goto(`${portal.baseUrl}/login`);

      await expect(page.getByRole('main')).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Secure sign in' })).toBeVisible();
      await expect(page.getByLabel(portal.emailLabel)).toBeVisible();
      await expect(page.getByLabel('Password')).toBeVisible();
      await expectNoHorizontalOverflow(page);

      await page.keyboard.press('Tab');
      await expect(page.getByRole('link', { name: 'Skip to sign in' })).toBeFocused();
      await page.keyboard.press('Enter');
      await expect(page.locator('#auth-form')).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(page.getByLabel(portal.emailLabel)).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(page.getByLabel('Password')).toBeFocused();

      const results = await new AxeBuilder({ page }).withTags(wcagTags).analyze();
      expect(results.violations).toEqual([]);
    });

    test('authenticated shell exposes named landmarks and passes WCAG checks', async ({ page }) => {
      await signIn(page, role);
      await expectNoHorizontalOverflow(page);
      await expect(page.getByRole('main')).toBeVisible();

      const width = page.viewportSize()?.width || 0;
      if (width < 768) {
        await expect(page.getByRole('navigation', { name: new RegExp(`${role === 'doctor' ? 'Clinician' : role[0].toUpperCase() + role.slice(1)} mobile navigation`, 'i') })).toBeVisible();
      }

      const results = await new AxeBuilder({ page }).withTags(wcagTags).analyze();
      expect(results.violations).toEqual([]);
    });
  });
}
