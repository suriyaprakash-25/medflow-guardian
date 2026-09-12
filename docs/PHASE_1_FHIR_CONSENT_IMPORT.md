# Phase 1 — FHIR R4 Consent import

## Boundary

FHIR Consent is imported as policy data. It never acts as a PDP or PEP. The
resulting `ConsentPolicyVersion` and `ConsentState` are evaluated through the
existing MedFlow Central Authorization Engine.

## Endpoint

`POST /api/interoperability/fhir/consents/import?source_system=https://fhir.example.org`

The authenticated actor must be the active MedFlow patient identified by
`Consent.patient`. Numeric `Patient/{id}`, `Practitioner/{id}`, and
`Organization/{id}` references are the only supported identity bridge until a
formal cross-system identifier registry exists.

## Deterministic mapping

| FHIR R4 input | MedFlow output |
| --- | --- |
| `status=draft` or `proposed` | `draft` |
| `status=active` | `active` (or `draft`/`expired` when the provision period requires it) |
| `status=rejected` or `entered-in-error` | `cancelled` |
| `status=inactive` | `revoked` |
| action `access` or `use` | operation `read` |
| action `collect` | operation `create` |
| action `disclose` | operations `read`, `download` |
| action `correct` | operations `read`, `update` |
| purpose `TREAT` | `TREATMENT` |
| purpose `HPAYMT` | `BILLING` |
| purpose `HOPERAT` | `HEALTHCARE_OPERATIONS` |
| purpose `RESCH` | `RESEARCH` |
| purpose `PATRQT` | `PATIENT_REQUEST` |
| purpose `PUBHLTH` | `PUBLIC_HEALTH` |

R4 defines controlled operations in `Consent.provision.action`; therefore the
implementation maps `action`, not `provision.code` (which identifies affected
content). Unknown codes, deny rules, nested rules, invalid periods, ambiguous
actor scopes, and missing mandatory R4 structure are rejected fail-closed.

## Versioning and provenance

`source_system + Consent.id` uniquely identifies an imported resource. A changed
re-import supersedes the current policy metadata, creates the next immutable
policy payload, and appends a new authoritative state. An identical re-import
is idempotent. Only FHIR provenance metadata is stored; the raw external payload
is not copied into the policy record. A transaction-scoped PostgreSQL advisory
lock plus database uniqueness constraints serialize concurrent first imports.
