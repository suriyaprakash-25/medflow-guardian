# Phase 12 Secret Management Audit

**Date:** 2026-09-11
**Objective:** Audit the repository for leaked secrets and establish the production secret boundary.

## 1. Discovery Results

### 1.1 Backend Service Secrets
- **DATABASE_URL**: Found in `.env` and `.env.example`. *The actual string in `.env` points to Supabase production, but `.env` is ignored via `.gitignore`.*
- **SUPABASE_SERVICE_ROLE_KEY**: Found in `.env`. Properly injected via `os.getenv` in `app/core/config.py`.
- **SECRET_KEY**: Generated automatically using `secrets.token_urlsafe()` if not provided.
- **ENCRYPTION_KEY**: Generated automatically using `Fernet.generate_key()` if not provided.

### 1.2 Frontend Bundles
- **Vite React App variables**: Frontends strictly use `VITE_API_BASE_URL` and occasionally `VITE_WS_URL`.
- **No Private Keys Leaked**: I performed a search across `patient-app`, `doctor-portal`, and `admin-portal`. Neither `SUPABASE_SERVICE_ROLE_KEY` nor `DATABASE_URL` is imported, bundled, or accessible in frontend code. 

### 1.3 CI/CD Environment
- **`ci.yml` Workflow**: Uses a local `postgres:15` service container. It passes `dummy_key` for Supabase and `test_secret_key_ci` for the JWT secret. **CLEAN.** No production secrets are exposed in the GitHub Actions configuration.

## 2. Risk Assessment
- `.env` files are correctly in `.gitignore`. 
- However, generating a random `SECRET_KEY` and `ENCRYPTION_KEY` at runtime via `config.py` means **every time the FastAPI server restarts, all user sessions will instantly become invalid, and MFA secrets will be un-decryptable!** This is a critical operational flaw.

## 3. Required Mitigation (Phase 12)
1. In `app/core/config.py`, the system MUST strictly require `SECRET_KEY` and `ENCRYPTION_KEY` in production (`ENV == "production"`), crashing the application if they are missing, rather than auto-generating ephemeral keys.
2. Production secrets must be mapped via the `render.yaml` deployment definition as environment variables.
