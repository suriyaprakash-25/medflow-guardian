# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: journeys.spec.ts >> patient journey >> patient can move through health, consent, and account workflows
- Location: tests\journeys.spec.ts:5:3

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:5174/login
Call log:
  - navigating to "http://127.0.0.1:5174/login", waiting until "load"

```

# Test source

```ts
  1  | import { expect, type Page } from '@playwright/test';
  2  | 
  3  | export const portals = {
  4  |   patient: {
  5  |     baseUrl: process.env.PATIENT_URL || 'http://127.0.0.1:5174',
  6  |     email: 'patient@demo.com',
  7  |     password: 'password',
  8  |     emailLabel: 'Email address',
  9  |     heading: /request symptom triage/i,
  10 |   },
  11 |   doctor: {
  12 |     baseUrl: process.env.DOCTOR_URL || 'http://127.0.0.1:5175',
  13 |     email: 'doctor@demo.com',
  14 |     password: 'password',
  15 |     emailLabel: 'Work email',
  16 |     heading: /triage queue/i,
  17 |   },
  18 |   admin: {
  19 |     baseUrl: process.env.ADMIN_URL || 'http://127.0.0.1:5176',
  20 |     email: 'admin@demo.com',
  21 |     password: 'password',
  22 |     emailLabel: 'Administrator email',
  23 |     heading: /platform governance/i,
  24 |   },
  25 | } as const;
  26 | 
  27 | export type PortalRole = keyof typeof portals;
  28 | 
  29 | export async function signIn(page: Page, role: PortalRole) {
  30 |   const portal = portals[role];
> 31 |   await page.goto(`${portal.baseUrl}/login`);
     |              ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:5174/login
  32 |   await page.getByLabel(portal.emailLabel).fill(portal.email);
  33 |   await page.getByLabel('Password').fill(portal.password);
  34 |   await page.getByRole('button', { name: /sign in securely|authenticate securely/i }).click();
  35 |   await expect(page).toHaveURL(/\/dashboard$/);
  36 |   await expect(page.getByRole('heading', { name: portal.heading }).first()).toBeVisible();
  37 | }
  38 | 
  39 | export async function expectNoHorizontalOverflow(page: Page) {
  40 |   const sizes = await page.evaluate(() => ({ viewport: window.innerWidth, scroll: document.documentElement.scrollWidth }));
  41 |   expect(sizes.scroll, `page scrollWidth ${sizes.scroll} should not exceed viewport ${sizes.viewport}`).toBeLessThanOrEqual(sizes.viewport + 1);
  42 | }
  43 | 
  44 | export async function disableMotion(page: Page) {
  45 |   await page.addStyleTag({ content: '* { animation: none !important; transition: none !important; caret-color: transparent !important; }' });
  46 | }
  47 | 
```