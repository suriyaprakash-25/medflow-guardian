# Phase R6 — FHIR / Interoperability Reality Audit

**Branch:** `fix/r6-fhir-interoperability-consolidation`  
**Base:** `dev` at `c013cee5a2f36339505576f4e93a643c157b3bde` when R6 began  
**Evidence run:** GitHub Actions `34701639061` on code head `152fc1544be7a78659cb99ee1dfee67bb3814d6e`  
**Status of this document:** repository audit for the declared MedFlow FHIR subset, not a FHIR conformance certification.

## 1. Architecture boundary

MedFlow currently uses the Model A topology: the FastAPI backend is the collocated Policy Decision Point and Policy Enforcement Point. FHIR payloads are interoperability inputs/outputs only. They do not become authorization decisions and they do not supply an authoritative enforcement snapshot.

The browser/client is not trusted to choose consent state, organization membership, user role, or authorization outcome. The R6 adversarial tests include request material named `enforcement_state_id`; it does not alter consent ownership or role checks.

## 2. Pre-R6 repository reality

The `dev` baseline contained two FHIR Consent import implementations with overlapping but non-identical semantics:

- `app/services/interoperability/fhir_consent.py`
- `app/services/interoperability/fhir_consent_import.py`

The repository also had FHIR serializers and a patient bundle export route. The duplicate importer paths were a policy-engine risk because different entry points could interpret the same external Consent differently.

R6 removes that semantic split. `fhir_consent.py` is now the only mapping/persistence implementation. `fhir_consent_import.py` remains only as a compatibility shim that delegates to the canonical importer and requires authenticated actor plus source provenance.

## 3. Public interoperability endpoints in the R6 branch

### Consent import

Canonical endpoint:

`POST /api/interoperability/fhir/consents/import`

Deprecated compatibility alias:

`POST /api/interoperability/consents/import`

Both call the same internal helper, run the same canonical mapper, invoke the Central Authorization Engine for `CONSENT + CREATE`, and persist through the same importer.

The authenticated patient must match `Consent.patient`. A doctor cannot create a patient's imported consent. The compatibility alias has no alternate semantic path.

### Patient FHIR export

`GET /api/interoperability/patients/{patient_id}/export`

The route requires an explicit `purpose`. Practitioner export requires explicit consent and an organization-scoped consent. Authorization occurs before patient/clinical/document transformation. Practitioner queries are then constrained to the consent hospital so one organization authorization decision cannot release records belonging to another hospital.

There is no dedicated public REST endpoint in this branch that exports a MedFlow Consent resource by ID. The Consent serializer is exercised directly by round-trip tests; do not interpret its presence as a public Consent export API.

## 4. Declared supported FHIR R4 subset

R6 implements a deliberately narrow subset rather than claiming general FHIR R4 support.

| Resource / construct | R6 support | Notes |
| --- | --- | --- |
| `Consent` import | Supported subset | Canonical fail-closed semantic mapping into MedFlow Consent, immutable policy-version history, and append-only state history |
| `Consent` serialization | Supported subset | Internal policy to a conservative R4 representation; fails when an operation set cannot be represented without broadening authority |
| `Patient` | Export serialization | Basic identity/contact fields used in patient Bundle export |
| `Practitioner` | Serialization helper | Basic identity/contact subset; not a general Practitioner API |
| `Organization` | Serialization helper | Basic organization subset; not a general Organization FHIR API |
| `MedicationRequest` | Export serialization | Uses `medicationCodeableConcept` for current domain model |
| `Observation` | Export serialization | Maps current LabResult fields and internal status values to the declared subset |
| `DocumentReference` from ClinicalNote | Export serialization | Clinical note body is UTF-8 base64 in `Attachment.data` |
| `DocumentReference` from MedicalDocument | Export metadata only | Does not expose the private Supabase object key or direct protected-storage URL |
| `Bundle` | Export | `collection` Bundle used for the authorized patient export |

No external FHIR validator, Implementation Guide conformance suite, profile validator, CapabilityStatement conformance test, or certification suite was run in R6. Therefore the appropriate claim is **“implemented and tested MedFlow's declared FHIR R4 subset”**, not “FHIR R4 compliant.”

## 5. Canonical FHIR Consent profile

The importer requires:

- `resourceType = Consent`
- stable FHIR `id` for provenance/idempotency
- supported R4 `status`
- `scope` containing `patient-privacy`
- category containing LOINC `59284-0`
- numeric internal `Patient/{id}` subject reference
- `policy` or `policyRule`
- an explicit top-level provision `type = permit`
- supported consent actions from `http://terminology.hl7.org/CodeSystem/consentaction`
- supported purposes from `http://terminology.hl7.org/CodeSystem/v3-ActReason`
- optional scoped actors represented as at most one numeric Practitioner and at most one numeric Organization using the declared MedFlow actor-role profile.

