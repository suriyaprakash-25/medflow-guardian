# Production Configuration

MedFlow Guardian enforces strict environment configuration using Pydantic `BaseSettings`. 
If specific production variables are missing, the application will refuse to boot.

## Required Environment Variables

| Variable | Description | Production Requirement |
|----------|-------------|------------------------|
| `ENV` | `development`, `staging`, or `production` | Must be `production`. |
| `SECRET_KEY` | JWT signing key | Must be explicitly set and >= 32 chars. |
| `DATABASE_URL` | PostgreSQL connection string | Must not be SQLite. Must use a secure connection. |
| `FRONTEND_CORS_ORIGINS` | Allowed CORS origins | Must not contain `localhost` or `*`. |
| `SUPABASE_URL` | Cloud storage endpoint | Required. |
| `SUPABASE_KEY` | Storage service key | Required. |
| `SUPABASE_BUCKET` | The bucket name | Required. |

## Pool Settings
- `DB_POOL_SIZE`: Default is 5. Designed to prevent overwhelming Supabase PgBouncer.
- `DB_MAX_OVERFLOW`: Default is 10. Allows spikes but strictly controls concurrent DB threads.
