import { expect, type Page } from '@playwright/test';

export const portals = {
  patient: {
    baseUrl: process.env.PATIENT_URL || 'http://127.0.0.1:5174',
    email: 'patient@demo.com',
    password: 'password',
    emailLabel: 'Email address',
    heading: /request symptom triage/i,
  },
  doctor: {
    baseUrl: process.env.DOCTOR_URL || 'http://127.0.0.1:5175',
    email: 'doctor@demo.com',
    password: 'password',
    emailLabel: 'Work email',
    heading: /triage queue/i,
  },
  admin: {
    baseUrl: process.env.ADMIN_URL || 'http://127.0.0.1:5176',
    email: 'admin@demo.com',
    password: 'password',
    emailLabel: 'Administrator email',
    heading: /dashboard/i,
  },
} as const;

export type PortalRole = keyof typeof portals;

export async function signIn(page: Page, role: PortalRole) {
  const portal = portals[role];
  await page.goto(`${portal.baseUrl}/login`);
  await page.getByLabel(portal.emailLabel).fill(portal.email);
  await page.getByLabel('Password').fill(portal.password);
  await page.getByRole('button', { name: /sign in securely|authenticate securely/i }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole('heading', { name: portal.heading }).first()).toBeVisible();
}

export async function expectNoHorizontalOverflow(page: Page) {
  const sizes = await page.evaluate(() => ({ viewport: window.innerWidth, scroll: document.documentElement.scrollWidth }));
  expect(sizes.scroll, `page scrollWidth ${sizes.scroll} should not exceed viewport ${sizes.viewport}`).toBeLessThanOrEqual(sizes.viewport + 1);
}
