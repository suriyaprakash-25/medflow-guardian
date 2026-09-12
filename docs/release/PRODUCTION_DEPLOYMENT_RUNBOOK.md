# PRODUCTION DEPLOYMENT RUNBOOK

## Pre-Deployment
- Release approval obtained.
- Backup verified via Supabase dashboard.
- Secrets verification (ensure `SUPABASE_SERVICE_ROLE_KEY` is loaded and secure).
- Environment verification.

## Deployment
1. Deploy Backend API.
2. Run Database Migrations (`alembic upgrade head`).
3. Verify Health/Readiness (`/health`, `/ready`).
4. Deploy Frontend applications (Vite build to CDN).
5. Verify API connectivity and authentication.
6. Verify critical clinical path.

## Post-Deployment
- Run smoke tests.
- Monitor 401, 403, and 500 error rates.
- Verify audit event generation.
