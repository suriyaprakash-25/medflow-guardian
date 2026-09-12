# ROLLBACK RUNBOOK

## Application Rollback
- Revert the Git commit to the previous stable release.
- Re-run the CI/CD pipeline to deploy the previous backend image.

## Database Rollback
- Note: Migrations involving destructive changes cannot always be trivially reversed.
- Prefer backward-compatible migrations.
- Before deployment, confirm the recovery window and record the intended recovery point in the release evidence.
- If data corruption occurs, stop writes and initiate the documented Supabase backup or Point-In-Time Recovery (PITR) process to the point immediately before the migration.
- Treat Storage-object recovery as a separate procedure: database recovery restores Storage metadata, not the underlying files.
- Re-run health checks, the golden consent workflow, and database-integrity checks after recovery before reopening traffic.

## Frontend Rollback
- Re-deploy previous CDN assets.
