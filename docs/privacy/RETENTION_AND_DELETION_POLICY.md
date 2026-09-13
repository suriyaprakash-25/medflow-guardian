# MedFlow retention, deletion, archival, and legal-hold policy

Policy version: `2026-09-13.1`

This policy is an engineering baseline and becomes legally operative only after
the jurisdiction, controller, clinical-record obligations, contracts, and
regulator-specific periods are entered in the release approval record.

## Implemented schedule

| Data class | Default action | Engineering period |
| --- | --- | --- |
| Spent refresh-token SHA-256 fingerprints | Delete | 90 days |
| Unanswered access requests | Mark expired | 30 days |
| Active access grants past expiry | Mark expired | Immediately |
| Medical-document metadata | Archive, do not erase | 2,557 days (7 years) |
| Clinical records and immutable consent/audit history | Retain | Until legally approved erasure date |
| Direct account/profile identifiers after approved deletion | Pseudonymize | On approved execution |

`python -m scripts.apply_retention` is dry-run by default. The Render cron uses
`--apply`. Active legal holds exclude a patient's documents from archival.

## Data-subject workflow

Patients submit export or deletion requests through `/api/privacy/requests`.
Only platform administrators can review requests, place/release legal holds, or
execute an approved deletion. Execution is row-locked and fail-closed when an
active legal hold exists. It revokes sessions, grants, pending requests, and
consents before pseudonymizing direct identifiers. Governed clinical and audit
evidence is preserved pending the applicable legal schedule.

## Required legal entries before production

- controller and processor legal names;
- operating jurisdictions and applicable health/privacy laws;
- approved period for each data class and minors, deceased patients, litigation,
  research, billing, and adverse-event exceptions;
- export identity-verification and delivery procedure;
- authorized legal-hold placers and release approvers;
- storage-object erasure and backup-expiry obligations;
- named privacy/legal approver and approval date.
