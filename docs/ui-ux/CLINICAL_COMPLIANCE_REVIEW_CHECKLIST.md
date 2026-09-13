# MedFlow Guardian Clinical Safety and Compliance Review Gate

## Purpose

This checklist defines the human clinical-safety, privacy, security, and compliance evidence required before a release can be approved. It is intentionally separate from automated tests. Passing CI does not constitute clinical or regulatory approval.

## Review inputs

Reviewers must evaluate the release candidate by commit SHA and include evidence from:

- Patient, clinician, and administrator interfaces.
- Current API/authorization behavior and audit evidence.
- Automated accessibility and browser-test results.
- Moderated usability findings.
- Current deployment/security configuration relevant to the release environment.

## Clinical safety review

- [ ] Symptom triage is described as automated screening/decision support, not diagnosis.
- [ ] The deterministic nature and limitations of the current triage engine are visible where the output can influence behavior.
- [ ] Emergency guidance does not encourage reliance on the portal for emergency care.
- [ ] Priority labels, counts, and status labels match authoritative backend values.
- [ ] No unsupported response-time, prognosis, “healthy,” “stable,” or trend claim appears in the UI.
- [ ] Recorded vital signs are not automatically represented as clinically normal/abnormal unless a validated clinical rule explicitly supplies that interpretation.
- [ ] Clinician workflows use authoritative patient/visit identifiers and present enough context to reduce wrong-patient actions.
- [ ] Upload confirmation makes target patient/visit and document category explicit.
- [ ] Any automated rationale is clearly separated from clinician judgment.

## Consent and privacy review

- [ ] Patients can identify the requesting practitioner and organization before approving access.
- [ ] Requested documents and access duration are visible before confirmation.
- [ ] Approval language accurately represents temporary/scoped access rather than ownership transfer or blanket consent.
- [ ] Revocation consequences are clear.
- [ ] Cross-role patient-bound operations preserve explicit purpose and consent context.
- [ ] UI behavior does not imply access where CAE can deny it.
- [ ] No PHI is placed in URLs, browser persistence, logs, or client-side diagnostic output beyond approved requirements.
- [ ] Browser bearer access tokens remain memory-only; refresh-cookie/session behavior remains server-controlled.

## Authorization and audit review

- [ ] Model A remains intact: backend is both PDP and PEP, and client state is not treated as enforcement authority.
- [ ] Administrative organization scope is derived from authenticated identity/membership, not client role claims alone.
- [ ] Audit views describe server audit evidence without exposing a client-controlled enforcement mechanism.
- [ ] ALLOW/DENY, purpose, consent trace, organization, resource, and actor information are understandable to intended administrators.
- [ ] Exported audit data is clearly limited to the records actually loaded/filtered by the UI unless the server provides a full export endpoint.
- [ ] Sensitive administrative actions have confirmation or explicit consequence messaging where appropriate.

## Accessibility review

- [ ] Automated Axe WCAG 2.2 A/AA checks are green for tested role surfaces.
- [ ] Keyboard navigation works for authentication, navigation, dialogs, tabs, tables, confirmation actions, and primary workflows.
- [ ] Dialog focus is trapped/restored and Escape behavior is correct.
- [ ] Icon-only controls have accessible names.
- [ ] Focus indication is visible at required contrast.
- [ ] Mobile touch targets are appropriately sized.
- [ ] Responsive tables expose horizontal scrolling as a labelled keyboard-focusable region where required.
- [ ] Screen-reader semantics have been manually spot-checked with at least one supported screen reader/browser combination.

## Compliance / operational review

Reviewers should map applicable organizational/regulatory obligations rather than assuming this checklist itself establishes compliance.

- [ ] Data minimization and minimum-necessary principles have been reviewed for each role.
- [ ] Retention, deletion, audit retention, and export requirements have been reviewed for the intended deployment jurisdiction.
- [ ] Incident-response and breach-notification procedures reference the current audit/observability implementation.
- [ ] Access provisioning/deprovisioning is consistent with organization policy.
- [ ] MFA/password/session controls match the deployment organization’s authentication policy.
- [ ] Production CORS, TLS/proxy, database, storage, malware scanning, backup/restore, and worker configuration evidence is current.
- [ ] Human reviewers understand that UI text alone does not establish HIPAA, GDPR, local health-law, or medical-device compliance.

## Required sign-off evidence

| Field | Evidence |
| --- | --- |
| Release candidate / commit | **PENDING HUMAN REVIEW** |
| Clinical reviewer name / credentials | **PENDING** |
| Privacy/compliance reviewer | **PENDING** |
| Security reviewer | **PENDING** |
| Accessibility manual check reviewer | **PENDING** |
| Moderated-test evidence reviewed | **PENDING** |
| Open critical/high safety findings | **PENDING** |
| Required remediation / exceptions | **PENDING** |
| Review date | **PENDING** |
| Clinical safety approval | **NOT YET GRANTED** |
| Privacy/compliance approval | **NOT YET GRANTED** |
| Release authorization | **NOT YET GRANTED** |

Pending fields are release blockers. This file is an evidence gate, not evidence that a review has occurred.
