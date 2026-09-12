# PHASE 6: GOLDEN END-TO-END SECURE DOCUMENT WORKFLOW

## 1. Objective
To demonstrate that the Phase 5 Consent, Policy, and Enforcement-State framework successfully and unconditionally protects the release of medical document bytes behind the StorageService boundary.

## 2. Security Architecture
The security boundary enforces a strictly ordered pipeline:
```mermaid
sequenceDiagram
    Doctor->>+FastAPI: Request Document
    FastAPI->>Authentication: Verify JWT
    Authentication-->>FastAPI: Identity (Doctor_ID)
    FastAPI->>+CAE: Authorize()
    CAE->>Organization: Check Membership / Uploader
    CAE->>AccessGrant: Check Active Relationship
    CAE->>+Consent State: Evaluate()
    Consent State->>Consent State: Assert Authoritative == Enforcement
    Consent State->>Policy Evaluation: Assert Request Purpose == Allowed
    Policy Evaluation-->>-Consent State: Pass
    Consent State-->>-CAE: ALLOW
    CAE-->>-FastAPI: Decision (ALLOW)
    FastAPI->>+StorageService: Download()
    StorageService-->>-FastAPI: Bytes
    FastAPI-->>-Doctor: StreamingResponse
```

## 3. Golden Workflow & Actors
- **Actors**: Patient A, Doctor A, Hospital A.
- **Data**: MedicalDocument (stored in Supabase).
- **Consent**: Active Consent, Policy allows `TREATMENT` + `DOWNLOAD`.

## 4. Positive Path
When Doctor A has an active grant and requests `purpose=TREATMENT` with an `enforcement_state_id` matching the database's `authoritative_state_id`, the system streams the document successfully.

## 5. Stale-State Path
If Patient A revokes the consent, a new `ConsentState` row is appended (`status=REVOKED`), advancing the authoritative state.
If Doctor A (e.g. via a cached UI state) requests with the *old* `enforcement_state_id`, the backend detects the mismatch and returns `403 Forbidden` (`ENFORCEMENT_STATE_STALE`). StorageService is **never accessed**.

## 6. Revocation Path
If Doctor A requests with the *synchronized* (new) `enforcement_state_id`, but the authoritative state indicates `REVOKED`, the backend returns `403 Forbidden` (`OPERATION_NOT_ALLOWED: revoked`). StorageService is **never accessed**.

## 7. Known Limitations
- **Streaming Semantics**: The enforcement is checked ONCE per HTTP request, before the bytes begin streaming. A revocation occurring precisely mid-stream cannot interrupt the already-flowing TCP packets.

## 8. Exact Commands Used
```bash
pytest tests/test_golden_workflow.py -v
alembic upgrade head
```

## 9. Exact Test Results
`PASSED` (3 passed in 61.77s). The live database securely executes the Stale-State mechanism.

## 10. Phase 7 Prerequisites
None. Ready to proceed.
