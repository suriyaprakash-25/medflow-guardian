# STAGING RUNBOOK

## Objective
Deploy and verify the MedFlow Guardian application in the staging environment.

## Steps
1. Push to `staging` branch to trigger GitHub Actions.
2. Monitor build process for backend, patient-app, and doctor-portal.
3. Validate staging database migration.
4. Verify environment secrets (isolated from production).
5. Run smoke tests and integration tests.
6. Check edge/WAF logs for anomalies.
