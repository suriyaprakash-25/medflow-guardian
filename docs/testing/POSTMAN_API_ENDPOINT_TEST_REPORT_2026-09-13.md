# MedFlow Guardian API Endpoint Test Report

**Test date:** 2026-09-13  
**Commit tested:** `e1aafdfe672715e2acf77aea8874fba04ae9469d`  
**Branches:** `main` and `dev`  
**Overall result:** **PARTIALLY CERTIFIED — application suite green; Postman coverage incomplete**

## 1. Executive result

- FastAPI exposes **72 HTTP operations** and **1 WebSocket route**.
- An isolated route/security smoke test reached all 72 HTTP operations.
- Static frontend/backend contract analysis found **74 frontend API call sites**;
  all 74 match a registered backend HTTP method and path.
- Results were 68 expected `401` responses for invalid bearer tokens, two `200`
  responses, one expected request-validation `422`, and one expected local
  readiness `503`. There were **zero unexpected server errors**.
- GitHub Actions run `34719870905`, on this exact commit, completed against
  PostgreSQL 15 with **273 passed, 2 skipped** in the full backend suite.
- Targeted FHIR, session/WebSocket, storage/malware, deployment, database, and
  production-hardening stages all passed in the same run.
- The three checked-in Postman collections contain 17 requests representing
  only **13 valid distinct API operations**, and contain **zero `pm.test`
  assertions**. They are therefore request samples, not a complete executable
  endpoint certification suite.

The current evidence supports that the routed API and tested business/security
flows are working on an isolated PostgreSQL database. It does **not** prove that
every success path works against a deployed Render/Supabase/Storage/ClamAV
environment.

## 2. Evidence used

| Check | Result | Evidence |
| --- | --- | --- |
| OpenAPI route inventory | PASS | 72 HTTP operations across 16 tags |
| Frontend-to-backend route alignment | PASS | 74 of 74 detected patient/doctor/admin API calls match registered operations |
| Invalid/missing-auth routing smoke | PASS | All protected routes rejected the probe; no unexpected `5xx` |
| Liveness | PASS | `GET /health` returned `200` |
| Local readiness failure behavior | PASS | `GET /ready` returned controlled `503` with an intentionally unreachable DB |
| PostgreSQL-backed CI | PASS | Run `34719870905`: 273 passed, 2 skipped |
| Database migration and drift check | PASS | Alembic upgrade, round-trip, and `alembic check` passed |
| Logical backup/restore | PASS | Dump, clean restore, and restored-schema integrity tests passed |
| FHIR target suite | PASS | 49 tests passed |
| Session/WebSocket target suite | PASS | 11 tests passed |
| Storage/malware/audit target suite | PASS | 32 tests passed |
| Frontend builds | PASS | Patient, doctor, and admin applications passed |
| Complete Newman/Postman certification | FAIL | Collections are incomplete and contain no assertions |
| Live deployed-environment verification | NOT RUN | No deployed base URL or test credentials were supplied |

## 3. Endpoint-family assessment

| Family | HTTP operations | Assessment |
| --- | ---: | --- |
| Access requests/grants | 8 | PARTIAL — create, approve, and doctor-list flows tested; remaining operations need explicit Postman success cases |
| Admin | 8 | PARTIAL — dashboard, audit, organization creation, staff creation and tenant denial tested; update/delete success cases need explicit coverage |
| Appointments | 5 | PARTIAL — patient lists and update/state rules tested; create and doctor-list need explicit success tests |
| Audit | 2 | PASS — patient/doctor allow and wrong-role denial tested |
| Authentication | 9 | PARTIAL — login, refresh rotation/replay, logout, logout-all, MFA and identity tested; profile update and password-change endpoints need explicit route cases |
| Clinical | 6 | PARTIAL — authorization helpers are certified and selected flows tested; labs and several read/create paths need explicit HTTP success cases |
| Consent | 3 | PASS — create, immutable policy version and lifecycle transition tested |
| Documents | 4 | PASS for repository scope — upload authorization, listing, metadata, download, quarantine and storage boundary tested |
| Health | 2 | PARTIAL — liveness passed locally; readiness passed through CI database checks but was not tested against a deployed service |
| Hospital/visit aliases | 4 | PARTIAL — hospital listing tested; detail and alias list routes need explicit cases |
| Interoperability | 3 | PASS for declared subset — both FHIR Consent import paths and authorized FHIR export tested |
| Monitoring/messages | 5 | AUTH-ONLY — routing and authentication boundary passed; success-path HTTP tests are missing |
| Notifications | 3 | PARTIAL — listing and single-read ownership tested; read-all needs an explicit success case |
| Triage | 4 | PASS — create/list/patient-list/update plus role and organization isolation tested |
| Users | 4 | PARTIAL — practitioner profile tested; patient profile routes need explicit HTTP cases |
| Visits | 2 | PASS — visit creation and patient-history isolation tested |
| WebSocket | 1 | PASS for repository scope — token, session revocation and outbound authorization tests passed |

## 4. Postman collection audit

| Collection | Requests | Test scripts | Finding |
| --- | ---: | ---: | --- |
| `MedFlow-Admin-API` | 5 | 0 | Sends useful requests but does not capture login tokens or assert responses |
| `MedFlow-Admin-Platform` | 8 | 0 | Includes positive/negative scenarios by name only; expected status codes are not asserted |
| `MedFlow-Security-Core` | 4 | 0 | Contains one obsolete URL and no token/ID chaining |

Critical Postman defect:

- `POST /api/auth/token` in `MedFlow-Security-Core` is not a registered route
  and returned `404`. The implemented login route is `POST /api/auth/login`.

Required collection improvements:

