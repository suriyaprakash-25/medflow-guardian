# Production Migration Runbook

**Last verified:** 2026-09-13

## 1. Pre-Check
1. Verify CI/CD tests have passed on the `main` branch.
2. Verify Alembic heads: `alembic heads`. There should only be one head.
3. Announce the maintenance window to the clinical team if the migration involves locking large tables.

## 2. Backup
1. In the Supabase Dashboard, open **Database > Backups** and confirm that the
   project's scheduled backup or Point-in-Time Recovery (PITR) coverage is
   healthy for the intended recovery point.
2. Record the latest recoverable time, project reference, release commit, and
   migration revision in the release evidence. Do not begin a destructive
   migration without a recovery point that meets the release recovery
   objective.
3. For an independent logical copy, use the supported Supabase CLI dump and
   restore workflow and test the dump in an isolated project or database before
   deployment. Never test a restore over the production database.
4. Back up Supabase Storage objects separately. Database backups contain Storage
   metadata but do not contain the stored files themselves.

## 3. Execution
1. Migrations are executed automatically via the Render deployment script (`alembic upgrade head`).
2. Monitor the Render deployment logs. If the migration fails, Render will automatically cancel the deployment and retain the previous healthy container.

## 4. Verification
1. Hit the `/health` and `/ready` endpoints.
2. Perform a "golden workflow" test: upload a document, grant consent, download the document.
3. Confirm the deployed Alembic revision matches `alembic heads` and retain the
   CI backup/restore rehearsal result with the release evidence.

## 5. Rollback
If a migration introduces critical logical errors:
1. Revert the commit in GitHub.
2. If the migration was purely additive (e.g., adding a table), the older application code will simply ignore it.
3. If the migration was destructive (e.g., dropping a column), you MUST restore
   the Supabase database to the recovery point verified in Step 2. *Do not rely
   on `alembic downgrade` for destructive operations in production.*

## 6. Automated Recovery Rehearsal

The backend CI job creates a PostgreSQL custom-format dump after all migrations,
restores it into a new empty database, runs `alembic check`, and reruns the P0
database-integrity tests against the restored copy. This proves that the schema,
Alembic revision, RLS posture, constraints, and grants survive a logical
backup/restore cycle. It does not replace a scheduled Supabase project restore
drill or a separate Storage-object recovery test.
