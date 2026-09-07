# Multi-Hospital & Patient Vault Implementation Plan

## 1. Current Architecture (Based on Actual Code)
- **Backend**: FastAPI running on Uvicorn (`app.main`), with SQLAlchemy ORM and SQLite (`medflow.db`). Alembic is configured for schema migrations.
- **Frontend**: Two React applications (`patient-app` and `doctor-portal`) built with Vite and TypeScript.
- **Authentication**: JWT-based authentication using `python-jose` and `passlib[bcrypt]`.
- **Real-Time Updates**: Custom WebSocket `ConnectionManager` in `backend/app/api/websockets.py` handling broadcast and personal messages.

## 2. Current Routes and Models
**Models**:
- `User`: Handles `email`, `hashed_password`, `role` (patient/doctor).
- `PatientProfile`: Currently has a hardcoded `assigned_doctor_id` and `medical_history`.
- `TriageRequest`: Patient submitted symptoms and AI prioritized status.
- `PatientReading`: Heart rate, O2, BP vitals.
- `Message`: Bidirectional chat messages.

**Core Routes**:
- `POST /api/auth/login`
- `GET/POST /api/triage`
- `GET/POST /api/readings` (including `/api/readings/patient`)
- `GET/POST /api/messages`
- `WS /ws` (WebSocket endpoint)

## 3. Proposed Database Entities and Relationships
To support multiple hospitals and the document vault, we will introduce the following models:

- **`Hospital`**: `id`, `name`, `address`, `contact_info`
- **`HospitalStaff`** (Association): `user_id` (FK User), `hospital_id` (FK Hospital), `role` (admin, doctor)
- **`Visit`**: `id`, `patient_id` (FK User), `hospital_id` (FK Hospital), `doctor_id` (FK User), `date`, `reason_for_visit`
- **`MedicalDocument`**: `id`, `patient_id` (FK User), `hospital_id` (FK Hospital), `uploaded_by_id` (FK User), `document_type` (prescription, scan, lab, summary), `file_path`, `upload_date`
- **`DocumentAccessRequest`**: `id`, `doctor_id` (FK User), `patient_id` (FK User), `status` (pending, approved, rejected, revoked), `duration_hours` (integer), `expires_at` (DateTime), `requested_at`
- **`AccessRequestDocument`** (Association): Links a `DocumentAccessRequest` to specific `MedicalDocument`s.
- **`AuditLog`**: `id`, `user_id` (FK User), `action` (e.g., VIEW_DOC, DOWNLOAD_DOC, REQUEST_ACCESS), `document_id` (FK MedicalDocument, nullable), `timestamp`, `ip_address`

## 4. Proposed API Routes
- **Hospitals**:
  - `GET /api/hospitals`: List hospitals
- **Documents (Vault)**:
  - `POST /api/documents`: Doctor uploads document to a visit.
  - `GET /api/documents/patient`: Patient views their own vault.
  - `GET /api/documents/{id}/download`: Secure file download endpoint.
- **Access Requests**:
  - `POST /api/access-requests`: Doctor requests access to a patient's vault.
  - `GET /api/access-requests/patient`: Patient views pending requests.
  - `PATCH /api/access-requests/{id}`: Patient approves/rejects/revokes (sets `expires_at`).
- **Audit Logs**:
  - `GET /api/audit-logs/patient`: Patient views who accessed their records.

## 5. Proposed Frontend Screens
**Patient App**:
- **My Vault**: Grid/List of all medical documents grouped by Hospital/Visit.
- **Access Control Center**: Dashboard showing pending doctor requests and active permissions. Includes buttons to `Approve (1h, 4h, 1d, 4d)`, `Reject`, and `Revoke`.
- **Audit History**: Timeline view of all access logs.

**Doctor Portal**:
- **Patient Lookup & Request**: Search for a patient (by email/ID) to request vault access.
- **Shared Records**: View approved documents before `expires_at` passes.
- **Visit Management**: Create a visit and upload documents (Prescriptions, Labs, etc.).

## 6. File Storage Strategy
- **Storage Layer**: For the hackathon/initial phase, files will be saved to a local `/storage/documents` directory on the backend server.
- **Security**: The directory will **not** be served statically. File retrieval will strictly route through `GET /api/documents/{id}/download`. This route will inject a dependency that verifies:
  1. The requester is the patient.
  2. OR the requester is the original uploader.
  3. OR the requester has an `APPROVED` `DocumentAccessRequest` where `expires_at > func.now()`.

## 7. Permission and Expiry Design
- When a patient approves a request, the UI passes a duration (1, 4, 24, 96 hours).
- The backend calculates `expires_at = datetime.utcnow() + timedelta(hours=duration)` and sets `status = "approved"`.
- If a patient revokes access, `status` changes to `"revoked"`.
- The authorization middleware/dependency checks both `status == "approved"` and `expires_at > datetime.utcnow()`. Expired tokens automatically yield a `403 Forbidden`.

## 8. Audit Logging Design
- A dedicated FastAPI dependency or SQLAlchemy event listener will intercept document reads.
- When `GET /api/documents/{id}/download` succeeds, a synchronous or background task inserts an `AuditLog` row.
- All actions (Upload, Request, Approve, Revoke, View) are logged immutably.

## 9. Migration Strategy from Current Schema
- The existing SQLite schema will be migrated using `alembic revision --autogenerate`.
- **Schema Changes**: 
  - The `PatientProfile.assigned_doctor_id` will be deprecated/removed, as patients will now exist independently of a single doctor and associate via `Visit` records or `Hospital` records.
  - Default all existing users to a "Default Hospital" to prevent orphan data during the transition.

## 10. Testing Strategy
- **Unit Tests**: Mock `datetime` to test strict boundary conditions of the 1h/4h/1d/4d expiry logic.
- **Integration Tests**: API tests ensuring a Doctor cannot bypass the `DocumentAccessRequest` gate for another hospital's patient documents.
- **E2E Tests**: Cypress or Browser Subagent simulating the exact flow: Doctor requests -> Patient approves -> Doctor downloads -> Expiry passes -> Doctor is blocked.

## 11. Phased Implementation Order
1. **[COMPLETED] Phase 1: DB Schema & Migrations**: Create new models (Hospital, MedicalDocument, DocumentAccessRequest, AuditLog) and run Alembic.
2. **[COMPLETED] Phase 2: Secure File Storage**: Implement the upload and secure download API endpoints.
3. **[COMPLETED] Phase 3: Vault API & Access Logic**: Implement the request, approve, and expiry verification middleware.
4. **[COMPLETED] Phase 4: Audit Logging**: Integrate action tracking for all vault events.
5. **Phase 5: Frontend UIs**: Build the Patient Vault, Access Control Center, and Doctor Upload/Request interfaces.
6. **Phase 6: WebSocket Notifications**: Broadcast real-time alerts when a doctor requests access or uploads a file.

## 12. Risks and Decisions Requiring Confirmation
- **File Encryption**: Should we encrypt files at rest (AES-256) on the local disk, or is OS-level security sufficient for this phase?
- **Storage Limits**: SQLite has limits, but the actual files will be on disk. We must ensure file names are sanitized to prevent path traversal attacks during upload.
- **Patient Identification**: How will doctors search for patients? By email? By a unique Patient ID? (Recommendation: Email or a generated unique MedFlow ID).