1. Cover every OpenAPI operation, including multipart document upload and `/ws`.
2. Add setup/teardown fixtures for patient, doctor, organization admin, and
   platform admin identities.
3. Capture access tokens, refresh cookies, created IDs, consent versions, and
   organization IDs automatically.
4. Assert status code, schema, required response fields, ownership, tenant
   isolation, and fail-closed behavior.
5. Run the collection against an isolated deployed test environment with
   PostgreSQL, private Supabase Storage, and ClamAV available.

## 5. Routes requiring explicit per-route success-path tests

The following routes were reachable and enforced authentication, but the
current test scan did not find a direct success-path HTTP case for each route:

- `GET /api/access-grants/doctor`
- `GET /api/access-grants/patient`
- `POST /api/access-grants/{grant_id}/revoke`
- `GET /api/access-requests/patient`
- `POST /api/access-requests/{request_id}/reject`
- `PUT /api/admin/organization/{hospital_id}`
- `GET /api/admin/staff`
- `PUT /api/admin/staff/{membership_id}`
- `DELETE /api/admin/staff/{membership_id}`
- `POST /api/appointments`
- `GET /api/appointments/doctor/{doctor_id}`
- `POST /api/auth/change-password`
- `PATCH /api/auth/me`
- `POST /api/clinical/labs`
- `GET /api/clinical/labs/patient/{patient_id}`
- `GET /api/clinical/notes/patient/{patient_id}`
- `POST /api/clinical/prescriptions`
- `GET /api/hospitals/{hospital_id}`
- `POST /api/messages`
- `GET /api/messages/{user_id}`
- `POST /api/notifications/read-all`
- `POST /api/readings`
- `GET /api/readings/patient`
- `GET /api/readings/{patient_id}`
- `GET /api/users/patient-profile`
- `POST /api/users/patient-profile`
- `GET /api/visits/doctor`
- `GET /api/visits/patient`
- `GET /ready` against the deployed target

The two FHIR Consent import URLs were not found by the literal-path scan because
their tests call a shared `_post(path, payload)` helper. Manual inspection
confirmed both routes have database-backed behavioral tests and both passed CI.

## 6. Full registered HTTP inventory

### Access

- `POST /api/access-requests`
- `GET /api/access-requests/doctor`
- `GET /api/access-requests/patient`
- `POST /api/access-requests/{request_id}/approve`
- `POST /api/access-requests/{request_id}/reject`
- `GET /api/access-grants/doctor`
- `GET /api/access-grants/patient`
- `POST /api/access-grants/{grant_id}/revoke`

### Admin

- `GET /api/admin/dashboard`
- `GET /api/admin/staff`
- `GET /api/admin/audit`
- `POST /api/admin/organization`
- `PUT /api/admin/organization/{hospital_id}`
- `POST /api/admin/staff`
- `PUT /api/admin/staff/{membership_id}`
- `DELETE /api/admin/staff/{membership_id}`

### Appointments and visits

- `POST /api/appointments`
- `GET /api/appointments/patient/{patient_id}`
- `GET /api/appointments/patient`
- `GET /api/appointments/doctor/{doctor_id}`
- `PATCH /api/appointments/{appointment_id}`
- `POST /api/visits`
- `GET /api/visits/patient/{patient_id}`
- `GET /api/visits/patient`
- `GET /api/visits/doctor`

### Authentication and profiles

- `POST /api/auth/login`
- `POST /api/auth/mfa/verify`
- `POST /api/auth/mfa/enroll`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/auth/logout-all`
- `POST /api/auth/change-password`
- `GET /api/auth/me`
- `PATCH /api/auth/me`
- `GET /api/users/practitioner-profile`
- `POST /api/users/practitioner-profile`
- `GET /api/users/patient-profile`
- `POST /api/users/patient-profile`

### Clinical and documents

- `POST /api/clinical/prescriptions`
- `GET /api/clinical/prescriptions/patient/{patient_id}`
- `POST /api/clinical/labs`
- `GET /api/clinical/labs/patient/{patient_id}`
- `POST /api/clinical/notes`
- `GET /api/clinical/notes/patient/{patient_id}`
- `POST /api/documents`
- `GET /api/documents/patient`
- `GET /api/documents/metadata/{patient_id}`
- `GET /api/documents/{document_id}/download`

### Consent and interoperability

- `POST /api/consents`
- `POST /api/consents/{consent_id}/policy-versions`
- `POST /api/consents/{consent_id}/transition`
- `POST /api/interoperability/fhir/consents/import`
- `POST /api/interoperability/consents/import`
- `GET /api/interoperability/patients/{patient_id}/export`

### Hospital, triage, monitoring and communication

- `GET /api/hospitals`
- `GET /api/hospitals/{hospital_id}`
- `POST /api/triage/`
- `GET /api/triage/`
- `GET /api/triage/patient`
- `PATCH /api/triage/{id}/status`
- `POST /api/readings`
- `GET /api/readings/patient`
- `GET /api/readings/{patient_id}`
- `POST /api/messages`
- `GET /api/messages/{user_id}`
- `GET /api/notifications`
- `POST /api/notifications/{notification_id}/read`
- `POST /api/notifications/read-all`
- `GET /api/audit/patient`
- `GET /api/audit/doctor`

### Operations

- `GET /health`
- `GET /ready`
- `WEBSOCKET /ws`

## 7. Final verdict

**No current evidence shows a general API routing or authorization failure.**
The current PostgreSQL-backed automated suite is green, and every registered
HTTP operation passed the route/authentication smoke check without an unexpected
server error.

However, the answer to “are all endpoints fully verified through Postman?” is
**no**. The checked-in collections are incomplete, assertion-free, and one
request uses an obsolete URL. A complete Newman collection and a live isolated
deployment run are still required before issuing a full endpoint certification.
