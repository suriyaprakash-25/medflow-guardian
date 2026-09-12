# Phase 2: Database and Storage Foundation

This document outlines the actual implemented architecture for the MedFlow Guardian database and storage foundation following the Phase 2 hardening process.

## 1. Current Database Architecture
- **Database Engine**: Supabase PostgreSQL.
- **ORM**: SQLAlchemy.
- **Fail-Fast Validation**: The backend strictly validates the `DATABASE_URL` during initialization (`app/core/config.py`). If the URL points to SQLite (`sqlite://`) or is missing, the application deliberately crashes to prevent silent usage of local databases in production.

## 2. SQLAlchemy Configuration & PostgreSQL Connection Strategy
- **Connection Strategy**: Uses direct configuration to the specified `DATABASE_URL`.
- **Pooling**: Configured in `app/core/database.py` with `pool_size=5`, `max_overflow=10`, `pool_timeout=30`, and `pool_pre_ping=True`. This provides robust behavior for PostgreSQL connections and gracefully handles connection drops when using poolers like Supabase.

## 3. Alembic Migration Strategy
- **Role**: Alembic is the strict schema authority.
- **Changes Made**: All `Base.metadata.create_all(...)` commands were ensured to be absent from production startup.
- **Model Integrity**: Foreign keys for entities (`patient_id`, `doctor_id`, `hospital_id`) across `audit.py`, `document.py`, and `access.py` are explicitly indexed (`index=True`) to optimize query access.

## 4. Session/Transaction Strategy
- **Pattern**: Routes use `Depends(get_db)` to yield independent, request-scoped sessions.
- **Transaction Bundling**: Write-heavy routes (e.g., Document Uploads in `app/api/document.py`) explicitly bundle `MedicalDocument`, `AuditLog`, and `Notification` inserts into single `try/except` transaction blocks, calling `db.commit()` only at the end and `db.rollback()` on failure.

## 5. Supabase Storage Architecture & Security
- **Service**: A new `StorageService` (`app/services/storage.py`) wraps raw Supabase `storage3` calls.
- **Private Bucket Strategy**: Medical documents are uploaded to a private bucket (`settings.SUPABASE_BUCKET`).
- **Authorization Boundary**: The backend acts as the sole authorization gate. No browser touches the Supabase storage directly.
- **File Validation**: `StorageService.upload_document` enforces allowed MIME extensions (`.pdf`, `.jpg`, `.png`, etc.) and prevents path traversal by generating a UUID storage path (`patient/<id>/<uuid>.ext`).
- **No Local Disk Fallback**: All `shutil` and local fallback logic (`STORAGE_DIR`) was completely removed.

## 6. Environment Configuration
- Configuration is centralized in `app/core/config.py` using `dotenv`.
- Production requires `DATABASE_URL`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY`.

## 7. CORS and Network Boundary
- **Backend**: `app/main.py` parses `FRONTEND_CORS_ORIGINS` from the environment, defaulting to standard dev ports, avoiding `allow_origins=["*"]`.
- **Frontend**: Both Vite frontends proxy to `import.meta.env.VITE_API_BASE_URL`, replacing hardcoded `http://localhost:8080`.

## 8. Verification Results
- **VERIFIED**:
  - Frontend build processes (`npm run build`).
  - Removal of local `storage` logic.
  - Fail-fast enforcement of `DATABASE_URL`.
  - Transaction bundling for uploads.
  - StorageService abstraction.
  - `pytest` execution successfully passed against the Supabase Pooler.
  - Alembic migrations correctly captured foreign key indexing.

## 9. Known Limitations & Remaining Risks
- **Testing**: End-to-end testing with actual mock data on Supabase remains to be structurally validated via CI/CD.
- **Signed URL Revocation**: `StorageService` currently uses direct file downloads (streaming via bytes) rather than signed URLs in this iteration. While secure, streaming large files through FastAPI may impact memory if scaled.
- **Audit Logging**: Still lacks enforcement states (deferred to Phase 3+).

## 10. Phase 3 Prerequisites
- Begin the structural database refactor for the `Consent` and `ConsentState` entities.
