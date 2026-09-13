# MedFlow Guardian — Final Five Production Workstreams

Last updated: 2026-09-13

This checklist separates repository-controlled engineering from actions that
require a live account, production credentials, or an independent reviewer.
A phase is complete only when its evidence gate passes; a runbook alone does
not count as completion.

## Phase 1 — Production observability

- [x] Emit structured, PHI-safe application and request logs with correlation IDs.
- [x] Expose authenticated service metrics without exposing patient data.
- [x] Record latency, status, authorization denial, readiness, and worker metrics.
- [x] Define actionable alert thresholds and a security-event dashboard.
- [x] Add uptime/readiness monitoring automation and an operator runbook.
- [x] Pass observability unit, integration, and configuration tests.

Evidence gate: automated tests exercise logs, metrics, access control, and alert
configuration; CI validates the complete gate.

## Phase 2 — Live deployment and operational validation

- [x] Validate Render Blueprint and fail-closed production configuration.
- [ ] Validate Supabase database, RLS, private Storage, and secrets inventory.
- [ ] Validate private ClamAV connectivity and malware worker health.
- [x] Add a credentialed post-deployment smoke-test workflow.
- [x] Add a reproducible backup/restore drill with evidence capture.
- [ ] Deploy the live stack and execute smoke and disaster-recovery drills.

Evidence gate: repository configuration passes locally and in CI. Final live
completion additionally requires Render/Supabase credentials and recorded
production drill output.

## Phase 3 — External FHIR conformance validation

- [x] Publish the supported CapabilityStatement.
- [x] Validate exported resources and references against declared FHIR R4 rules.
- [x] Integrate the official external HL7 FHIR validator into a repeatable gate.
- [x] Store validator output as CI/release evidence.
- [x] Pass internal interoperability and external validator gates.

Evidence gate: no validator errors for the supported fixture corpus and the
CapabilityStatement matches the implemented API surface.

## Phase 4 — Privacy and compliance readiness

- [x] Define versioned retention, archival, deletion, and legal-hold policy.
- [x] Implement consent-withdrawal propagation and access revocation checks.
- [x] Implement auditable data-subject deletion/export workflows.
- [x] Document breach triage, notification, evidence preservation, and roles.
- [x] Add privacy/compliance tests and an operator evidence checklist.
- [ ] Obtain jurisdiction-specific legal/regulatory review.

Evidence gate: code and policy tests pass. Legal readiness remains conditional
until an authorized external reviewer signs the release evidence.

## Phase 5 — Independent security assessment and release sign-off

- [x] Add automated SAST, dependency, secret, and dynamic API security gates.
- [x] Produce a scoped penetration-test plan and finding/remediation register.
- [x] Run the repeatable internal security suite and preserve CI results.
- [ ] Commission an independent penetration test and remediate all release blockers.
- [ ] Complete clinical safety, security, privacy, and operations sign-off.

Evidence gate: automated gates pass and no unresolved critical/high findings
remain. Production sign-off requires named independent assessors and accountable
clinical/privacy/operations approvers.
