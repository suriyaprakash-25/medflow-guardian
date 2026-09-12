# PHASE 5: CONSENT, POLICY EVALUATION & ENFORCEMENT-STATE VERIFICATION

## Overview

Phase 5 introduces a robust, immutable, and verifiable **Consent Data Model** into the MedFlow Guardian architecture. 
It establishes a firm security perimeter where the **Central Authorization Engine (CAE)** actively prevents protected medical data release unless the **Authoritative Consent State** explicitly permits the operation.

## Key Invariants Established

1. **Stale-State Enforcement Denial (Fail Closed)**
   If a client requests a resource under an Enforcement State (e.g. `consentStateId = 42`) that no longer matches the Authoritative Consent State (e.g. `consentStateId = 43`), the operation is instantly **DENIED** with reason `ENFORCEMENT_STATE_STALE`.

2. **Purpose-Based Access**
   Every Consent policy has an immutable `ConsentPolicyVersion` that dictates `allowed_purposes`. Access must match these purposes or it is **DENIED** with reason `PURPOSE_NOT_ALLOWED`.

3. **Immutable History**
   `ConsentState` is an append-only ledger. When a patient revokes a consent, a new `ConsentState` row is appended marking the status as `REVOKED`. The previous states are never deleted, ensuring full auditability of the governance lifecycle.

## Architectural Changes

### 1. Governance Data Model (`app/models/consent.py`)
- **`Consent`**: Represents the overarching governance decision between a Patient and a Doctor/Hospital.
- **`ConsentPolicyVersion`**: The immutable ruleset (`allowed_purposes`, `allowed_operations`).
- **`ConsentState`**: The append-only state history. The row with the most recent `created_at` represents the **Authoritative State**.

### 2. Access Integration (`app/models/access.py` & `app/api/access.py`)
- `DocumentAccessGrant` now acts as the *Application Relationship* layer, and holds a foreign key to `Consent` (the *Governance layer*).
- When a Patient approves a `DocumentAccessRequest`, the system automatically generates an active `Consent`, policy version, and state history.
- When a Patient revokes a grant, the system automatically inserts a `REVOKED` state into the `ConsentState` ledger.

### 3. Policy Evaluation Engine (`app/services/consent.py`)
- Evaluates `purpose` and `enforcement_state_id`.
- Sits seamlessly within the Central Authorization Engine's pipeline. Base logic handles identity and organization checking; Consent Engine handles governance validation.

### 4. Enforcement Point (`app/api/document.py`)
- The `download_document` API directly accepts `purpose` and `enforcement_state_id`.
- The bytes are securely transferred through the FastAPI backend (`StreamingResponse`) rather than issuing long-lived Signed URLs. This provides the ultimate "Instant Revocation" capability, because every single byte download request evaluates the authoritative state in real-time.

## Verification

The system was verified using a custom unit test suite (`tests/test_consent_engine.py`) that explicitly proves:
- Active policies with correct purpose and enforcement state are allowed.
- Mismatched `enforcement_state_id` requests are denied.
- Operations against `REVOKED` consent states are denied.
- Operations with mismatched purposes are denied.
