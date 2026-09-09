# Verified Repository Audit

**Date:** 2026-09-09
**Goal:** Establish the exact, verified truth of the MedFlow Guardian codebase to serve as the foundation for structural reliability improvements.

---

## 1. Exact Existing Models and Relationships
- **User:** `id`, `email`, `hashed_password`, `role`. Relates to `PatientProfile`, `HospitalStaff`, `Visit`, `TriageRequest`.
- **PatientProfile:** `user_id`, `assigned_doctor_id`, `medical_history`.
- **Hospital:** `name`, `address`. Relates to `HospitalStaff`, `Visit`.
- **HospitalStaff:** `user_id`, `hospital_id`, `role`. (Serves the role of "HospitalMembership").
- **Visit:** `patient_id`, `hospital_id`, `doctor_id`, `status`.
- **MedicalDocument:** `patient_id`, `hospital_id`, `uploaded_by_doctor_id`, `visit_id`, `document_type`, `stored_filename`.
- **DocumentAccessRequest:** `patient_id`, `requesting_doctor_id`, `requesting_hospital_id`, `status`, `requested_documents` (M2M).
- **DocumentAccessGrant:** `access_request_id`, `patient_id`, `doctor_id`, `hospital_id`, `status`, `expires_at`, `granted_documents` (M2M).
- **AuditLog:** Records actor, action, and entity IDs.
- **Notification:** Records user_id, message, and read status.
- **TriageRequest, PatientReading, Message:** Models exist to support live monitoring features.

## 2. Exact Existing API Routes
- `POST /api/auth/login`
- `POST /api/documents`
- `GET /api/documents/patient`
- `GET /api/documents/metadata/{patient_id}`
- `GET /api/documents/{document_id}/download`
- `POST /api/access-requests`
- `GET /api/access-requests/doctor`
- `GET /api/access-requests/patient`
- `POST /api/access-requests/{request_id}/approve`
- `POST /api/access-requests/{request_id}/reject`
- `POST /api/access-grants/{grant_id}/revoke`
- `GET /api/access-grants/patient`
- `GET /api/access-grants/doctor`

## 3. Exact Authorization Checks
- `POST /api/documents`: Verifies `current_doctor` is affiliated with the visit's hospital via `HospitalStaff`.
- `GET /api/documents/{document_id}/download`: 
  - **Patient:** Can only download if `doc.patient_id == current_user.id`.
  - **Doctor:** Checks if doctor's `HospitalStaff` affiliations match the document's `hospital_id`. If not, checks for an `active` `DocumentAccessGrant` where `expires_at > datetime.utcnow()`. Returns `403` if neither matches.

## 4. Exact WebSocket Authorization Behavior
- Defined in `app/api/websockets.py`. Expects a JWT `token` via query string (`ws://.../ws?token=...`). 
- Calls `jwt.decode` using `settings.SECRET_KEY` and disconnects with code 1008 if invalid.

## 5. Exact Database Engine Configuration
- Defined in `app/core/database.py`.
- **Finding:** Hardcodes `connect_args={"check_same_thread": False}`. This is strictly an SQLite parameter and will crash the application if `DATABASE_URL` is switched to PostgreSQL.

## 6. Whether Alembic is Actually Used
- The `alembic/` folder and `alembic.ini` exist.
- **Finding:** Migrations are entirely bypassed at runtime because `app/main.py` explicitly calls `Base.metadata.create_all(bind=engine)` inside the `_seed_db()` startup sequence.

## 7. Exact Seed Behavior
- Defined in `app/main.py` `_seed_db()`.
- Automatically inserts demo accounts (`patient@demo.com`, `doctor@demo.com`, `doctor2@demo.com`), creates hospitals, maps `HospitalStaff`, and creates dummy `Visit` records directly via SQLAlchemy ORM every time the app restarts.

## 8. Exact Frontend Routes and Screens
- `patient-app/` and `doctor-portal/` both contain `src/pages/Login.tsx` and `src/pages/Dashboard.tsx`.
- `package.json` files **do** contain `"react-router-dom": "^7.18.3"`.
- Routing strictly navigates between `/login` and `/` (Dashboard). The dashboards themselves are monolithic (27-30KB single files).

## 9. Exact Test Commands and Results
- Automated integration test `test_final_verification.py` executes smoothly from start to finish via `python test_final_verification.py`.
- Security suite `test_phase6_security.py` passes successfully, validating IDOR guards.

## 10. Confirmed Gaps
1. Database engine hardcodes SQLite parameters preventing dialect swapping.
2. Alembic is bypassed, putting data at risk during schema changes.
3. Frontends are structurally monolithic despite having the router dependency installed.

## 11. Claims from the Previous Gap Analysis That Are Incorrect or Unverified
- **Incorrect Claim:** "Scaffold `react-router-dom` in `patient-app`...". *Correction:* The dependency `react-router-dom` is already installed and basic routing (`/login`) is active.
- **Incorrect Claim:** "Implement S3/Blob storage". *Correction:* The current local `storage/documents` perfectly isolates files using `uuid` hashing and fulfills the verified MVP requirements; cloud abstraction is unnecessary scope creep for this phase.
- **Incorrect Claim:** "Missing HospitalMembership". *Correction:* `HospitalStaff` functionally fulfills this requirement perfectly without needing immediate renaming.

## 12. Recommended Implementation Order
1. Refactor `app/core/database.py` to conditionally apply `check_same_thread` only for SQLite, allowing safe dialect switching.
2. Remove `Base.metadata.create_all` from `main.py` to enforce Alembic migrations, moving seed logic to a separate dedicated script or robust lifecycle event.
3. Break the monolithic `Dashboard.tsx` files into logical router-driven sub-components based on existing confirmed backend contracts.
