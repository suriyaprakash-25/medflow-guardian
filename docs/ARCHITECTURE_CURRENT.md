# MedFlow Guardian — Current Architecture

_Last updated: 2026-09-14_

This document is the current architecture reference for MedFlow Guardian. Historical phase reports may describe earlier implementation gaps and must not be treated as current system state.

## Security boundary

MedFlow uses **Model A: collocated PDP + PEP** in the FastAPI backend. The browser never supplies or owns enforcement state. Every protected operation is authorized server-side through `AuthorizationService`; patient-bound cross-role access is then evaluated by `ConsentService` using authoritative database state.

The invariant is:

> No protected CAE decision may ALLOW unless all security-relevant context required for that operation is present and validated.

## Identity and session model

- Password + MFA authentication is implemented by the backend.
- Browser access tokens are memory-only.
- Refresh cookies are HttpOnly and server-managed.
- Protected portal actions remain subject to server-side CAE checks after authentication.
- External OIDC federation is not currently a product requirement and is intentionally not enabled. See `docs/adr/ADR-001-OIDC-FEDERATION.md`.

## Consent and authorization

- `Consent`, immutable `ConsentPolicyVersion`, and append-only `ConsentState` are active runtime models.
- Patient self-access does not require third-party consent.
- Cross-role patient access requires explicit purpose and server-resolved consent context unless an operation is explicitly marked `requires_consent=False`.
- `ConsentService` validates patient, practitioner and organization binding, latest ACTIVE state, validity window, purpose and operation.
- Revocation/suspension affects subsequent authorization immediately; no client enforcement snapshot is trusted.

## FHIR interoperability

- FHIR R4 serializers and CapabilityStatement are implemented.
- External FHIR `Consent` import maps into the existing MedFlow consent/policy/state model; it does not create a second policy engine.
- Practitioner FHIR export is scoped by patient + hospital + purpose. The backend resolves the exact active scoped consent; the client does not submit a consent ID as authority.
- Supported FHIR fixtures are validated in CI with the pinned official HL7 validator CLI.

## Storage and malware controls

- Production medical documents use the configured private Supabase Storage bucket.
- Production local-disk fallback is forbidden.
- Readiness validates that the configured bucket exists and is `public=false`.
- ClamAV is provisioned as a private Render service in `render.yaml`.
- Production readiness sends `PING` to ClamAV and requires `PONG`.
- Upload processing remains fail-closed through persisted malware scan state and recovery worker logic.

## Frontend contracts

Shared transport contracts live under `frontend-shared/api/contracts.ts` and are consumed by patient, doctor and admin portals. They are TypeScript transport types only and never grant authorization.

## Deployment and release evidence

- `render.yaml` is the infrastructure definition for backend, private ClamAV, worker, retention job and the three static portals.
- `/health` is liveness.
- `/ready` is dependency-aware readiness and, in production, requires database + ClamAV + private Supabase storage.
- `.github/workflows/production-validation.yml` and `scripts/production_smoke.py` provide live deployment checks.
- External account validation must be backed by actual Render/Supabase evidence; repository configuration alone is not proof of a live deployment.
