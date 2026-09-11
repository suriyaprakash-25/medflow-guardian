# ROLLBACK RUNBOOK

## Application Rollback
- Revert the Git commit to the previous stable release.
- Re-run the CI/CD pipeline to deploy the previous backend image.

## Database Rollback
- Note: Migrations involving destructive changes cannot always be trivially reversed.
- Prefer backward-compatible migrations.
- If data corruption occurs, initiate a Point-In-Time Recovery (PITR) via Supabase to the minute before the migration.

## Frontend Rollback
- Re-deploy previous CDN assets.
