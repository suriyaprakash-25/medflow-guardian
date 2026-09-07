# MedFlow Guardian - Security & Privacy Review

**Date:** 2026-09-07  
**Scope:** Phase 6 Security, Privacy, and Production-Readiness Review  
**Disclaimer:** This is a privacy-oriented access control prototype designed around patient-controlled consent. It has not been assessed against actual medical regulatory compliance standards (such as HIPAA or GDPR) and should not be considered compliant out-of-the-box.

---

## Vulnerabilities Found & Fixes Applied

### 1. Insecure Direct Object Reference (IDOR) on Patient Readings
- **Severity:** High
- **Description:** `GET /api/readings/{patient_id}` allowed any authenticated doctor to query the vitals history of any patient in the system, bypassing hospital and visit constraints.
- **Fix Applied:** Modified `app/api/monitoring.py` to enforce that the `current_doctor` has a registered `Visit` with the `patient_id` before returning the readings.
- **Files Changed:** `backend/app/api/monitoring.py`

### 2. Unauthorized Bidirectional Messaging (IDOR)
- **Severity:** High
- **Description:** The `POST /api/messages` and `GET /api/messages/{user_id}` endpoints lacked relationship checks. A doctor could message any patient, and a patient could message any doctor.
- **Fix Applied:** Enforced a `Visit` validation check in `app/api/monitoring.py` ensuring that messages can only be exchanged if the patient and doctor have a shared visit history.
- **Files Changed:** `backend/app/api/monitoring.py`

### 3. Patient Document Metadata Leakage (IDOR)
- **Severity:** Medium
- **Description:** `GET /api/documents/metadata/{patient_id}` allowed doctors to list the titles and types of medical documents for any patient, even if they never interacted with the patient.
- **Fix Applied:** Enforced a relationship constraint in `app/api/document.py` requiring the doctor to have at least one registered `Visit` with the patient to view metadata.
- **Files Changed:** `backend/app/api/document.py`

### 4. Cross-Origin Resource Sharing (CORS) Misconfiguration
- **Severity:** Medium
- **Description:** The `CORSMiddleware` was configured with `allow_origins=["*"]` alongside `allow_credentials=True`, violating browser security standards and allowing potential Cross-Site Request Forgery (CSRF).
- **Fix Applied:** Tightened CORS origins in `app/main.py` to strict localhost addresses representing the front-end ports (`5173`, `5174`, `5175`).
- **Files Changed:** `backend/app/main.py`

### 5. Path Traversal & Weak File Validation
- **Severity:** Medium
- **Description:** The document upload handler used `os.path.splitext` on the user-provided filename. While the stem was replaced by a UUID preventing directory traversal, malicious extensions (e.g. `.sh`, `.exe`) could still be attached and executed depending on OS handling.
- **Fix Applied:** Added explicit file extension validation matching against a static allowlist (`.pdf`, `.jpg`, `.jpeg`, `.png`, `.txt`) in `app/api/document.py`.
- **Files Changed:** `backend/app/api/document.py`

### 6. Hardcoded Cryptographic Secrets
- **Severity:** High (in Production)
- **Description:** The `SECRET_KEY` used for JWT signature generation was hardcoded to a static string in `app/core/config.py`.
- **Fix Applied:** Replaced the hardcoded fallback with `secrets.token_urlsafe(32)`, ensuring secure, ephemeral tokens for local environments and enforcing `os.getenv` for production.
- **Files Changed:** `backend/app/core/config.py`

---

## Tests Added
A dedicated security integration test suite has been implemented to continuously verify these fixes:
- **`backend/test_phase6_security.py`**
  - **Test IDOR 1:** Validates that unauthorized doctors get `403 Forbidden` on `/api/readings/{patient_id}`.
  - **Test IDOR 2:** Validates that unauthorized doctors get `403 Forbidden` on `/api/documents/metadata/{patient_id}`.
  - **Test IDOR 3:** Validates that users get `403 Forbidden` when attempting to message unrelated parties.
  - **Test Path Traversal/Extension:** Validates that malicious file uploads with invalid extensions (e.g., `evil.pdf/../malware.sh`) are rejected with `400 Bad Request`.

---

## Remaining Limitations & Privacy Notes

1. **Global Triage Queue:** Currently, the Triage Queue (`GET /api/triage/`) acts as a global queue for the platform, allowing doctors to view pending triage requests across hospitals. While functional for this prototype's architecture, a production healthcare app would require triage visibility strictly siloed to specific hospitals or departments.
2. **Database Encryption:** Medical documents and PII are stored in plain text in the SQLite database. Production rollouts should implement At-Rest Encryption (e.g., AWS KMS) and field-level encryption for symptoms and chat histories.
3. **Audit Log Mutability:** Audit logs are currently stored in a standard SQL table. A compliant system must use an immutable, append-only ledger for audit logs to prevent tampering by compromised administrators.
