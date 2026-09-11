# Doctor Portal Current State

## 1. Existing Screens
- **Dashboard** (`DashboardView.tsx`): Displays the Triage Queue. Doctors can assign themselves, change status, or view requests.
- **My Patients** (`Patients.tsx`): Displays a list of patients the doctor has interacted with or been assigned to.
- **Patient Details** (`PatientDetails.tsx`): Contains active patient context, live vitals, historical readings, and a real-time chat interface.
- **Upload Report** (`UploadReport.tsx`): Form to upload medical documents (prescriptions, labs, scans) linked to a specific visit.
- **Access Control** (`AccessControl.tsx`): Allows doctors to request access to external/historical patient documents from other hospitals.
- **Notifications** (`Notifications.tsx`): A basic list of notifications with mark-as-read functionality.
- **Profile/Audit** (`Profile.tsx`): Displays security audit logs tracking the doctor's activity across patient records.

## 2. Existing Routes
- `/login`: Authentication entry.
- `/dashboard`: Triage queue overview.
- `/patients`: List of active patients.
- `/patient-details`: Focused view on a single patient.
- `/upload-report`: Document upload workflow.
- `/access-control`: Document access requests.
- `/notifications`: Doctor alerts.
- `/profile`: Audit logs and settings.

## 3. Existing API Calls
All API requests are heavily authenticated and role-based:
- `GET /api/triage/`: Fetches all triage requests visible to the doctor.
- `PATCH /api/triage/{id}/status`: Updates request status.
- `GET /api/visits/doctor`: Fetches patient visits associated with the logged-in doctor.
- `GET /api/messages/{id}` & `POST /api/messages`: Real-time messaging.
- `GET /api/readings/{id}`: Fetches historical vitals.
- `POST /api/documents`: Uploads a document.
- `GET /api/documents/metadata/{patient_id}`: Views available remote documents.
- `POST /api/access-requests`: Submits a request to view a document.
- `GET /api/access-requests/doctor` & `GET /api/access-grants/doctor`: Views requests and grants.
- `GET /api/documents/{docId}/download`: Downloads an authorized document.
- `GET /api/notifications` & `/read-all`: Handles alerts.
- `GET /api/audit/doctor`: Fetches security logs.

## 4. Existing WebSocket Behavior
- Connected via `ws://localhost:8080/ws?token=...` in `Layout.tsx`.
- Listens for: `message`, `triage_update`, `reading`, `access_request_created`, `access_request_approved`, `access_request_rejected`, `access_revoked`, `notification_created`.
- Auto-reconnects every 3000ms. Refetches APIs immediately upon relevant events.

## 5. Existing Components
- `Layout.tsx`: The primary Shell that provides context (`useDoctorContext`) to all children.
- No other reusable components exist; UI is largely monolithic.

## 6. Existing Styling Approach
- Basic `App.css` containing legacy CSS classes (`.card`, `.btn-primary`, `.input-field`, `.dashboard-grid`).
- Highly generic SaaS look. Does not look like a clinical workspace.

## 7. Supported Functionality
- Viewing, assigning, and resolving triage requests.
- Real-time patient chat.
- Real-time simulated vitals monitoring.
- Secure document uploading with validation.
- Requesting temporary access to off-network patient records.
- Downloading approved documents.
- Viewing personal audit logs.

## 8. Unsupported Functionality
- Viewing full patient medical history across all hospitals without explicit access grants.
- Generating new fake patients or custom hospital entities.
- Triage deletion or priority modification (handled by AI).

## 9. Current UX Problems
- Extremely wide, empty generic cards.
- Important clinical information (Triage priority) is hidden inside cards rather than being scannable in a queue list.
- Triage Queue lacks sorting and filters.
- Exposes raw database IDs (`Patient ID: 3`, `Hospital ID: 2`) instead of resolving to human-readable names.
- The Dashboard (`DashboardView.tsx`) is functionally just a Triage Queue; it lacks a true "Overview" of urgent tasks, pending access, and active patients.
- Upload workflow is a raw HTML form with basic selects, lacking modern step-by-step guidance.
- Access Control form requires manual Patient/Hospital ID entry instead of utilizing search/select.

## 10. Components to Safely Extract
- `TriageQueueItem`: A reusable row for triage requests.
- `VitalsMonitor`: A specialized card for vitals visualization.
- `DoctorChatDrawer`: The messaging interface.
- `StatCard`: A summary block for the dashboard overview.
- All base UI (`Button`, `Card`, `Select`, `Input`, `Badge`) can be leveraged from `@shared/ui`.
