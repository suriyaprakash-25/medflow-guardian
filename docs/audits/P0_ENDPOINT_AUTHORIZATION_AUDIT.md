# P0 Endpoint Authorization Surface Audit

## Decision

All REST endpoints that operate on application resources must terminate at the
MedFlow Central Authorization Engine (Model A). Authentication/session routes
establish identity and are not resource authorization endpoints. The WebSocket
route authenticates the connection and performs live authorization for outbound
messages in `api/websockets.py`.

## Audited surface

| Area | Route group | Enforcement after remediation |
|---|---|---|
| Access governance | access requests and grants | CAE request, list, approve, reject, and revoke decisions |
| Consent governance | consent create, policy version, transition | reviewed `_enforce_consent_write` CAE boundary |
| Documents | upload, patient list, metadata discovery, download | CAE; metadata remains hospital and visit scoped; downloads use trusted server-side grant context |
| Clinical | prescriptions, labs, notes | reviewed `_authorize_clinical_access` CAE boundary |
| Interoperability | FHIR Consent import and patient export | reviewed import boundary and direct CAE export decision |
| Appointments and visits | create, list, update | CAE, including doctor self-list binding |
| Triage and readings | create, list, update | CAE plus organization/relationship-scoped queries |
| Messaging | send and history | CAE relationship checks |
| Notifications | list and mark read | CAE plus recipient-scoped queries |
| Profiles and hospitals | read/update/list | CAE role and active-account checks |
| Administration and audit | dashboard, staff, organizations, logs | CAE with tenant-scoped queries |

## Closed findings

1. Access-request and grant routes previously duplicated membership and ownership
   checks locally. They now obtain all resource decisions from Model A.
2. Doctor appointment listing now binds the requested doctor identifier to the
   authenticated practitioner.
3. Patient document listing, notification mutations, triage lists, patient
   readings, hospitals, visits, and profile routes now invoke Model A rather than
   relying only on identity dependencies or query filters.
4. Pre-consent operations are explicitly marked with `requires_consent=False`.
   This prevents the consent evaluator from blocking the act of requesting
   consent while retaining CAE role, relationship, and organization checks.
5. CI now statically rejects a newly introduced resource REST endpoint that does
   not call the CAE directly or through a reviewed boundary helper.
6. Denials for nonexistent patient, organization, consent, or consent-state IDs
   preserve attempted identifiers in audit metadata without violating audit-log
   foreign keys or poisoning the request transaction.

## Fail-closed rules

- Unrecognized resource/operation combinations deny by default.
- Inactive actors are denied by the CAE.
- Practitioner FHIR and document releases require trusted server-side consent
  context and an explicit purpose.
- Document bytes are released only after a clean malware state and durable audit
  persistence.
- Cross-patient, cross-practitioner, and cross-organization identifiers are not
  accepted as authority.

## Verification gates

- `tests/test_endpoint_authorization_surface.py`
- `tests/test_authorization_endpoints.py`
- `tests/test_authorization_engine.py`
- `tests/security/test_consent_mutation_authorization.py`
- `tests/test_admin_tenant_isolation.py`
- `tests/test_r5_consent_context_propagation.py`
- `tests/test_r8_session_websocket_rate_limit.py`
