# MedFlow Guardian Production Deployment Runbook

This document details the exact steps and configurations required to provision, deploy, and verify MedFlow Guardian in a production environment.

## 1. Prerequisites
- GitHub Repository with `main` branch configured as the default and protected branch.
- Supabase account with a provisioned project (PostgreSQL + Storage).
- Render account for hosting backend APIs, frontends, and background workers.
- Optional: Configured Identity Providers (Auth0, Okta, Entra) for OIDC.

## 2. GitHub Branch Model & Protection
MedFlow Guardian follows a strict `dev -> main` promotion model.

**GitHub Manual Configuration Steps:**
1. Navigate to your repository **Settings > Default branch** and ensure it is set to `main`.
2. Navigate to **Settings > Branches** and add a branch protection rule for `main`.
3. Check the following:
   - **Require a pull request before merging**
   - **Require status checks to pass before merging** (select all CI/CD workflows: security gates, FHIR tests, Backend/Frontend tests).
   - **Require branches to be up to date before merging**
   - **Do not allow bypassing the above settings**

## 3. Supabase Project & PostgreSQL Setup
1. Create a new Supabase Project.
2. Note the **Project URL** and the **Service Role Key** (found in Project Settings > API).
3. Under Database Settings, retrieve the **Connection string (URI)**.
4. **Storage Bucket**: Navigate to Storage and create a private bucket exactly named: `medical-documents`.
   - *Ensure the bucket is private. Do not enable public access.*

## 4. Environment Variables
You must set the following environment variables in the Render Dashboard for `medflow-backend-prod`:

| Variable | Type | Source | Required? |
|----------|------|--------|-----------|
| `ENV` | Env Var | Set to `production` | Yes |
| `DATABASE_URL` | Secret | Supabase Database Settings | Yes |
| `SUPABASE_URL` | Secret | Supabase API Settings | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Secret | Supabase API Settings | Yes |
| `SUPABASE_STORAGE_BUCKET` | Env Var | Set to `medical-documents` | Yes |
| `SECRET_KEY` | Secret | Render Generate / Custom | Yes |
| `ENCRYPTION_KEY` | Secret | Custom (See Key Generation) | Yes |
| `TRUSTED_PROXY_CIDRS` | Secret | Cloudflare / Proxy IPs | Yes (if behind proxy) |
| `FRONTEND_CORS_ORIGINS` | Secret | Frontend origins (HTTPS) | Yes |
| `OBSERVABILITY_TOKEN` | Secret | Custom >= 32 chars | Yes |

*Do NOT store these secrets in GitHub Actions or any source-controlled file.*

## 5. Cryptographic Key Generation
The `ENCRYPTION_KEY` must be a valid Fernet key. Generate it safely offline using:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Place the output in the Render `ENCRYPTION_KEY` secret.

## 6. Render Blueprint Setup
The infrastructure is fully defined in `render.yaml`.
1. Go to the Render Dashboard > Blueprints > New Blueprint Instance.
2. Connect the MedFlow Guardian repository.
3. Render will detect the 6 services: Backend API, ClamAV service, Malware worker, Retention cron, Patient App, Doctor Portal, and Admin Portal.
4. Ensure Render deploys from the `main` branch.
5. In Render, fill in the required Secrets as prompted by the Blueprint variables (which map to `sync: false`).

## 7. Custom Domains & CORS
Once custom domains are added in Render:
- **Patient App**: `https://app.example.com`
- **Doctor Portal**: `https://doctor.example.com`
- **Admin Portal**: `https://admin.example.com`
- **API**: `https://api.example.com`

Update the `FRONTEND_CORS_ORIGINS` secret in the Render backend service to:
`https://app.example.com,https://doctor.example.com,https://admin.example.com`

## 8. GitHub Production Environment
1. In GitHub, go to **Settings > Environments > New environment** and name it `production`.
2. Add Deployment branches rule: Selected branches -> `main`.
3. Add Environment variables:
   - `PRODUCTION_API_URL`: `https://api.example.com`
   - `PATIENT_APP_URL`: `https://app.example.com`
   - `DOCTOR_PORTAL_URL`: `https://doctor.example.com`
   - `ADMIN_PORTAL_URL`: `https://admin.example.com`
4. Add Environment Secret:
   - `OBSERVABILITY_TOKEN`: The same 32+ character token configured in Render.

## 9. Rollback & Disaster Recovery
### Application Rollback
If a deployment to `main` fails or exhibits issues:
1. Identify the previous working commit SHA on `main`.
2. In GitHub, revert the faulty commit or hard reset and force push (if allowed by admins).
3. Render will auto-deploy the corrected `main` branch.

### Database Rollback
**Never blindly downgrade Alembic in production.**
- Small non-destructive migrations: Use `alembic downgrade <revision>`.
- Destructive migrations / Data loss: Restore the Supabase database using Supabase Point-in-Time Recovery (PITR) or manual backups via `pg_restore`.

## 10. Production Validation & Smoke Testing
Run the GitHub Actions workflow **Production release validation** (`production-validation.yml`).
This workflow performs:
- API connectivity and security header checks.
- FHIR metadata validation.
- Frontend static asset and CSP header checks.
- Passive OWASP ZAP Baseline scanning.

## 11. Known Limitations
- The retention cron job permanently deletes data. Ensure legal holds are applied via the app if data must not be deleted.
- Ensure ClamAV (`medflow-clamav-prod`) is healthy; the malware worker will pause processing if ClamAV is unresponsive, causing a pending scan backlog.
