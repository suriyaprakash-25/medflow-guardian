# Supabase Migration Audit

## 1. Current Architecture
- **Frontend**: React, TypeScript, Vite, Tailwind CSS (`patient-app`, `doctor-portal`) communicating via REST and native WebSockets.
- **Backend**: Python, FastAPI, Uvicorn, SQLAlchemy.

## 2. Current Database Architecture
- **Database Engine**: SQLite.
- **Storage Location**: Local file `medflow.db` stored in the `backend/` directory.
- **Connection Configuration**: Fetched from environment variable `DATABASE_URL`, defaulting to `sqlite:///./medflow.db` in `app.core.config`.

## 3. Current Database Models
- **Auth**: `User` (patient, doctor, admin roles).
- **Core Entity**: `Hospital`, `HospitalStaff`, `Visit`.
- **Medical Data**: `MedicalDocument`, `TriageRequest`, `VitalsReading`.
- **Security & Activity**: `DocumentAccessGrant`, `Notification`, `AuditLog`.

## 4. Current Database Initialization
- Uses Alembic migrations via `backend/scripts/seed.py`. 
- Does not rely on `Base.metadata.create_all(...)` in the main application lifecycle, successfully using declarative base models mapped to Alembic.

## 5. Current Migration Situation
- An `alembic/` directory and `alembic.ini` exist.
- Migrations are actively maintained inside `alembic/versions/`.
- `env.py` fetches the SQLAlchemy connection string from `app.core.config.settings.SQLALCHEMY_DATABASE_URI`.

## 6. Current Document Storage Implementation
- **Location**: `backend/storage/documents/`.
- **Upload**: `app.api.document.upload_document` streams the file to disk using `shutil.copyfileobj`.
- **Download**: `app.api.document.download_document` verifies authorization and returns the file using `fastapi.responses.FileResponse`.
- **Protection**: Filenames are sanitized into UUIDs. Path traversal checks are inherently covered by UUID generation, though arbitrary local storage paths are used.

## 7. Current Authentication Flow
- Handled by `app.api.auth.login` generating JWTs via `jose` and passwords verified with `passlib[bcrypt]`.
- Frontend passes JWTs via standard HTTP Bearer headers and WebSocket query parameters.

## 8. Current Authorization Flow
- Enforced at the route level using `get_current_user`, `get_current_doctor`, and `get_current_patient` dependencies.
- Doctors must have active `DocumentAccessGrant`s or `HospitalStaff` affiliations to download patient documents.

## 9. Hospital Isolation Behavior
- Enforced at the query level. For instance, `upload_document` and `download_document` explicitly cross-reference the `HospitalStaff` table to ensure a doctor can only access records associated with their assigned hospitals.
- Triage queue filtering inherently requires hospital affiliation checks.

## 10. Existing API Contracts
- Fast API REST routes returning explicitly defined Pydantic schemas (e.g., `MedicalDocumentSchema`).
- These contracts must remain identical so the React frontends do not break.

## 11. Existing WebSocket Contracts
- Managed by `ConnectionManager` in `app.api.websockets`.
- Supports `send_personal_message`, `broadcast_to_role`, and `broadcast_to_hospital`.
- Authentication relies on decoding the JWT token passed upon WebSocket connection.

## 12. Existing Frontend Dependencies on Backend
- Relies heavily on REST (`/api/auth/login`, `/api/documents/`, etc.) and WS connections (`/ws?token=...`).
- Relies on the backend to provide readable error messages and standard HTTP status codes.

## 13. Existing Tests
- Comprehensive `pytest` suite present in `backend/tests/` (e.g., `test_security.py`, `test_phase3_access.py`, etc.).
- Explicit tests for database config exist, asserting `sqlite` usage.

## 14. Risks
- **Testing**: Many tests may rely on the speed and in-memory/file nature of SQLite. Moving to PostgreSQL requires a running Postgres instance or Supabase project to execute tests successfully.
- **Data Migration**: Existing `medflow.db` data needs to be safely converted to PostgreSQL. SQLite type affinities (e.g., storing booleans as integers) might cause minor friction during direct raw data migration.
- **Storage**: Changing `FileResponse` to a Supabase signed URL or direct byte-stream proxy will require careful consideration of API return types. We must ensure the frontend `fetch` blob logic continues working seamlessly without CORS or structural breaks.

## 15. Migration Plan
We will follow the mandated 15 phases precisely. The implementation plan outlines this execution strategy.

## 16. Files that MUST Change
- `backend/requirements.txt` (adding `psycopg2-binary`, `supabase` client).
- `backend/app/core/config.py` (adding Supabase ENV vars).
- `backend/app/api/document.py` (rewriting local storage logic to use Supabase).
- `backend/alembic/env.py` (ensuring PostgreSQL compatibility).
- `.env.example` (documenting secrets).
- `backend/tests/*` (updating db connection fixtures if required).

## 17. Files that should NOT Change
- Any `.tsx` or React component files in `patient-app/` and `doctor-portal/` (except pointing to standard API configs).
- `app/api/websockets.py` (logic is solid, requires no Supabase integration).
- Core SQLAlchemy models in `app/models/` (unless specific Postgres types are strictly necessary).
