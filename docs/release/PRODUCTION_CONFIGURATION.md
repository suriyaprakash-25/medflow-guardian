# PRODUCTION CONFIGURATION

## Environment Separation
- Production URLs differ from Staging (`api.medflow.app` vs `staging.api.medflow.app`).
- Database and JWT secrets are unique.

## Configuration Items
- `SUPABASE_URL`: Connected to production project.
- `SUPABASE_SERVICE_ROLE_KEY`: Secured in environment variable vault.
- `JWT_SECRET`: Rotated specifically for production.
- `CORS_ORIGINS`: Explicitly mapped to production frontend URLs.
