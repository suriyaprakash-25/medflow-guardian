# MedFlow Guardian - Demo Verification Baseline

**Date of Verification:** 2026-09-06
**Auditor:** Antigravity

This document records the baseline state of the MedFlow Guardian demo before applying demo hardening and high-value completion improvements.

## 1. Startup Commands and Ports
*   **Backend:** `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload` (Port: 8080)
*   **Patient App:** `npm run dev -- --port 5174` (Port: 5174)
*   **Doctor Portal:** `npm run dev -- --port 5175` (Port: 5175)

## 2. Demo Accounts
*   **Patient:** `patient@demo.com` / `password`
*   **Doctor:** `doctor@demo.com` / `password`

## 3. Tests Executed
*   **Milestone Tests:** `test_milestone.py`
    *   Verifies patient and doctor login.
    *   Verifies triage request submission with AI priority generation.
    *   Verifies doctor retrieving triage queue.
    *   Verifies doctor updating triage status.
    *   Verifies patient retrieving updated triage history.
*   **Security Tests:** `test_security.py`
    *   Verifies missing/invalid JWT (401).
    *   Verifies role-based access control (403 for cross-role access).

## 4. Results
*   **Milestone Tests:** ✅ PASSED. All steps executed successfully without errors.
*   **Security Tests:** ✅ PASSED. All unauthorized/forbidden access attempts correctly blocked.
*   **Manual Demo Journey:** ✅ PASSED (Based on the preceding comprehensive browser subagent run).
    *   Authentication works correctly for both roles.
    *   AI triage generates expected critical priority and reasoning.
    *   Real-time (WebSocket) triage queue and status updates function correctly.
    *   Simulated vitals broadcast properly from patient to doctor.
    *   Bidirectional real-time messaging operates normally.
    *   State persists across browser refreshes via REST fallbacks.

## 5. Known Limitations
*   Patient-to-Doctor assignment is hardcoded (Patient ID=1, Doctor ID=2).
*   AI is keyword-based (mock prototype), not a true ML model.
*   Vitals are simulated locally in the patient app.
*   SQLite is used for the database (single-file, not for production scale).
*   No WebSocket auto-reconnect logic exists (requires manual refresh if disconnected).
*   No historical readings view in UI (only live vitals).
