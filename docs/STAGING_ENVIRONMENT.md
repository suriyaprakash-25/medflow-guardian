# Staging Environment Architecture

**Date:** 2026-09-11

## Objective
To provide a secure, isolated deployment environment that mirrors production exactly, used for security validation and penetration testing before releasing Phase 13.

## Environment Separation Constraints
1. **Isolated Database**: The staging backend MUST connect to a physically isolated Supabase project (e.g., `medflow-staging`). It cannot share a database cluster with production.
2. **Isolated Storage**: Staging MUST use staging storage buckets.
3. **Isolated Secrets**: Staging MUST have its own set of `SUPABASE_SERVICE_ROLE_KEY`, `SECRET_KEY`, and `ENCRYPTION_KEY`.
4. **Isolated Frontends**: The Vite applications must be deployed to separate URLs (e.g., `patient.staging.medflow.com`) pointing to the staging backend API.

## Data Constraints
- **NO REAL PHI**: The staging environment must never be populated with actual Patient Health Information. 
- All data in staging must be synthetic or heavily anonymized.

## Deployment Target
As defined in `render.yaml`, Staging will be a parallel deployment on Render, configured exactly like production but mapped to the `medflow-staging` Supabase backend.
