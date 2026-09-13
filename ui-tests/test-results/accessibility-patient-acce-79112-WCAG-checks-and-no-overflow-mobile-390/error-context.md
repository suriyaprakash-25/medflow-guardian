# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: accessibility.spec.ts >> patient accessibility >> login has labels, keyboard order, WCAG checks and no overflow
- Location: tests\accessibility.spec.ts:10:5

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:5174/login
Call log:
  - navigating to "http://127.0.0.1:5174/login", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | import AxeBuilder from '@axe-core/playwright';
  3  | import { expectNoHorizontalOverflow, portals, signIn, type PortalRole } from './helpers';
  4  | 
  5  | const roles = Object.keys(portals) as PortalRole[];
  6  | const wcagTags = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
  7  | 
  8  | for (const role of roles) {
  9  |   test.describe(`${role} accessibility`, () => {
  10 |     test('login has labels, keyboard order, WCAG checks and no overflow', async ({ page }) => {
  11 |       const portal = portals[role];
> 12 |       await page.goto(`${portal.baseUrl}/login`);
     |                  ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:5174/login
  13 | 
  14 |       await expect(page.getByRole('main')).toBeVisible();
  15 |       await expect(page.getByRole('heading', { name: 'Secure sign in' })).toBeVisible();
  16 |       await expect(page.getByLabel(portal.emailLabel)).toBeVisible();
  17 |       await expect(page.getByLabel('Password')).toBeVisible();
  18 |       await expectNoHorizontalOverflow(page);
  19 | 
  20 |       await page.keyboard.press('Tab');
  21 |       await expect(page.getByRole('link', { name: 'Skip to sign in' })).toBeFocused();
  22 |       await page.keyboard.press('Enter');
  23 |       await expect(page.locator('#auth-form')).toBeFocused();
  24 |       await page.keyboard.press('Tab');
  25 |       await expect(page.getByLabel(portal.emailLabel)).toBeFocused();
  26 |       await page.keyboard.press('Tab');
  27 |       await expect(page.getByLabel('Password')).toBeFocused();
  28 | 
  29 |       const results = await new AxeBuilder({ page }).withTags(wcagTags).analyze();
  30 |       expect(results.violations).toEqual([]);
  31 |     });
  32 | 
  33 |     test('authenticated shell exposes named landmarks and passes WCAG checks', async ({ page }) => {
  34 |       await signIn(page, role);
  35 |       await expectNoHorizontalOverflow(page);
  36 |       await expect(page.getByRole('main')).toBeVisible();
  37 | 
  38 |       const width = page.viewportSize()?.width || 0;
  39 |       if (width < 768) {
  40 |         await expect(page.getByRole('navigation', { name: new RegExp(`${role === 'doctor' ? 'Clinician' : role[0].toUpperCase() + role.slice(1)} mobile navigation`, 'i') })).toBeVisible();
  41 |       }
  42 | 
  43 |       const results = await new AxeBuilder({ page }).withTags(wcagTags).analyze();
  44 |       expect(results.violations).toEqual([]);
  45 |     });
  46 |   });
  47 | }
  48 | 
```