# P1 Completion Evidence Report — 2026-09-14

## Scope

This report covers the seven P1 completion priorities: shared frontend API contracts, server-resolved clinician consent, production storage/malware configuration, live deployment/recovery validation, external FHIR validation/integration, OIDC federation decision, and architecture-document alignment.

## Implementation status

### 1. Shared API contracts — IMPLEMENTED

`frontend-shared/api/contracts.ts` is the shared transport-contract module for patient, clinician and admin portals. Portal context/auth code imports these contracts instead of independently redefining core login, identity, visit, document, access, notification, audit and FHIR transport shapes. Contracts are transport types only and do not carry authorization authority.

### 2. Clinician consent-ID prompt — IMPLEMENTED

The doctor portal no longer prompts for or transmits a consent ID for FHIR export. It submits purpose plus the active visit's hospital scope. The backend resolves the newest ACTIVE consent explicitly bound to the patient, practitioner and hospital via `resolve_active_scoped_consent()`, then passes the resolved consent into the existing `AuthorizationService` + `ConsentService` path. Missing/wrong scope fails closed.

### 3. Private Supabase + production ClamAV — REPOSITORY CONTROLS IMPLEMENTED; LIVE ACCOUNT EVIDENCE REQUIRED

`render.yaml` defines private ClamAV infrastructure and injects its private host into the backend and malware worker. Production storage refuses local fallback. Production `/ready` requires database connectivity, ClamAV PING/PONG, and Supabase bucket metadata proving the configured bucket exists and is `public=false`.

Actual Supabase project/bucket and Render service state must still be verified against the connected production accounts; repository configuration is not evidence of a live resource.

### 4. Render deployment/recovery — AUTOMATED VALIDATION IMPLEMENTED; LIVE DRILL EVIDENCE REQUIRED

`scripts/production_smoke.py` validates liveness, dependency-aware readiness, FHIR CapabilityStatement, hidden API docs/metrics and frontend security headers. `.github/workflows/production-validation.yml` provides the production smoke/ZAP gate. `docs/release/P1_LIVE_DEPLOYMENT_RECOVERY.md` defines the evidence-backed ClamAV, worker, backend and storage recovery drills.

The live drills require authorized Render/Supabase account access and must not be marked PASS without deploy/log/resource evidence.

### 5. External FHIR validation + integration — IMPLEMENTED

The existing official HL7 validator CLI remains pinned by version and SHA-256 and runs over generated fixtures. P1 additionally adds an authenticated HTTP integration path: PostgreSQL + migrations/seed + real FastAPI login + `/api/auth/me` + live FHIR CapabilityStatement/patient export, followed by validation of those HTTP-produced resources with the official HL7 validator.

### 6. External OIDC — NOT REQUIRED BY CURRENT PRODUCT; DEFERRED BY DESIGN

No current repository product requirement, IdP configuration, SSO workflow or federation dependency exists. `docs/adr/ADR-001-OIDC-FEDERATION.md` records the decision not to add unnecessary federation attack surface. A dedicated design/security phase is required if federation becomes a real requirement later.

### 7. Architecture reports — ALIGNED

`docs/ARCHITECTURE_CURRENT.md` is the current architecture source of truth. The stale complete-feature audit that still claimed ConsentService/FHIR Consent were missing was removed. The FHIR export security document was updated to describe server-resolved scoped consent.

## Release evidence still required

Before this P1 is called fully operationally complete, attach:

- green full repository CI/security/FHIR HTTP-integration results for the P1 PR;
- live Render deployment evidence for the release commit;
- proof the configured Supabase medical-document bucket exists and is private;
- live ClamAV PING/PONG and fail-closed/recovery evidence;
- worker pending-scan recovery evidence;
- successful production smoke validation.

No report should substitute configuration or mocked tests for those live-account checks.
