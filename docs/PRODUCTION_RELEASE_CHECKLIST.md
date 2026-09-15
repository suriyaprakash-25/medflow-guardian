# MedFlow Guardian Production Release Checklist

Use this checklist during every production promotion from `dev` to `main`.

### Pre-release
- [ ] Record exact `dev` SHA: ________
- [ ] GitHub CI checks pass (Backend Tests, Frontend Builds, security-gates).
- [ ] FHIR Validator green.
- [ ] No high-severity vulnerabilities in `npm audit` or `pip-audit`.
- [ ] Migration rehearsal is green (`alembic downgrade`, `upgrade head`, `check`).
- [ ] Backup/Restore rehearsal is green.

### Infrastructure
- [ ] Supabase project active and responsive.
- [ ] Supabase storage bucket `medical-documents` exists and is private.
- [ ] Render Blueprint is synchronized.
- [ ] Production secrets are configured securely in Render (No `.env` files in source).
- [ ] `medflow-clamav-prod` is healthy.
- [ ] `medflow-malware-worker-prod` is healthy.
- [ ] Retention cron is scheduled properly.

### Release
- [ ] Validated `dev` SHA matches the SHA being promoted to `main`.
- [ ] Merge `dev` into `main`.
- [ ] Render auto-deploy succeeds for all 6 services.
- [ ] Alembic migrations run successfully during Render pre-deploy.
- [ ] Backend API `/ready` endpoint returns HTTP 200.
- [ ] Frontends load successfully with correct security headers (CSP, HSTS).

### Production validation
- [ ] Run **Production release validation** GitHub Action (`production-validation.yml`).
- [ ] Verify OWASP ZAP baseline is clean.
- [ ] Verify Patient and Doctor login via synthetic/demo accounts.
- [ ] Verify cross-tenant authorization correctly returns 403 (e.g. Doctor requesting unauthorized document).
- [ ] Verify consent lifecycle: Grant access -> Revoke access.
- [ ] Verify FHIR Interoperability endpoints.
- [ ] Verify Malware scan lifecycle (upload a test safe file and verify it's marked clean).
- [ ] Verify session/WebSocket revocation behaves as expected.
- [ ] Review Audit Logs for correct capture of activities.

### Post-release
- [ ] Tag the deployed SHA in GitHub (e.g., `v1.9.0`).
- [ ] Archive security/ZAP evidence from GitHub Actions.
- [ ] Confirm observability dashboard (or `/internal/metrics`) is populated.
- [ ] Ensure no unexplained HTTP 5xx spikes post-deployment.
- [ ] Confirm rollback plan (Application revert SHA) is ready if needed.
