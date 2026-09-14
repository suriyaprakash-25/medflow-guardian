import { test, expect } from '@playwright/test';
import { expectNoHorizontalOverflow, portals, signIn } from './helpers';

test.describe('patient journey', () => {
  test('patient can move through health, consent, and account workflows', async ({ page }) => {
    await signIn(page, 'patient');
    await expectNoHorizontalOverflow(page);
    await expect(page.getByText(/automated screening support, not a diagnosis/i)).toBeVisible();

    await page.goto(`${portals.patient.baseUrl}/access-requests`);
    await expect(page.getByRole('heading', { name: /document access requests/i })).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await page.goto(`${portals.patient.baseUrl}/profile`);
    await expect(page.getByRole('heading', { name: /patient identity|demo patient/i }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /profile settings/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /triage history/i })).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });
});

test.describe('doctor journey', () => {
  test('clinician can move through triage, patient, access, and upload workspaces', async ({ page }) => {
    await signIn(page, 'doctor');
    await expect(page.getByText(/triage priority is decision support, not a diagnosis/i)).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await page.goto(`${portals.doctor.baseUrl}/patients`);
    await expect(page.getByRole('heading', { name: /my patients/i })).toBeVisible();
    await expect(page.getByText(/patient id/i).first()).toBeVisible();

    await page.goto(`${portals.doctor.baseUrl}/access-control`);
    await expect(page.getByRole('heading', { name: /access control/i })).toBeVisible();
    await expect(page.getByRole('tab', { name: /request records/i })).toBeVisible();
    await expect(page.getByRole('tab', { name: /active grants/i })).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await page.goto(`${portals.doctor.baseUrl}/upload-report`);
    await expect(page.getByRole('heading', { name: /upload clinical document/i })).toBeVisible();
    await expect(page.getByLabel(/select patient visit/i)).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });
});

test.describe('admin journey', () => {
  test('administrator can inspect governance, audit, staff, and account security workflows', async ({ page }) => {
    await signIn(page, 'admin');
    await expect(page.getByText(/no trend or health status is inferred/i)).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await page.goto(`${portals.admin.baseUrl}/staff`);
    await expect(page.getByRole('heading', { name: /staff directory/i })).toBeVisible();
    await expect(page.getByLabel(/search staff/i)).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await page.goto(`${portals.admin.baseUrl}/audit`);
    await expect(page.getByRole('heading', { name: /audit/i }).first()).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await page.goto(`${portals.admin.baseUrl}/settings`);
    await expect(page.getByRole('heading', { name: /administrative settings/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /change password/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /enroll mfa/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /revoke all sessions/i })).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });
});
