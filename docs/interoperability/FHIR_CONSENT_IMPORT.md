# FHIR R4 Consent Import → MedFlow Governance

## Purpose

This phase adds a one-way import bridge from an external FHIR R4 `Consent` resource into the existing MedFlow Guardian governance model.

The imported FHIR resource **does not become an authorization engine**. It is transformed into ordinary MedFlow data:

```text
FHIR Consent
    ↓
validated mapping
    ↓
Consent
    ↓
immutable ConsentPolicyVersion
    ↓
append-only ConsentState
    ↓
existing AuthorizationService + ConsentService
```

All later protected operations continue through the existing Model A authorization path.

## Import endpoint

```text
POST /api/interoperability/consents/import
```

Current trust policy: an authenticated patient may import a FHIR Consent only for their own MedFlow patient identity. Provider or service-to-service ingestion is intentionally not inferred from a public FHIR payload. A future trusted integration identity must be authenticated and authorized separately before that mode is enabled.

The endpoint invokes the existing Central Authorization Engine before persistence. The CAE currently groups interoperability under `ResourceType.FHIR_EXPORT`; `Operation.CREATE` distinguishes this import operation in authorization/audit context. A later authorization-taxonomy cleanup may introduce a dedicated interoperability-import resource type without changing the trust model.

## Supported deterministic mapping

### Status

| FHIR `Consent.status` | MedFlow `ConsentState.status` |
| --- | --- |
| `draft` | `draft` |
| `proposed` | `draft` |
| `active` | `active` |
| `rejected` | `cancelled` |
| `inactive` | `revoked` |
| `entered-in-error` | `cancelled` |

Other statuses are rejected.

### Patient scope

```text
Consent.patient.reference = Patient/<MedFlow user id>
```

The referenced MedFlow user must exist with role `patient`.

### Practitioner scope

```text
Consent.performer[0].reference = Practitioner/<MedFlow user id>
```

At most one practitioner is currently supported. The referenced user must exist with role `doctor`.

### Organization scope

```text
Consent.organization[0].reference = Organization/<MedFlow hospital id>
```

At most one organization is currently supported. The hospital must exist and be active. If practitioner and organization are both present, the practitioner must have an active `HospitalStaff` membership for that hospital.

### Purpose

MedFlow imports only its explicit purpose coding system:

```text
system = https://medflowguardian.example/fhir/purpose
```

Each `Consent.provision.purpose[].code` is copied into:

```json
{
  "allowed_purposes": ["..."]
}
```

Unknown purpose coding systems are rejected rather than guessed.

### Action → operation

Only mappings that are explicit and lossless enough for the current MedFlow operation vocabulary are supported:

| FHIR consent action | MedFlow operation |
| --- | --- |
| `access` | `read` |
| `disclose` | `download` |

Other FHIR consent action codes are rejected.

## Fail-closed rules

MedFlow currently rejects FHIR policy constructs that it cannot represent without broadening or changing the original consent semantics. This includes:

- `Consent.provision.type = deny`
- `Consent.provision.period`
- nested `Consent.provision.provision`
- `actor`
- `securityLabel`
- `class`
- `code`
- `dataPeriod`
- `data`

These are not silently ignored. They return a validation error until a lossless internal mapping is implemented.

This rule is particularly important for `period`: ignoring an external expiration window would violate MedFlow's RIGHT TIME requirement by turning a temporary consent into an indefinite one.

## Persistence contract

A successful import creates exactly one new set of governance records in one transaction:

```text
Consent
  ├─ patient_id
  ├─ doctor_id (optional)
  ├─ hospital_id (optional)
  └─ lifecycle status

ConsentPolicyVersion
  ├─ version_number = 1
  ├─ allowed_purposes
  ├─ allowed_operations
  └─ provenance

ConsentState
  ├─ policy_version_id
  ├─ mapped lifecycle status
  └─ reason = Imported from FHIR R4 Consent
```

The policy payload records import provenance:

```json
{
  "provenance": {
    "source": "FHIR_R4_CONSENT_IMPORT",
    "source_resource_id": "<FHIR Consent.id or null>"
  }
}
```

The external resource identifier is metadata only. It is never trusted as an internal MedFlow primary key.

## Authorization behavior after import

Once imported, the FHIR resource has no special authorization semantics. A doctor accessing protected patient information must still satisfy the normal MedFlow path:

```text
Authentication
  ↓
CAE base authorization
  ↓
patient / doctor / organization binding
  ↓
ConsentService
  ↓
current authoritative ConsentState
  ↓
purpose check
  ↓
operation check
  ↓
ALLOW / DENY
```

Tests cover successful import, cross-patient denial, provider import denial, purpose/action mapping, revoked status mapping, practitioner-organization membership, imported-policy CAE use, wrong-purpose denial, and fail-closed handling of unsupported FHIR constraints.

## Deliberately deferred

This phase does **not** claim complete FHIR Consent interoperability. Deferred items include:

- trusted service-to-service FHIR ingestion identities
- idempotent external-resource reconciliation / update semantics
- temporal (`period`) mapping into MedFlow authorization state
- nested permit/deny policy trees
- FHIR actor/data/security-label constraints
- terminology-service based purpose translation
- complete FHIR profile/conformance validation

Those should be implemented in later interoperability/conformance phases rather than guessed in this importer.
