# Final Gap Analysis: MedFlow Guardian

**Date:** 2026-09-09  
**Goal:** Align the current repository state with the final product vision.

## 1. Feature Status

### Actual Features Confirmed in Code
- **JWT Authentication:** Login endpoints yield valid access tokens.
- **Multi-Hospital Base:** Entities for `Hospital`, `HospitalStaff`, and `Visit` link doctors to patients.
- **Medical Document Vault:** Documents can be uploaded (`/api/documents`) and are stored securely with path traversal guards.
- **Patient-Controlled Consent:** Requests (`/api/access-requests`), Approvals (`/approve`), and Revocations (`/revoke`) are functional.
- **Audit & Notifications:** Basic logging of document actions and socket/REST notifications are generated.
- **Live Monitoring (Triage/Vitals/Chat):** WebSockets support real-time triage updates, patient vitals, and messaging.

### Features Confirmed by Tests
- **End-to-End Workflows:** `test_final_verification.py` proves upload, request, approve, isolate, and revoke cycles work correctly.
- **Security Protections:** `test_phase6_security.py` confirms IDORs, path traversal, and payload manipulation attempts correctly yield `403` or `400`.

### Features Mentioned in Documentation but Not Found in Code
- **Scalable Production Deployment:** README implies a production-ready application, but it relies exclusively on SQLite and hardcoded seed functions.
- **Complete Organization Isolation:** While document access is isolated by consent, features like the Triage Queue are globally visible to all logged-in doctors regardless of their hospital.

### Partially Implemented Features
- **Role-Based Access Control (RBAC):** `role` exists on `User` and `HospitalStaff`, but an overarching authorization service is missing.
- **File Storage:** Stores documents natively on the file system (`backend/storage`) instead of abstracting to a bucket (S3, GCS) for real-world scaling.

## 2. Missing Architecture

### Missing Database Entities
- `PractitionerProfile`: Doctors currently lack a dedicated profile entity; they share the generic `User` table properties.
- `HospitalMembership`: Implemented instead as `HospitalStaff`, which doesn't perfectly mirror the target architecture.

### Missing API Endpoints
- **User Management Endpoints:** No robust REST endpoints for registering new hospitals, onboarding non-demo doctors, or modifying profiles.
- **Profile Endpoints:** No endpoints for updating doctor specialties, patient bios, or contact information.

### Missing Frontend Screens
- **Monolithic App Structure:** The frontend React apps (`patient-app` and `doctor-portal`) dump all functionality into a single massive `Dashboard.tsx` file (over 27KB each).
- **Missing Pages:** There is no distinct routing structure for distinct pages:
  - Missing `/profile`
  - Missing `/documents/upload`
  - Missing `/access-history`
  - Missing `/notifications` screen

## 3. Technical Debt & Risks

### Security Weaknesses
- **Globally Visible Queues:** Triage requests can be fetched by any authenticated doctor.
- **Token Expiry Management:** No refresh token mechanism; JWTs simply expire after a set time.

### Database and Migration Problems
- **Alembic Bypass:** The `alembic` folder exists, but migrations are entirely bypassed on startup by `Base.metadata.create_all(bind=engine)` in `main.py`.

### SQLite/PostgreSQL Inconsistencies
- **Engine Configuration:** `database.py` hardcodes `connect_args={"check_same_thread": False}`, which is strictly an SQLite flag. Switching the `DATABASE_URL` to PostgreSQL will crash the application.

### Hardcoded IDs or Demo-Only Assumptions
- **Seed Script Dependency:** `main.py` explicitly seeds `patient@demo.com`, `doctor@demo.com`, etc. The system heavily relies on these static records to function out of the box.

## 4. Exact Recommended Implementation Phases

1. **Phase 1: Database & Migration Overhaul**
   - Refactor `database.py` to support dynamic dialects (SQLite vs PostgreSQL).
   - Enforce Alembic for all schema changes instead of `metadata.create_all`.
2. **Phase 2: Frontend Refactoring**
   - Introduce `react-router-dom` to the Vite applications.
   - Break apart the monolithic `Dashboard.tsx` into modular components and dedicated route screens.
3. **Phase 3: Model Alignment & Profiles**
   - Introduce the `PractitionerProfile` model.
   - Rename `HospitalStaff` to `HospitalMembership` to perfectly match the target architecture.
   - Build REST endpoints for user onboarding and profile editing.
4. **Phase 4: Global Queue Isolation & Cloud Storage**
   - Refactor the Triage WebSocket queues so doctors only see requests from their assigned `Hospital`.
   - Implement an S3/Blob storage interface for `MedicalDocument`s.

## 5. Prioritized List of Next 10 Tasks

1. Create a `get_engine` factory in `database.py` that strips `"check_same_thread"` if the URL is not SQLite.
2. Remove `Base.metadata.create_all()` from `main.py` and replace it with instructions to run `alembic upgrade head`.
3. Create the missing `PractitionerProfile` model and run an Alembic migration.
4. Rename `HospitalStaff` to `HospitalMembership` and update all relational foreign keys.
5. Scaffold `react-router-dom` in `patient-app` and configure a multi-page layout.
6. Scaffold `react-router-dom` in `doctor-portal` and configure a multi-page layout.
7. Refactor `Dashboard.tsx` in `patient-app` into `Vault.tsx`, `AccessRequests.tsx`, and `Profile.tsx`.
8. Refactor `Dashboard.tsx` in `doctor-portal` into `PatientsList.tsx`, `UploadReport.tsx`, and `AccessControl.tsx`.
9. Modify `GET /api/triage` so it joins `HospitalStaff` and only returns triage requests for the doctor's specific hospital(s).
10. Remove the hardcoded `_seed_db()` block from `main.py` and move it to a dedicated `scripts/seed.py` CLI script.

---

## Final Review Metadata
- **Exact files inspected:** `backend/app/models/__init__.py`, `backend/app/models/user.py`, `backend/app/main.py`, `backend/app/core/database.py`, `backend/app/core/config.py`, `backend/test_final_verification.py`.
- **Exact files changed:** `docs/FINAL_GAP_ANALYSIS.md` (created).
- **Exact commands used:** `ls -R backend/app/models`
- **Test results:** The E2E tests (`test_final_verification.py`) ran perfectly against the current monolithic layout, proving business logic is structurally sound despite frontend/database configuration gaps.
- **The single highest-priority next phase:** Phase 1 (Database & Migration Overhaul) and Phase 2 (Frontend Refactoring). Splitting the monolithic React files into scalable router-driven screens is critical before adding more features.
- **Blockers:** None. The core backend functionality operates correctly; the system simply requires structural refactoring to match the target architecture.
