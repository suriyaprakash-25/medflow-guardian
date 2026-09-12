# MedFlow Guardian API Endpoint Test Report

**Test date:** 2026-09-13

**Commit tested:** `e67d1ed20648afd3426543ae79aab26dd874de6b`

**Branch:** `dev`

**Overall result:** **PASS — complete repository API endpoint certification**

## 1. Executive result

- FastAPI exposes **72 HTTP operations** and **1 WebSocket route**.
- Newman reached all 72 HTTP operations against the running FastAPI service and
  migrated PostgreSQL 15 database.
- Static frontend/backend contract analysis found **74 frontend API call sites**;
  all 74 match a registered backend HTTP method and path.
- Newman executed **72 requests, 72 test scripts, and 146 assertions**, with
  **zero failures**. Exact status codes and security headers were asserted.
- GitHub Actions run `34721700316`, on this exact commit, completed against
  PostgreSQL 15 with **281 passed, 2 skipped** in the full backend suite.
- Targeted FHIR, session/WebSocket, storage/malware, deployment, database, and
  production-hardening stages all passed in the same run.
- The canonical collection is generated from FastAPI OpenAPI, and a regression
  test fails CI if any HTTP operation is missing, duplicated, or lacks an
  assertion. All legacy collections now have effective assertions as well.
- The obsolete `POST /api/auth/token` request was replaced with the implemented
  `POST /api/auth/login` endpoint.
- Success-path testing exposed and corrected a doctor readings/messages defect:
  those routes and the doctor portal now provide trusted hospital, purpose, and
  server-resolved consent context to Model A.

The complete repository API surface is certified in the isolated CI integration
environment. Production Render/Supabase URLs and credentials were not supplied,
so this report does not claim a production-environment smoke test.

## 2. Evidence used

| Check | Result | Evidence |
| --- | --- | --- |
| OpenAPI route inventory | PASS | 72 HTTP operations across 16 tags |
| Frontend-to-backend route alignment | PASS | 74 of 74 detected patient/doctor/admin API calls match registered operations |
| Newman route contract | PASS | 72 requests, 72 scripts, 146 assertions, 0 failures |
| Liveness | PASS | `GET /health` returned `200` |
| Database readiness | PASS | `GET /ready` returned `200` in Newman against PostgreSQL 15 |
| PostgreSQL-backed CI | PASS | Run `34721700316`: 281 passed, 2 skipped |
| Database migration and drift check | PASS | Alembic upgrade, round-trip, and `alembic check` passed |
| Logical backup/restore | PASS | Dump, clean restore, and restored-schema integrity tests passed |
| FHIR target suite | PASS | 49 tests passed |
| Session/WebSocket target suite | PASS | 11 tests passed |
| Storage/malware/audit target suite | PASS | 32 tests passed |
| Frontend builds | PASS | Patient, doctor, and admin applications passed |
| Complete Newman/Postman certification | PASS | Generated collection exactly matches the OpenAPI HTTP surface |
| Live deployed-environment verification | NOT RUN | No deployed base URL or test credentials were supplied |

## 3. Endpoint-family assessment

| Family | HTTP operations | Assessment |
| --- | ---: | --- |
| Access requests/grants | 8 | PASS — create, list, approve, reject, grant list and revoke flows verified |
| Admin | 8 | PASS — dashboard, audit, organization and staff lifecycle plus tenant denial verified |
| Appointments | 5 | PASS — create, patient/doctor lists, update and state rules verified |
| Audit | 2 | PASS — patient/doctor allow and wrong-role denial tested |
| Authentication | 9 | PASS — login, refresh rotation/replay, logout, logout-all, MFA, identity, profile update and password change verified |
| Clinical | 6 | PASS — prescription, lab and note create/list flows verified with consent context |
| Consent | 3 | PASS — create, immutable policy version and lifecycle transition tested |
| Documents | 4 | PASS for repository scope — upload authorization, listing, metadata, download, quarantine and storage boundary tested |
| Health | 2 | PASS — liveness and PostgreSQL-backed readiness verified |
| Hospital/visit aliases | 4 | PASS — listing, detail, patient and doctor visit routes verified |
| Interoperability | 3 | PASS for declared subset — both FHIR Consent import paths and authorized FHIR export tested |
| Monitoring/messages | 5 | PASS — patient/doctor readings and bidirectional messaging verified with consent enforcement |
| Notifications | 3 | PASS — listing, single-read ownership and read-all verified |
| Triage | 4 | PASS — create/list/patient-list/update plus role and organization isolation tested |
| Users | 4 | PASS — practitioner and patient profile read/update verified |
| Visits | 2 | PASS — visit creation and patient-history isolation tested |
| WebSocket | 1 | PASS for repository scope — token, session revocation and outbound authorization tests passed |

## 4. Postman collection audit

| Collection | Requests | Test scripts | Finding |
| --- | ---: | ---: | --- |
| `MedFlow-All-Endpoints` | 72 | 72 | Canonical generated contract; executed in CI with 146 assertions |
| `MedFlow-Admin-API` | 5 | Collection policy | Asserts success/security headers and captures the login token |
| `MedFlow-Admin-Platform` | 8 | Collection policy | Asserts positive `200` and negative `403` authorization scenarios |
| `MedFlow-Security-Core` | 4 | Collection policy | Correct login URL, assertions, token capture and consent-ID capture |

The canonical collection is regenerated in CI and compared with the committed
file. Route drift, duplicate requests, missing assertions, or reintroduction of
`/api/auth/token` fails the build.

## 5. Success-path gap closure

All 29 routes previously listed as lacking an explicit success-path case now
have PostgreSQL-backed coverage in
`backend/tests/test_remaining_endpoint_success_paths.py`. This includes access
request/grant lifecycle, organization/staff mutations, appointment creation and
doctor listing, password/profile changes, clinical creation/listing, monitoring,
messaging, notifications, patient profiles, visit aliases, hospital detail, and
database readiness.

Both FHIR Consent import URLs retain their existing shared-helper behavioral
tests. The complete suite passed with 281 tests and two intentional skips.

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

**All registered repository API endpoints are correctly routed and verified for
the tested integration scope.** The assertion-based Newman run, PostgreSQL-backed
success/security tests, WebSocket tests, migration checks, live ClamAV protocol
tests, backup/restore rehearsal, and all three frontend builds passed.

This is a repository and isolated-integration certification. A final smoke test
must still be executed after deployment before making claims about the actual
production network, secrets, Supabase Storage bucket, or external infrastructure.
