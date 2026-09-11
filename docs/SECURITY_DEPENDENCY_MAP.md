# Security Decision Dependency Map

**Date:** 2026-09-11

This document maps the flow of a security decision in MedFlow Guardian and defines the fail-closed behavior for each dependency.

## The Security Chain

```text
Incoming Request -> WAF -> Rate Limiter -> FastAPI Router
       ↓
1. Authentication (JWT / Session)
       ↓
2. Identity (Actor Resolution)
       ↓
3. Organization Isolation (Membership Check)
       ↓
4. Central Authorization Engine (CAE)
       ↓
5. Consent Engine (Policy Evaluation)
       ↓
6. Enforcement State Verification
       ↓
7. Malware/Quarantine State Check
       ↓
8. Protected Resource Access (Storage/DB)
       ↓
9. Audit Logging
```

## Failure Behaviors

1. **Authentication Fails**: (e.g., token expired, invalid signature). **Action**: Return `401 Unauthorized`.
2. **Database Unavailable**: **Action**: Return `503 Service Unavailable`. Do NOT use stale local cache for authorization.
3. **CAE Fails/Errors**: **Action**: Return `403 Forbidden`. Fail closed.
4. **Consent Engine Unavailable**: **Action**: Return `403 Forbidden`. If we cannot compute consent, we cannot grant access.
5. **Enforcement State Mismatch**: (e.g., state ID provided does not match the current database state). **Action**: Return `403 Forbidden`.
6. **Malware Quarantine `pending`**: **Action**: Return `403 Forbidden`. The file cannot be released until marked `clean`.
7. **Storage Service Unavailable**: **Action**: Return `503 Service Unavailable`.
8. **Audit Logging Fails**: **Action**: Proceed or Fail? *Decision*: If the database is completely down, the request will fail anyway. If only the audit table insert fails, the transaction rolls back, meaning the entire operation fails. **Fail closed.**
