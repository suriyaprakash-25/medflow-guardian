# P1 Live Deployment and Recovery Validation

This is the release evidence protocol for the deployed Render + Supabase environment. It is intentionally separate from repository CI: configuration tests prove the intended topology, while this protocol proves the actual production resources.

## Required evidence

Record the UTC timestamp, Render deploy IDs, backend/worker/ClamAV service names, Supabase project reference, and tester identity in the release ticket. Never paste service-role keys, tokens, PHI, or document contents into evidence.

## Baseline validation

1. Confirm all production services are deployed from the intended release commit.
2. Confirm `medflow-clamav-prod` is a private service and is not internet exposed.
3. Confirm the configured Supabase Storage bucket is `medical-documents` (or the explicitly configured production value) and `public=false`.
4. Run `.github/workflows/production-validation.yml` or `scripts/production_smoke.py` against the deployed URLs.
5. Require `/health` = 200 and `/ready` = 200. Production `/ready` transitively verifies database connectivity, ClamAV PING/PONG and private-bucket metadata.
6. Confirm FHIR metadata returns `CapabilityStatement`, FHIR `4.0.1`, and `application/fhir+json`.
7. Confirm unauthenticated `/docs`, `/redoc`, `/openapi.json` and `/internal/metrics` remain hidden.

## Malware/storage recovery drill

Use a dedicated non-PHI test patient/account and a harmless fixture only.

1. Upload the harmless fixture through the authorized document workflow.
2. Confirm the persisted scan state moves through the expected pending/processing state and reaches clean before download becomes available.
3. Restart the malware worker while one harmless fixture remains pending. Do not delete the persisted database row.
4. After restart, confirm the worker reclaims the pending scan and reaches a terminal clean state.
5. Confirm the document can be downloaded only through the MedFlow authorized endpoint; do not expose a public Supabase URL.
6. Verify the Supabase bucket is still private after the drill.
7. Verify `/ready` remains or returns healthy after worker recovery.

## ClamAV fail-closed drill

1. Temporarily stop or isolate the private ClamAV service in an approved maintenance window.
2. Confirm production `/ready` returns 503 while ClamAV cannot answer PING/PONG.
3. Confirm new uploads are not released as clean while the scanner is unavailable.
4. Restore ClamAV and wait for a successful PONG.
5. Confirm `/ready` returns 200 and persisted pending scans are recovered by the worker.

## Backend recovery drill

1. Trigger a controlled backend restart/redeploy.
2. Verify migrations complete successfully and the release starts without manual schema edits.
3. Verify `/health`, then `/ready`, then the production smoke workflow.
4. Verify patient, clinician and admin frontends can reach the restarted API without CORS or cookie failures.
5. Verify no bearer token, storage service key, observability token, patient payload, or document content appears in application logs.

## Pass criteria

The live P1 operational gate is PASS only when all baseline checks and recovery drills above have attached evidence. A green repository CI run by itself is not evidence that the actual Render services or Supabase bucket were validated.
