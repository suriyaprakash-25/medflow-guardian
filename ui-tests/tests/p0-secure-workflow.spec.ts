import { expect, test, type Page } from '@playwright/test';
import { portals, signIn } from './helpers';

type ApiResult<T> = { status: number; data: T; contentType: string };

async function browserApi<T>(
  page: Page,
  path: string,
  method = 'GET',
  body?: unknown,
): Promise<ApiResult<T>> {
  return page.evaluate(async ({ path, method, body }) => {
    const refresh = await fetch('/api/auth/refresh', {
      method: 'POST',
      credentials: 'include',
    });
    if (!refresh.ok) throw new Error(`Session refresh failed with ${refresh.status}`);
    const { access_token: accessToken } = await refresh.json();
    const response = await fetch(path, {
      method,
      credentials: 'include',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('json')
      ? await response.json()
      : await response.arrayBuffer().then((value) => ({ byteLength: value.byteLength }));
    return { status: response.status, data, contentType };
  }, { path, method, body });
}

test('P0 authenticated request, approval, download, revocation, denial and audit', async ({ browser }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop-1440', 'Security workflow runs once on desktop.');

  const doctorContext = await browser.newContext({ acceptDownloads: true });
  const patientContext = await browser.newContext({ acceptDownloads: true });
  const doctorPage = await doctorContext.newPage();
  const patientPage = await patientContext.newPage();

  await signIn(doctorPage, 'doctor');
  const visits = await browserApi<Array<{ patient_id: number; hospital_id: number }>>(
    doctorPage,
    '/api/visits/doctor',
  );
  expect(visits.status).toBe(200);
  expect(visits.data.length, 'Seeded clinician requires at least one visit').toBeGreaterThan(0);
  const visit = visits.data[0];

  const documents = await browserApi<Array<{ id: number }>>(
    doctorPage,
    `/api/documents/metadata/${visit.patient_id}?hospital_id=${visit.hospital_id}`,
  );
  expect(documents.status).toBe(200);
  expect(documents.data.length, 'Seeded visit requires at least one clean document').toBeGreaterThan(0);
  const documentId = documents.data[0].id;

  const requested = await browserApi<{ id: number }>(doctorPage, '/api/access-requests', 'POST', {
    patient_id: visit.patient_id,
    hospital_id: visit.hospital_id,
    document_ids: [documentId],
    reason: `P0 browser validation ${Date.now()}`,
  });
  expect(requested.status).toBe(200);

  await signIn(patientPage, 'patient');
  const pending = await browserApi<Array<{ id: number; requested_documents: Array<{ id: number }> }>>(
    patientPage,
    '/api/access-requests/patient?status=pending',
  );
  expect(pending.status).toBe(200);
  const request = pending.data.find((item) => item.id === requested.data.id);
  expect(request).toBeTruthy();

  const approved = await browserApi<{ id: number }>(
    patientPage,
    `/api/access-requests/${requested.data.id}/approve`,
    'POST',
    { duration_hours: 1, document_ids: [documentId] },
  );
  expect(approved.status).toBe(200);

  const released = await browserApi<{ byteLength: number }>(
    doctorPage,
    `/api/documents/${documentId}/download?purpose=TREATMENT`,
  );
  expect(released.status).toBe(200);
  expect(released.data.byteLength).toBeGreaterThan(0);

  const revoked = await browserApi<{ message: string }>(
    patientPage,
    `/api/access-grants/${approved.data.id}/revoke`,
    'POST',
    {},
  );
  expect(revoked.status).toBe(200);

  const denied = await browserApi<{ detail: string }>(
    doctorPage,
    `/api/documents/${documentId}/download?purpose=TREATMENT`,
  );
  expect(denied.status).toBe(403);

  const audit = await browserApi<Array<{
    resource_id?: string;
    operation: string;
    decision: string;
    request_id?: string;
    correlation_id?: string;
    authorization_id?: string;
    enforcement_point?: string;
    enforcement_state?: string;
  }>>(doctorPage, '/api/audit/doctor');
  expect(audit.status).toBe(200);
  const denialAudit = audit.data.find((row) =>
    row.resource_id === String(documentId)
    && row.operation === 'download'
    && row.decision === 'DENY');
  expect(denialAudit).toMatchObject({
    enforcement_point: 'fastapi-model-a-collocated-pep',
  });
  expect(denialAudit?.request_id).toBeTruthy();
  expect(denialAudit?.correlation_id).toBeTruthy();
  expect(denialAudit?.authorization_id).toBeTruthy();
  expect(denialAudit?.enforcement_state).toBeTruthy();

  await doctorContext.close();
  await patientContext.close();
});

test('patient UI creates, versions and transitions consent', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop-1440', 'Consent mutation workflow runs once on desktop.');
  await signIn(page, 'patient');
  await page.goto(`${portals.patient.baseUrl}/consents`);
  await expect(page.getByRole('heading', { name: 'Consent policies' })).toBeVisible();

  await page.getByLabel('Allowed purposes').fill('TREATMENT, PAYMENT');
  await page.getByRole('button', { name: 'Create and activate' }).click();
  await expect(page.getByText('Consent created and activated.')).toBeVisible();

  const consents = await browserApi<Array<{ id: number; status: string }>>(page, '/api/consents');
  expect(consents.status).toBe(200);
  const created = consents.data[0];
  expect(created.status).toBe('active');

  const card = () => page.getByText(`Consent #${created.id}`).locator('xpath=ancestor::div[contains(@class,"rounded-xl")][1]');
  await card().getByRole('button', { name: 'Revise policy' }).click();
  await page.getByLabel('Allowed purposes').fill('TREATMENT');
  await page.getByRole('button', { name: 'Create policy version' }).click();
  await expect(page.getByText('A new authoritative policy version was created.')).toBeVisible();
  await expect(card().getByText('Policy version 2')).toBeVisible();

  await card().getByRole('button', { name: 'suspended' }).click();
  await expect(page.getByText('Consent suspended.')).toBeVisible();
  await card().getByRole('button', { name: 'active' }).click();
  await expect(page.getByText('Consent active.')).toBeVisible();
  await card().getByRole('button', { name: 'revoked' }).click();
  await expect(page.getByText('Consent revoked.')).toBeVisible();
  await expect(card().getByText('revoked', { exact: true })).toBeVisible();
});
