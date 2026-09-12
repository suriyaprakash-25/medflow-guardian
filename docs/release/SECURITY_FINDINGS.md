# SECURITY FINDINGS

| Finding ID | Severity | Component | Description | Remediation | Status |
|------------|----------|-----------|-------------|-------------|--------|
| MED-01 | CRITICAL | Auth | 7-day bearer token vulnerability | Migrated to short-lived access and HTTP-only refresh tokens | CLOSED |
| MED-02 | HIGH | IDOR | Cross-org doctor access | CAE enforced | CLOSED |
| MED-03 | MEDIUM | Uploads | Document uploads rely on extension/MIME | Implement ICAP AV scanning pipeline | DEFERRED |
