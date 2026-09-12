# PHASE 4 — CENTRAL AUTHORIZATION ENGINE

## 1. Purpose

Phase 4 implements the **Central Authorization Engine (CAE)** for MedFlow Guardian.

The CAE answers a single, well-defined question:

> **"Is this authenticated actor permitted to perform this operation on this resource in this organization/context?"**

It does NOT answer consent questions (Phase 5).

---

## 2. Authorization Architecture

```
Request
   │
   ▼
Authentication (JWT / OAuth2)
   │
   ▼
Authenticated Actor (User from DB)
   │
   ▼
Active User Check (is_active)
   │
   ▼
Identity Classification (patient / doctor / admin)
   │
   ▼
Organization Membership (HospitalStaff)
   │
   ▼
Organization Context (hospital_id verified server-side)
   │
   ▼
┌──────────────────────────────────┐
│  CENTRAL AUTHORIZATION ENGINE    │
│  app/services/authorization.py   │
│                                  │
│  authorize(AuthorizationContext) │
│  → AuthorizationDecision         │
└──────────────┬───────────────────┘
               │
         ALLOW / DENY
               │
     ┌─────────┴──────────┐
     ▼                    ▼
Protected Operation   403 / 404
```

---

## 3. Authentication vs Authorization

| Concern | Question | Implementation |
|---------|----------|---------------|
| Authentication | Who are you? | JWT decode, DB lookup (`get_current_user`) |
| Authorization | Can you do this? | `AuthorizationService.authorize()` |
| Consent | Does the patient permit this? | **Phase 5 — NOT YET IMPLEMENTED** |

These three concepts are strictly separated.

---

## 4. Identity Context

Identity is resolved from the JWT token + database, never from client-supplied payload fields.

```python
# NEVER trust:
request.body.user_id
request.body.role
request.body.patient_id

# ALWAYS resolve from:
get_current_user(token)   # → User from DB
get_patient_identity()     # → requires role == "patient"
get_practitioner_identity() # → requires role == "doctor"
```

---

## 5. Organization Context

Organization membership is validated server-side via `HospitalStaff`:

```python
def _get_active_membership(self, user_id: int, hospital_id: int) -> Optional[HospitalStaff]:
    return self._db.query(HospitalStaff).filter(
        HospitalStaff.user_id == user_id,
        HospitalStaff.hospital_id == hospital_id,
        HospitalStaff.is_active == True
    ).first()
```

Client-supplied `hospital_id` values are used only as lookup keys — the membership record in PostgreSQL is the authoritative truth.

---

## 6. Membership Model

```
User ──────── HospitalStaff ──────── Hospital
               (user_id, hospital_id)
               role: "doctor" | "admin" | "staff"
               is_active: bool
               UniqueConstraint(user_id, hospital_id)
```

- A user may belong to **multiple hospitals** (multi-org support).
- Membership in Hospital A **does not authorize** Hospital B operations.
- Inactive memberships (`is_active=False`) are denied.

---

## 7. Role Model

Roles are evaluated as **one input** to authorization, not the complete model.

| Role | System Meaning | NOT sufficient for |
|------|---------------|-------------------|
| `patient` | Patient identity | Access to any patient data |
| `doctor` | Practitioner identity | Access to any medical record |

Role alone NEVER grants access. The engine also checks:
- Organization membership
- Resource ownership
- Visit/relationship context

---

## 8. AuthorizationContext

```python
@dataclass
class AuthorizationContext:
    actor: User               # From authenticated session
    operation: Operation      # Centralized vocabulary
    resource_type: ResourceType  # Centralized vocabulary
    db: Session               # For relationship lookups

    resource: Optional[Any]   # Target resource object (None = list ops)
    hospital_id: Optional[int]  # Organization scope
    patient_id: Optional[int]   # Patient subject (cross-role ops)
    relationship_context: Optional[Any]  # e.g., active grant, visit
```

**Phase 5 Extension Points** (present in code, NOT activated):
```python
# purpose: Optional[str]
# consent_state_id: Optional[str]
# policy_version: Optional[str]
# enforcement_state: Optional[str]
```

---

## 9. AuthorizationDecision

```python
@dataclass
class AuthorizationDecision:
    allowed: bool
    reason: Optional[DenialReason]
    detail: str
```

Every denial carries a typed `DenialReason` for auditability.

---

## 10. Operations

```python
class Operation(str, enum.Enum):
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    DOWNLOAD = "download"
    REQUEST_ACCESS = "request_access"
    GRANT_ACCESS = "grant_access"
    REVOKE_ACCESS = "revoke_access"
    LIST = "list"
    MARK_READ = "mark_read"
    UPDATE_STATUS = "update_status"
```

---

## 11. Resource Types

