# PHASE A PRE-IMPLEMENTATION SECURITY REALITY AUDIT

## 1. ConsentService Integration
- **Current Implementation:** `backend/app/services/consent.py` contains a fully modeled `ConsentService.evaluate()` method which handles purpose, active status, and stale-state detection.
- **Exact File:** `backend/app/services/authorization.py` (lines 238-249).
- **Current Behavior:** The `ConsentService` integration inside `AuthorizationService._dispatch()` is explicitly commented out under `# DO NOT ACTIVATE YET`.
- **Expected Behavior:** Consent evaluation MUST execute for all protected patient resources if base authorization passes.
- **Severity:** CRITICAL

## 2. Consent State Lifecycle & Transitions
- **Current Implementation:** `ConsentStatus` enum exists in `models/consent.py` containing DRAFT, ACTIVE, SUSPENDED, REVOKED, EXPIRED, SUPERSEDED, CANCELLED.
- **Exact File:** N/A (Missing `api/consent.py`).
- **Current Behavior:** There is no centralized mechanism to transition consent states. Consent cannot be transitioned or revoked.
- **Expected Behavior:** Centralized transition mechanism enforcing valid state transitions (e.g., ACTIVE -> REVOKED) and writing to `ConsentState` history.
- **Severity:** HIGH

## 3. Enforcement-State Verification
- **Current Implementation:** `ConsentService.evaluate()` expects `enforcement_state_id`. 
- **Exact File:** `backend/app/services/consent.py` (line 64).
- **Current Behavior:** Because ConsentService is commented out, stale-state enforcement is bypassed.
- **Expected Behavior:** Compare `authoritative_state.id` against `enforcement_state_id`. Fail closed if they do not match (`ENFORCEMENT_STATE_STALE`).
- **Severity:** CRITICAL

## 4. Purpose Validation
- **Current Implementation:** `websockets.py` (line 103) and `interoperability.py` (line 39) hardcode `purpose="TREATMENT"`.
- **Current Behavior:** Purpose is bypassed in CAE due to ConsentService being disabled, and hardcoded in critical routes to pass basic tests.
- **Expected Behavior:** Purpose must be dynamically supplied by the requester's context and validated against the Consent Policy's `allowed_purposes`.
- **Severity:** HIGH

## 5. Local Storage Fallback
- **Current Implementation:** `backend/app/services/storage.py` (line 9).
- **Current Behavior:** If Supabase keys are missing, it falls back to local file storage.
- **Expected Behavior:** Production should FAIL CLOSED if secure object storage is not configured. Local storage fallback is a path traversal and data exposure risk.
- **Severity:** CRITICAL

## 6. WebSocket Security Context Drift
- **Current Implementation:** `backend/app/api/websockets.py` dynamically evaluates authorization per-message via `_evaluate_message_authorization()`.
- **Current Behavior:** It correctly evaluates per-message, but since ConsentService is disabled, it will not detect revoked consent. Additionally, it hardcodes `purpose="TREATMENT"`.
- **Expected Behavior:** Must evaluate current consent and use accurate purpose context.
- **Severity:** HIGH
