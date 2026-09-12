# PHASE 8 REALITY AUDIT

| Area | Expected | Actual | Evidence | Gap | Status |
|------|----------|--------|----------|-----|--------|
| **Frontend Setup** | Vite + React + Tailwind | Vite + React + Tailwind | `package.json`, `.tsx` files in `patient-app` & `doctor-portal` | None | VERIFIED |
| **Auth Guards** | ProtectedRoute + Interceptor | ProtectedRoute exists | `App.tsx` & `api.ts` from Phase 7 | None | VERIFIED |
| **Mock Vitals** | Removed from UI | Removed in Phase 7 | `DashboardView.tsx` shows 'Historic Data Only' | None | VERIFIED |
| **Consent Model** | Stateful & Immutable | `ConsentState` append-only | `models/consent.py` | Missing concurrency control (`FOR UPDATE`) | PARTIAL |
| **Audit Logs** | Comprehensive & Append-Only | Basic model, no `UPDATE`/`DELETE` API | `models/audit.py`, `api/audit.py` | Missing security context fields (`operation`, `resource_type`, `decision`, etc.) | PARTIAL |
| **WebSocket Security** | Per-message authorization | Connection-level only | `api/websockets.py` | WS broadcasts don't evaluate active consent state | BROKEN |
| **Appointments** | Exists in DB/UI | Not found | `grep_search` found no Appointment model | Need to implement backend & UI | NOT VERIFIED |
| **Visits** | Exists in DB/UI | `Visit` model exists | `models/hospital.py` | Lacks dedicated views/authz expansion | PARTIAL |
| **Prescriptions/Meds** | Exists in DB/UI | Not found | `grep_search` found no models | Need to implement backend & UI | NOT VERIFIED |
| **Lab Results** | Exists in DB/UI | Not found | `grep_search` found no models | Need to implement backend & UI | NOT VERIFIED |
| **Clinical Notes** | Exists in DB/UI | Not found | `grep_search` found no models | Need to implement backend & UI | NOT VERIFIED |
| **Messaging** | Exists in DB/UI | `Message` model exists | `models/monitoring.py` | Needs organization/consent scoping | PARTIAL |
| **Triage** | Scoped access | Exists | `api/triage.py` | Ensure no fake data in production UI | PARTIAL |