```python
class ResourceType(str, enum.Enum):
    DOCUMENT = "document"
    ACCESS_REQUEST = "access_request"
    ACCESS_GRANT = "access_grant"
    TRIAGE_REQUEST = "triage_request"
    VISIT = "visit"
    NOTIFICATION = "notification"
    AUDIT_LOG = "audit_log"
    PATIENT_READING = "patient_reading"
    MESSAGE = "message"
    HOSPITAL = "hospital"
    PRACTITIONER_PROFILE = "practitioner_profile"
    PATIENT_PROFILE = "patient_profile"
```

---

## 12. Default-Deny Behavior

```python
def authorize(self, ctx: AuthorizationContext) -> AuthorizationDecision:
    if ctx.actor is None:
        return AuthorizationDecision.deny(DenialReason.AUTHENTICATION_REQUIRED)
    if not ctx.actor.is_active:
        return AuthorizationDecision.deny(DenialReason.USER_INACTIVE)
    try:
        result = self._dispatch(ctx)
    except Exception:
        return AuthorizationDecision.default_deny()  # Fail closed
    return result

def _dispatch(self, ctx):
    # If no rule matches:
    return AuthorizationDecision.default_deny()
```

**Any exception → DENY. Unknown resource type → DENY. Unknown operation → DENY.**

---

## 13. Organization Isolation

| Scenario | Result |
|----------|--------|
| Doctor in Hospital A uploads to Hospital B visit | DENY (MEMBERSHIP_REQUIRED) |
| Doctor in Hospital A views Hospital B triage | DENY (MEMBERSHIP_REQUIRED) |
| Doctor with inactive membership | DENY (MEMBERSHIP_REQUIRED) |
| Patient A downloads Patient B document | DENY (RESOURCE_NOT_OWNED) |

---

## 14. Patient Ownership

Patient resources are scoped by authenticated `user.id`:
- Documents: `doc.patient_id == actor.id`
- Notifications: `notification.user_id == actor.id`
- Triage requests: `triage.patient_id == actor.id`
- Access requests: `request.patient_id == actor.id`
- Access grants: `grant.patient_id == actor.id`

Client-supplied `patient_id` values in URLs/bodies are used only as lookup keys, then verified against resource ownership.

---

## 15. Practitioner Relationships

For cross-role operations (doctor accessing patient data), the CAE checks for legitimate Visit relationships:

```python
def _has_visit_relationship(self, patient_id: int, doctor_id: int) -> bool:
    return self._db.query(Visit).filter(
        Visit.patient_id == patient_id,
        Visit.doctor_id == doctor_id
    ).first() is not None
```

This preserves the existing access-request/grant workflow architecture.

---

## 16. Document Authorization

```
UPLOAD:   actor.role == "doctor" AND active membership in visit's hospital
DOWNLOAD: patient → must own document
          doctor  → membership in doc's hospital OR uploader OR active grant
READ metadata: doctor → visit relationship with patient required
LIST:     patient → own documents only
```

Authorization occurs **before** `StorageService` is invoked.

---

## 17. Access Request Authorization

| Operation | Actor | Requirements |
|-----------|-------|-------------|
| `REQUEST_ACCESS` | Doctor | Active membership in requested hospital |
| `GRANT_ACCESS` (approve) | Patient | Own the access request, status == pending |
| `DELETE` (reject) | Patient | Own the access request, status == pending |
| `LIST` | Doctor/Patient | Own scope enforced by DB query |

---

## 18. Access Grant Authorization

| Operation | Actor | Requirements |
|-----------|-------|-------------|
| `REVOKE_ACCESS` | Patient | Own the grant, status == active |
| `LIST` | Doctor/Patient | Own scope enforced by DB query |

---

## 19. Triage Authorization

| Operation | Actor | Requirements |
|-----------|-------|-------------|
| `CREATE` | Patient | Authenticated patient |
| `LIST` | Doctor | Active membership scopes list |
| `UPDATE_STATUS` | Doctor | Active membership in triage's hospital |

---

## 20. Visit Authorization

| Operation | Actor | Requirements |
|-----------|-------|-------------|
| `LIST` | Patient/Doctor | Own scope |
| `READ` | Patient | Own visit |
| `READ` | Doctor | Membership in visit's hospital OR assigned |

---

## 21. Notification Authorization

Notifications are strictly owner-scoped. The `notification.user_id` must match `actor.id`. Violation returns **404** (not 403) to prevent notification enumeration.

---

## 22. WebSocket Authorization

WebSocket connections are authenticated via JWT token in query parameter. The handler:
1. Validates token
2. Loads user from DB
3. Checks `is_active`
4. Verifies hospital membership before accepting subscription

---

## 23. Error Semantics