The mapping does not infer authorization from client-supplied organization fields or from an `enforcement_state_id` field.

## 6. Purpose, action, and status mappings

### Purpose mapping

| FHIR v3 ActReason code | MedFlow purpose |
| --- | --- |
| `TREAT` | `TREATMENT` |
| `HPAYMT` | `BILLING` |
| `HOPERAT` | `HEALTHCARE_OPERATIONS` |
| `RESCH` | `RESEARCH` |
| `PATRQT` | `PATIENT_REQUEST` |
| `PUBHLTH` | `PUBLIC_HEALTH` |

Unknown purposes fail closed.

### Action mapping

| FHIR consent action | MedFlow operations |
| --- | --- |
| `access` | `read` |
| `use` | `read` |
| `collect` | `create` |
| `disclose` | `read`, `download` |
| `correct` | `read`, `update` |

For export, MedFlow chooses FHIR actions only when their imported union exactly equals the internal allowed-operation set. It will not use a broader FHIR action merely to make serialization succeed. For example, an internal policy granting only `download` is rejected for Consent export because the supported `disclose` mapping would also grant `read` if re-imported.

### Status mapping

Inbound FHIR status mapping:

- `draft` → `draft`
- `proposed` → `draft`
- `active` → `active`
- `rejected` → `cancelled`
- `inactive` → `revoked`
- `entered-in-error` → `cancelled`

Outbound internal states are conservative. Internal `suspended`, `revoked`, `expired`, and `superseded` all serialize as the non-authorizing FHIR status `inactive`. This loses internal-state specificity, so it is not a lossless reverse mapping across every status.

## 7. Fail-closed unsupported semantics

The current internal policy engine cannot enforce every R4 Consent constraint. R6 therefore rejects, rather than silently discards, policy-relevant semantics that could narrow or alter authorization:

- provision `period`
- `data` and `dataPeriod`
- `securityLabel`
- provision `class`
- provision `code`
- nested provisions
- deny provisions
- missing/implicit provision type
- nonempty top-level `verification`
- unsupported action/purpose systems or codes
- ambiguous/non-numeric subject or scoped actor references

`period` is intentionally rejected until RIGHT TIME can be represented and checked dynamically by the authorization/consent engine. An expired period is not converted once at import time and then treated as permanent policy state.

## 8. Provenance, idempotency, conflict and replay behavior

An imported Consent is identified by normalized `source_system + resource_id`.

- Identical repeated imports return the existing Consent/policy/state and create no new history rows.
- Changed content using the same non-null `meta.versionId` is rejected as a conflict.
- Doctor/organization scope changes are included in conflict detection even though they are stored on the Consent row rather than solely inside the policy JSON.
- A changed import requires `meta.lastUpdated` both on the previously stored external representation and the incoming representation.
- The incoming timestamp must be strictly later. Older/equal changed resources are rejected as stale/replayed updates.
- PostgreSQL uses a transaction-scoped advisory lock keyed by source system/resource ID to serialize concurrent imports, including the first-import case where no row exists to lock yet.

FHIR `meta.versionId` is treated as opaque identity/version provenance, not as a sortable integer.

## 9. Storage and PHI release boundary

The patient export route authorizes first and transforms second. It does not read a protected document binary from storage before the authorization result.

FHIR `DocumentReference` metadata for `MedicalDocument` deliberately omits the private `stored_filename` and does not provide a direct private-storage URL. Protected binary release remains through MedFlow's authorized backend document path.

## 10. Evidence observed in CI

GitHub Actions run `34701639061` completed successfully against PostgreSQL 15:

- Alembic `upgrade head`: PASS
- targeted R6 interoperability suite: **49 passed, 2 warnings**
- complete backend suite: **153 passed, 2 warnings**
- patient-app build: PASS
- doctor-portal build: PASS
- admin-portal build: PASS

The two persistent pytest warnings in that run were:

1. `PytestConfigWarning: Unknown config option: asyncio_mode`
2. Starlette TestClient/httpx deprecation warning.

The PostgreSQL service also logs non-fatal `role "root" does not exist` noise because the health probe runs as the container OS user rather than the configured database role; the service still becomes healthy and migrations/tests complete.

## 11. Scope boundary and integration caveat

R6 was branched from `dev`, not from the R5 remediation branch. It therefore verifies R6 against its current `dev` base only. R1–R5 remediation work that remains on separate branches is not automatically part of the R6 evidence.

A future cumulative integration branch must combine the remediation branches and rerun migrations, targeted security suites, the full backend suite, frontend builds, and release gates before any production-readiness decision.
