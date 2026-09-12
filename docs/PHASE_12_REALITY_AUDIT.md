# Phase 12 Reality Audit

## 1. Environment & Architecture
- **Backend Framework:** FastAPI, Uvicorn, Python 3.11
- **Database:** Supabase PostgreSQL (Production), SQLAlchemy, Alembic
- **Storage:** Supabase Storage
- **Frontends:** React 18, Vite (patient-app, doctor-portal, admin-portal)
- **Rate Limiting:** MISSING. Not implemented at API or WAF layer.
- **WAF / Edge:** MISSING. No cloud edge proxy (like Cloudflare, AWS WAF, etc.) is currently defined in code or docs.

## 2. Dependencies (Phase 11 Review)
- **Short-lived access tokens:** VERIFIED. Set to 15 minutes in `app.core.config`.
- **Refresh-token architecture:** VERIFIED. Rotating `HttpOnly` refresh cookie implemented in Phase 11.
- **MFA:** VERIFIED. Integrated via PyOTP and enforced for `admin`/`doctor` roles via pre-auth tokens.
- **Session Revocation:** VERIFIED. Implemented via the `sessions` tracking table.

## 3. Secret Management
- **Service Role Key:** STORED IN ENV. `SUPABASE_SERVICE_ROLE_KEY` is loaded from the environment in `config.py` and strictly used in the backend. 
- **Frontend Keys:** VERIFIED CLEAN. Frontends do not contain backend secrets. They only use `VITE_API_BASE_URL`.
- **External Secret Manager:** MISSING. Secrets currently rely entirely on standard environment variables (and `.env` files locally).
- **JWT Secret:** IMPLEMENTED BUT UNVERIFIED in production (relies on deployment setting `SECRET_KEY`).

## 4. Abuse & Rate Limits
- **Rate Limiting:** MISSING.
- **Malware Scanning:** MISSING. `app/api/document.py` performs MIME validation and a 10MB size limit check, but no anti-virus or malware quarantine boundary exists.

## 5. CI/CD & Deployment
- **Workflows:** `ci.yml` exists. Runs tests on PRs to main. 
- **Deployment Files:** MISSING. No `Dockerfile`, `docker-compose.yml`, or specific PaaS manifest (like `render.yaml` or AWS SAM) exists to define the production target.
- **Staging Readiness:** MISSING. No staging environment separated from production.

## 6. Observability & Logging
- **Structured JSON Logging:** VERIFIED. Phase 10 introduced structured JSON logs in `app/core/logging.py`.
- **Metrics/Alerts:** MISSING. No Prometheus endpoints, Datadog integration, or alerting rules defined.
- **Health Checks:** PARTIALLY IMPLEMENTED. `/health` exists but only returns `{"status": "ok"}`. It does not check database connectivity.

## 7. Storage Security
- **Privacy:** VERIFIED. Supabase Storage buckets are private; accessed via Service Role keys on the backend and streamed to clients after authorization.
- **Accidental Deletion/Backup:** UNVERIFIED. Relying on Supabase platform defaults.

## 8. Database Security
- **Connection Pool:** PARTIALLY IMPLEMENTED. SQLAlchemy configured with basic connection pooling, but Phase 10 noted Supabase pooler instability.
- **Network Isolation:** UNVERIFIED. Supabase DB is accessible over public internet with a password; IP allowlisting is an unverified cloud configuration.
- **Migration Pipeline:** IMPLEMENTED. Alembic is functional, but there is no automated rollback runbook.

## Conclusion
The application logic is strongly secured, but the *infrastructure wrapper* is non-existent. A deployment target must be chosen, WAF configured, health checks improved, rate limiting added, and malware scanning designed.
