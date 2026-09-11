# MedFlow Guardian Production Gap Matrix

| Area | Required | Current | Status | Risk | Evidence |
|------|----------|---------|--------|------|----------|
| **Consent Architecture** | Versioned Consent Policies & States | None | MISSING | P0 | Missing `Consent` entities in SQLAlchemy |
| **Enforcement State** | Verification of Auth vs Enforcement State | None | MISSING | P0 | Direct `DocumentAccessGrant` usage with no generic state verification |
| **Authentication** | Secure Auth / OIDC | Local JWT | PARTIAL | P1 | Hardcoded local JWT without invalidation/refresh tokens |
| **Authorization** | Contextual Policy Evaluation | Simple RBAC | PARTIAL | P1 | Hardcoded role and `hospital_id` checks |
| **Document Security** | Protected Signed URLs with immediate revocation | Signed URLs | PARTIAL | P1 | Signed URLs remain valid until expiration even if consent revokes |
| **Audit Logging** | Immutable, fully contextual logging | Basic logging | PARTIAL | P2 | Missing consent and authorization evaluation contexts |
| **WebSockets** | Isolated Subscription Auth | Initial Token validation | PARTIAL | P2 | Lacks dynamic subscription validation |
| **Deployment** | CI/CD, Containerization | Local execution | MISSING | P2 | No Dockerfiles or deployment configs present |
| **Testing** | Security/E2E Coverage | Basic unit/E2E scripts | PARTIAL | P2 | Pytest exists and runs, but missing state divergence cases |
