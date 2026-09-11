# Production Migration Runbook

**Date:** 2026-09-11

## 1. Pre-Check
1. Verify CI/CD tests have passed on the `main` branch.
2. Verify Alembic heads: `alembic heads`. There should only be one head.
3. Announce the maintenance window to the clinical team if the migration involves locking large tables.

## 2. Backup
1. Access the Supabase Dashboard.
2. Navigate to Database > Backups.
3. Trigger a manual Point-in-Time (PITR) backup snapshot. Wait for completion.

## 3. Execution
1. Migrations are executed automatically via the Render deployment script (`alembic upgrade head`).
2. Monitor the Render deployment logs. If the migration fails, Render will automatically cancel the deployment and retain the previous healthy container.

## 4. Verification
1. Hit the `/health` and `/ready` endpoints.
2. Perform a "golden workflow" test: upload a document, grant consent, download the document.

## 5. Rollback
If a migration introduces critical logical errors:
1. Revert the commit in GitHub.
2. If the migration was purely additive (e.g., adding a table), the older application code will simply ignore it.
3. If the migration was destructive (e.g., dropping a column), you MUST restore the Supabase database from the PITR snapshot taken in Step 2. *Do not rely on `alembic downgrade` for destructive operations in production.*
