# P0 — Direct CAE enforcement for FHIR export

## Protected operation

`GET /api/interoperability/patients/{patient_id}/export`

Patient self-export requires an explicit purpose but does not require consent.
Practitioner export requires both `purpose` and `consent_id` query parameters.

## Practitioner decision chain

1. Authenticated and active practitioner.
2. Explicit consent exists and matches the supplied `consent_id`.
3. Consent belongs to the requested patient.
4. Practitioner scope matches when the consent names a practitioner.
5. Organization scope and active membership match when the consent names an organization.
6. A doctor-patient visit exists in the consent's organization when organization-scoped.
7. The latest authoritative `ConsentState` is active.
8. The active `ConsentPolicyVersion` permits the supplied purpose.
9. The policy permits the `read` operation.

Every missing, stale, mismatched, revoked, or unsupported input results in
`DENY`. FHIR remains a serialization boundary; all decisions terminate at the
MedFlow Central Authorization Engine.

## Certification cases

| Context | Expected |
| --- | --- |
| Patient exports own record with purpose | ALLOW |
| Patient exports another patient | DENY |
| Practitioner omits consent ID | DENY |
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