| HTTP Code | When |
|-----------|------|
| `401` | No token, invalid token, expired token, inactive user |
| `403` | Authenticated but unauthorized |
| `404` | Resource not found OR existence hidden from unauthorized actors |

**Never `500` for authorization failures.**

---

## 24. IDOR Protection

Every sensitive resource ID in the URL or body is:
1. Loaded from the database by ID
2. Verified for ownership/membership/relationship
3. Hidden via 404 when appropriate (documents, notifications)

Tested explicitly via IDOR attack matrix in `tests/test_authorization_endpoints.py`.

---

## 25. Test Strategy

### Unit Tests (`test_authorization_engine.py`)
- 37 tests against `AuthorizationService` directly using `MockDB`
- No Supabase connection required
- Tests: DEFAULT DENY, all resource types, all roles, ownership, org isolation

### E2E Tests (`test_authorization_endpoints.py`)
- Real HTTP endpoints against real PostgreSQL (Supabase)
- Tests: IDOR, cross-org access, role escalation, legitimate flows
- Does NOT mock the authorization service

### Existing Tests
- `test_identity.py` — `/api/auth/me` endpoint
- `test_organization_isolation.py` — cross-org access request denial

---

## 26. Performance Considerations

- No authorization caching introduced (healthcare state changes dynamically)
- One additional DB query per request for membership checks (acceptable for correctness)
- `_has_visit_relationship` uses indexed FK columns
- Single `AuthorizationService` instance per request (FastAPI dependency scope)

---

## 27. Audit Compatibility

Authorization decisions are structured to support future audit expansion:

```python
# Future Phase 5 audit record structure (conceptual):
{
    "actor_id": ctx.actor.id,
    "actor_role": ctx.actor.role,
    "organization_id": ctx.hospital_id,
    "resource_type": ctx.resource_type,
    "operation": ctx.operation,
    "decision": "ALLOW" | "DENY",
    "denial_reason": decision.reason,
    # Phase 5:
    "purpose": ...,
    "consent_state_id": ...,
    "policy_version": ...,
    "enforcement_state": ...,
}
```

---

## 28. Phase 5 Extension Points

Phase 5 (Consent/Policy/Enforcement) will extend `AuthorizationContext` with:

```python
# NOT YET ACTIVATED — Phase 5 only
purpose: Optional[str]
consent_state_id: Optional[str]
policy_version: Optional[str]
enforcement_state: Optional[str]
```

The engine's dispatch architecture allows adding consent evaluation without rewriting existing rules:

```python
# Phase 5 flow (conceptual)
def authorize(self, ctx):
    base_decision = self._dispatch(ctx)
    if not base_decision.allowed:
        return base_decision
    # Phase 5: add consent evaluation here
    consent_decision = self._evaluate_consent(ctx)
    return consent_decision
```

---

## 29. Known Limitations

1. **WebSocket channel isolation** — Organization-scoped WebSocket subscriptions are enforced at connection time but not per-message. Phase 5 should add per-message authorization.
2. **Visit relationship as proxy for clinical relationship** — The current data model uses `Visit` as the authoritative patient-doctor relationship. More granular care-team relationships are a Phase 5 concern.
3. **Audit logs not yet immutable** — AuditLog records can be deleted via DB admin. Phase 5 should add append-only enforcement.
4. **Document metadata exposure** — `GET /documents/metadata/{patient_id}` returns all document metadata for a patient if any visit relationship exists. Fine-grained document-level metadata permissions are deferred to Phase 5.

---

## 30. Explicitly Deferred Features (Phase 5)

- Consent model (`ConsentPolicy`, `ConsentState`, `ConsentStateId`)
- Purpose-based access rules
- Enforcement State verification
- Dynamic consent revocation
- Policy version evaluation
- FHIR Consent interoperability
- Complete OIDC migration
- Per-message WebSocket authorization
- Immutable audit log
- OPA / Cedar / Casbin (not required)
- Redis authorization cache (not required at this scale)

---

## Files Changed in Phase 4

| File | Change |
|------|--------|
| `app/services/authorization.py` | **NEW** — Central Authorization Engine |
| `app/api/dependencies.py` | Added `get_authorization_service()`, `require_authorization()` |
| `app/api/audit.py` | CAE integrated — replaced scattered role checks |
| `app/api/monitoring.py` | CAE integrated — replaced scattered role checks in messages/readings |
| `app/api/document.py` | CAE integrated — upload and download authorization |
| `app/api/triage.py` | CAE integrated — `update_status` organization check |
| `tests/test_authorization_engine.py` | **NEW** — 37 unit tests |
| `tests/test_authorization_endpoints.py` | **NEW** — E2E endpoint security tests |
| `conftest.py` | Removed `autouse=True` to allow pure unit tests without DB |
