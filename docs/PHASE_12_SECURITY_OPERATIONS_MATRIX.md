# Phase 12 Security Operations Matrix

| Control | Implementation | Verification | Evidence | Owner | Status | Remaining Risk |
|---|---|---|---|---|---|---|
| Rate Limiting | `slowapi` on login/upload | `test_rate_limiting.py` | CI Test Logs | Platform Eng | VERIFIED | Distributed attacks may overwhelm memory limits. |
| Edge WAF | Render Cloudflare Edge | N/A | `WAF_CONFIGURATION.md` | Infrastructure | DEPLOYMENT DEPENDENCY | Requires manual configuration in Cloudflare/Render. |
| Malware Scanning | Quarantine State (`scan_status`) | `test_malware_quarantine.py` | API Code | Security | IMPLEMENTED | Actual background scanner worker is mocked. |
| Production Secrets | `config.py` strict enforcement | Manual code review | App crashes if missing | Platform Eng | VERIFIED | Keys must be securely transferred to the PaaS. |
| Database Hardening | `pool_size`, `max_overflow`, `pool_pre_ping` | `database.py` review | Configured in codebase | Platform Eng | IMPLEMENTED | Pooler drops may still occur under extreme load. |
| Storage Privacy | Supabase Bucket configuration | Manual review | Buckets are private | Platform Eng | IMPLEMENTED | Relying on Supabase IAM for boundary enforcement. |
| Backups | Supabase PITR | N/A | `BACKUP_VERIFICATION.md` | Infrastructure | UNVERIFIED | A staging restore drill has not been executed. |
| CI/CD Security | GitHub Actions Secrets | `ci.yml` review | Workflow definition | Platform Eng | VERIFIED | None. |
| Observability | Structured JSON Logging | Phase 10 | `logging.py` | Platform Eng | VERIFIED | No centralized dashboard (e.g., Datadog) exists yet. |
