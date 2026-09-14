# P0 — Direct CAE enforcement for FHIR export

## Protected operation

`GET /api/interoperability/patients/{patient_id}/export`

Patient self-export requires an explicit purpose but does not require third-party consent.
Practitioner export requires explicit `purpose` and `hospital_id` scope. The browser does **not** provide a consent ID as authorization authority.

## Practitioner decision chain

1. Authenticated and active practitioner.
2. Practitioner supplies the intended organization (`hospital_id`) and purpose only.
3. Backend resolves the newest ACTIVE consent explicitly bound to the exact patient, practitioner and organization using `resolve_active_scoped_consent()`.
4. The resolved consent ID is injected into trusted `AuthorizationContext` server-side.
5. Active practitioner membership must match the organization.
6. A doctor-patient visit must exist in that organization.
7. `ConsentService` reloads and validates the authoritative consent and latest append-only `ConsentState`.
8. The latest state must be ACTIVE.
9. The active immutable `ConsentPolicyVersion` must be currently valid.
10. The policy must permit the supplied purpose and `read` operation.
11. Exported clinical resources are filtered to the resolved organization scope.

Every missing, stale, mismatched, revoked or unsupported context results in `DENY`. FHIR remains a serialization boundary; all decisions terminate at the MedFlow Central Authorization Engine and `ConsentService` inside the collocated Model A backend.

## Certification cases

| Context | Expected |
| --- | --- |
| Patient exports own record with purpose | ALLOW |
| Patient exports another patient | DENY |
| Practitioner omits hospital scope | DENY |
| No active exact-scope consent exists | DENY |
| Consent belongs to another patient | DENY |
| Consent is scoped to another practitioner | DENY |
| Consent organization differs | DENY |
| Practitioner membership is inactive | DENY |
| No doctor-patient visit exists | DENY |
| Visit exists only in another organization | DENY |
| Consent is revoked or otherwise inactive | DENY |
| Purpose is not allowed | DENY |
| Read operation is not allowed | DENY |
| Every required control matches | ALLOW |
