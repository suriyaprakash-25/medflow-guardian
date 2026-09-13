# MedFlow Guardian Moderated UX Testing Protocol

## Purpose

This protocol defines the human evidence required before MedFlow Guardian can claim moderated UX validation. Automated Playwright, Axe, keyboard, responsive, and visual-regression checks are necessary but do not replace observation of representative users.

## Required participant groups

At minimum, recruit participants who can credibly represent each production role:

- **Patients:** people comfortable completing common portal tasks such as reviewing recorded health information, understanding document-access requests, and messaging a care team.
- **Clinicians:** practicing or recently practicing clinicians who can assess triage queues, patient context, temporary access requests, and document upload workflows.
- **Administrators:** healthcare or security/operations administrators familiar with staff membership, organization scope, and audit review.

Do not use project developers as the only representatives. Record participant role/background without collecting unnecessary health information.

## Test environments

Run each core journey at least once on:

- Mobile-width experience around 390 px.
- Tablet-width experience around 768 px.
- Desktop-width experience around 1440 px.

Use a non-production test dataset with no real PHI.

## Core journeys

### Patient

1. Sign in and explain what security/authorization messaging means.
2. Review the health summary and identify whether displayed vitals are measurements versus clinical interpretations.
3. Submit a symptom-triage request and explain the automated-screening disclaimer.
4. Review a document-access request, identify requesting clinician/organization, duration, documents, and approve/reject consequences.
5. Find previous access grants and revoke access.
6. Find and use care-team messaging.

### Clinician

1. Sign in and interpret triage priority, status, rationale, and disclaimer.
2. Find a patient using authoritative patient/visit identifiers.
3. Review a patient workspace without assuming unshown data is available.
4. Request temporary access to external records and explain purpose/organization context.
5. Review active grants and download an authorized document.
6. Upload a document to a specific visit and verify patient/visit context before submission.

### Administrator

1. Sign in and identify current administrative scope.
2. Review governance counts without interpreting them as fabricated health/trend signals.
3. Manage staff membership and explain effects of role/deactivation.
4. Review the authorization audit trail and expand event evidence.
5. Use search/filter and export visible audit records.
6. Review account-security actions: profile, password change, MFA enrollment, and session revocation.

## Moderator rules

- Do not coach until the participant has attempted the task.
- Ask neutral questions: “What do you expect this to do?” and “What does this status mean to you?”
- Specifically probe clinical certainty, consent scope, temporary access, identity, organization scope, and error recovery.
- Stop a scenario if a participant would take a clinically unsafe action based on the UI; record it as a critical finding.
- Never ask participants to enter real credentials or real patient data.

## Evidence to capture

For every session capture:

- Date and build/commit tested.
- Participant group and relevant experience (non-identifying summary).
- Device/viewport.
- Task completion: success, success with assistance, failure.
- Time-on-task where useful.
- Errors, hesitation, misinterpretations, and quotes with consent.
- Accessibility or assistive-technology observations.
- Severity of each finding: critical, high, medium, low.
- Proposed remediation and owner.

## Release thresholds

A release candidate passes moderated UX testing only when:

- No open **critical** or **high** usability finding can lead to wrong-patient action, unintended disclosure, misunderstood consent, unsafe triage interpretation, or irreversible administrative action.
- At least 90% of core tasks across each role are completed without moderator intervention.
- Every participant can distinguish automated triage screening from diagnosis/clinical judgment after seeing the UI.
- Every participant can explain the scope and duration of a document-access approval before confirming it.
- Mobile navigation supports completion of each role’s core tasks without desktop-only escape hatches.

## Evidence record

This section must be completed by human reviewers before release.

| Field | Evidence |
| --- | --- |
| Release candidate / commit | **PENDING HUMAN TEST** |
| Patient participants | **PENDING** |
| Clinician participants | **PENDING** |
| Administrator participants | **PENDING** |
| Session notes / recordings location | **PENDING** |
| Critical findings open | **PENDING** |
| High findings open | **PENDING** |
| Task success summary | **PENDING** |
| Reviewer name(s) | **PENDING** |
| Review date | **PENDING** |
| Approval | **NOT YET GRANTED** |

A blank or pending evidence record is a release blocker and must never be interpreted as completed moderated testing.
