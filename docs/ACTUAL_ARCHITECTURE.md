# MedFlow Guardian Actual Architecture

## Runtime stack

- Backend: FastAPI on Python, SQLAlchemy ORM and Alembic migrations.
- Database: Supabase-hosted PostgreSQL. Browser database roles are denied direct
  table access; the FastAPI API is the application boundary.
- Object storage: private Supabase Storage in production, with backend-mediated
  release after authorization and malware-scan checks.
- Frontends: separate React, Vite and TypeScript patient, clinician and platform
  administration portals.
- Authentication: MedFlow-issued JWT access tokens held in memory, rotated
  HttpOnly refresh cookies, optional TOTP MFA and server-side replay detection.
- Real-time delivery: authenticated FastAPI WebSockets.

## Authorization architecture decision: Model A

MedFlow intentionally retains Model A: the FastAPI backend is the collocated
policy decision point (PDP) and policy enforcement point (PEP). Every protected
request is evaluated synchronously by `AuthorizationService`; governed patient
access then loads the latest authoritative `ConsentState` and its immutable
`ConsentPolicyVersion` from PostgreSQL. The decision checks actor, organization,
relationship, data, purpose, operation, lifecycle state and validity period.

No browser or separately deployed portal supplies an enforcement-state snapshot.
Therefore there are no independent trusted PEP replicas whose state can diverge,
and literal distributed stale-state detection is not applicable to this design.
The authoritative state ID and policy version used are recorded in audit evidence.

If a future release introduces an independent PEP, it must first add a trusted,
authenticated and versioned state-distribution component with monotonic update
ordering and fail-closed divergence detection. Client-provided state identifiers
must never become authorization evidence.

## Implemented governed flows

- Patient consent creation, immutable policy versioning and append-only lifecycle
  transitions.
- Start-inclusive/end-exclusive consent validity periods, including lossless FHIR
  R4 `Consent.provision.period` import/export.
- Clinician request, patient approval, protected document download and immediate
  revocation followed by denial.
- Hospital membership and doctor-patient relationship enforcement.
- Correlated authorization auditing with request, correlation, authorization,
  enforcement-point, consent-state and policy-version identifiers.
- Private file storage, malware status enforcement and backend-controlled release.

## Deployment boundary

Each portal may be deployed on a different origin. All patient and clinician API
traffic uses the configured `VITE_API_BASE_URL` client with credentials, in-memory
access tokens, one refresh queue and normalized errors. Development proxies remain
only a local convenience.
