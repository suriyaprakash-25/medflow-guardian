# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: visual.spec.ts >> doctor visual regression >> secure sign-in visual baseline
- Location: tests\visual.spec.ts:8:5

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:5175/login
Call log:
  - navigating to "http://127.0.0.1:5175/login", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | import { disableMotion, portals, signIn, type PortalRole } from './helpers';
  3  | 
  4  | const roles = Object.keys(portals) as PortalRole[];
  5  | 
  6  | for (const role of roles) {
  7  |   test.describe(`${role} visual regression`, () => {
  8  |     test('secure sign-in visual baseline', async ({ page }) => {
  9  |       const portal = portals[role];
> 10 |       await page.goto(`${portal.baseUrl}/login`);
     |                  ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:5175/login
  11 |       await disableMotion(page);
  12 |       await expect(page).toHaveScreenshot(`${role}-login.png`, {
  13 |         fullPage: true,
  14 |         animations: 'disabled',
  15 |         caret: 'hide',
  16 |       });
  17 |     });
  18 | 
  19 |     test('authenticated dashboard visual baseline', async ({ page }) => {
  20 |       await signIn(page, role);
  21 |       await disableMotion(page);
  22 |       await expect(page).toHaveScreenshot(`${role}-dashboard.png`, {
  23 |         fullPage: true,
  24 |         animations: 'disabled',
  25 |         caret: 'hide',
  26 |         mask: [page.locator('time'), page.locator('[role="status"]')],
  27 |       });
  28 |     });
  29 |   });
  30 | }
  31 | 
```