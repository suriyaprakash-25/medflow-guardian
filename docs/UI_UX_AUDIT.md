# MedFlow Guardian UI/UX Audit

This document serves as a complete analysis of the current frontend implementation for both `patient-app` and `doctor-portal`, verifying existing functionalities against UX standards.

## 1. Existing Screens
### Patient App
- **Login**: Basic username/password entry.
- **Dashboard (Triage & Chat)**: Form to submit symptoms; live chat with doctor.
- **My Documents**: List of uploaded files with download buttons.
- **Access Requests**: Pending requests from doctors needing consent (with duration selection).
- **Access History**: Active temporary access grants (with immediate revocation button).
- **Notifications**: System notifications (mark as read).
- **Profile & Audit**: Patient visit history, historic triage queue, security audit log table.

### Doctor Portal
- **Login**: Basic username/password entry.
- **Admin Dashboard**: (Admin only) Lists affiliated doctors, cross-hospital visits, and origin documents.
- **Triage Queue**: Queue of patient symptoms with AI reasoning and actionable statuses.
- **My Patients**: List of active hospital visits with 'View Details' action.
- **Patient Details (Vitals & Chat)**: Real-time and historic vitals, plus direct patient chat.
- **Upload Report**: Form to upload medical files (prescription, lab report, etc.) to a visit.
- **Access Control**: Form to request patient documents across hospitals, plus view active approved grants.
- **Notifications**: System notifications.
- **Profile**: Doctor's audit log.

## 2. Existing Components
- **Layout**: Sidebar navigation with dynamic active states, WebSocket connection status indicator.
- **Cards**: Generic `.card` container for sections.
- **Badges**: Basic inline spans for status/priority formatting.
- **Form Groups**: Generic text inputs and native `<select>` dropdowns.

## 3. Existing Routes
Both apps use `react-router-dom` with the following structures:
- `patient-app`: `/login`, `/dashboard`, `/documents`, `/access-requests`, `/access-history`, `/notifications`, `/profile`
- `doctor-portal`: `/login`, `/dashboard`, `/patients`, `/patient-details`, `/upload-report`, `/access-control`, `/notifications`, `/profile`

## 4. Existing API Calls
All calls utilize standard `axios` REST requests securely passing JWT tokens.
- **Auth**: `/api/auth/login`
- **Triage**: `/api/triage/` (GET/POST/PATCH)
- **Documents**: `/api/documents` (Upload, metadata, download)
- **Access**: `/api/access-requests` (POST request, GET patient/doctor, approve/reject)
- **Grants**: `/api/access-grants` (GET, revoke)
- **Visits/Hospital**: `/api/visits/patient`, `/api/visits/doctor`
- **Messages/Vitals**: `/api/messages`, `/api/readings`
- **Audit/Notifications**: `/api/audit`, `/api/notifications`

## 5. Existing WebSocket Behavior
**State Source**: `ws://localhost:8080/ws?token=<JWT>` handled centrally in `Layout.tsx`.
- Connects on successful login; displays "Live", "Connecting...", or "Offline" badge.
- Automatically reconnects on close/error (3s timeout).
- Receives real-time events: `triage_update`, `message`, `reading`, `access_request_created`, `access_request_approved`, `notification_created`, `access_revoked`.
- Re-fetches HTTP endpoints silently in the background when specific events trigger.

## 6. Existing Loading / Error / Empty States
- **Loading states**: Simple "Fetching..." or "Uploading..." text on buttons. The overall page lacks skeleton loaders or transition indicators.
- **Error states**: Rely completely on blocking `window.alert()` or standard generic `.error` banners.
- **Empty states**: Basic `<p className="empty-state">No records.</p>` text snippets, lacking visual cues or calls-to-action.

## 7. Existing Design Tokens
Defined strictly in native CSS (`App.css`):
- **Colors**: `--primary` (blue), `--bg` (slate), `--card-bg` (white), `--text-main`, `--text-muted`, `--border`.
- **Status Colors**: `--status-pending` (amber), `--status-reviewed` (blue), `--status-resolved` (emerald).
- **Priority Colors**: `--priority-critical` (red), `--priority-high` (orange), etc.
- No standard spacing scale or typography tokens (relies on system fonts and manual pixel margins).

## 8. Confirmed UX Problems
- **Visuals**: Very basic CSS with an excessive amount of whitespace in the generic grid layout.
- **Hierarchy**: Lack of clear visual distinction between primary dashboard data (like active Chat) vs secondary metrics (like historic visits).
- **Technical Exposure**: Exposes raw database IDs (e.g., "Patient ID: 3", "Request from Doctor ID: 2") rather than meaningful names or contexts.
- **Clunky Forms**: The document upload and access request forms use clunky native `<select>` and file inputs, lacking drag-and-drop or sophisticated multi-select.
- **Alerts**: Relying on `alert()` for errors and successes breaks user immersion.
- **Consent Workflow**: Approving/rejecting documents is confusing because the data presentation relies on raw arrays visually clumped together.

## 9. Features that can be improved WITHOUT backend changes
- **Full visual redesign** using modern frameworks (TailwindCSS, Framer Motion, Radix/Shadcn).
- **Toast Notifications**: Replace `alert()` with smooth toast notifications.
- **Skeleton Loaders**: Provide perceived performance improvements over blank screens.
- **Data Formatting**: Hide raw IDs by combining available metadata (e.g., "Dr. John Doe (Metro Health)" instead of "Doc 2, Hosp 1").
- **Drag and Drop**: Improve document upload UX with drag-and-drop file zones.
- **Interactive Consent**: Build clear, stepper-based or modal-based consent workflows with toggle switches instead of native dropdowns.
- **Mobile Responsiveness**: Re-engineer the layout grid for mobile-first views.

## 10. Features that require backend changes
- **Paging/Sorting/Filtering**: The current APIs return complete un-paginated arrays. Sophisticated data tables will require backend cursor/offset pagination if datasets grow.
- **Rich Media Previews**: Downloading raw blobs is supported, but secure PDF/Image thumbnail previews would require backend processing endpoints.
- **Profile Avatars**: Returning image URLs for doctors and patients requires database schema updates.

## 11. Recommended Implementation Order
1. **Design System & Layout**: Introduce Tailwind CSS. Update `Layout.tsx` for both apps with a modern sidebar, header, and global Toast/Alert system.
2. **Dashboard Overview UI**: Overhaul the high-visibility components (Triage Queue, Patient Details, Live Vitals).
3. **Complex Forms**: Refactor Upload Document and Request Access into polished, accessible forms.
4. **Consent & Security Views**: Overhaul the Access Requests, Access History, and Audit Logs into intuitive lists/tables.
