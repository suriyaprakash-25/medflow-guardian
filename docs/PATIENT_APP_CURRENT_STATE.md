# Patient App Current State Audit

## 1. Existing Screens & Routes
- `/login` - Basic login form.
- `/dashboard` (`DashboardView.tsx`) - Contains Triage Request Form, Vitals Monitor (with simulation toggle), and Chat interface.
- `/documents` (`Documents.tsx`) - Lists documents with hospital/type filtering and download actions.
- `/access-requests` (`AccessRequests.tsx`) - Lists pending requests. Allows approval (with duration select) or rejection.
- `/access-history` (`AccessHistory.tsx`) - History of document access grants.
- `/notifications` (`Notifications.tsx`) - List of system notifications with "mark read" actions.
- `/profile` (`Profile.tsx`) - Contains profile data, visit history, triage history, and security audit logs.

## 2. Existing API Calls
- `GET /api/visits/patient` - Fetches hospital visits/doctors.
- `GET /api/triage/patient` - Fetches triage history.
- `GET /api/messages/{doctorId}` - Fetches chat messages.
- `GET /api/readings/patient` - Fetches vital readings.
- `GET /api/documents/patient` - Fetches patient medical documents.
- `GET /api/access-requests/patient` - Fetches pending access requests.
- `GET /api/access-grants/patient` - Fetches active/historical grants.
- `GET /api/notifications` - Fetches notifications.
- `GET /api/audit/patient` - Fetches audit logs.
- `POST /api/readings` - Posts simulated vital readings.
- `POST /api/triage/` - Submits a new triage request.
- `POST /api/messages` - Sends a chat message.
- `GET /api/documents/{id}/download` - Downloads a document.
- `POST /api/access-requests/{id}/approve` - Approves access request.
- `POST /api/access-requests/{id}/reject` - Rejects access request.
- `POST /api/access-grants/{id}/revoke` - Revokes an active grant.
- `POST /api/notifications/{id}/read` - Marks single notification as read.
- `POST /api/notifications/read-all` - Marks all notifications as read.

## 3. Existing WebSocket Behavior
- Connects to `ws://localhost:8080/ws?token=${token}`.
- Handles real-time events: `message`, `triage_update`, `access_request_created`, `access_request_approved`, `access_request_rejected`, `access_revoked`, `document_uploaded`, `notification_created`.
- Triggers data refetching upon receiving events.
- Automatically reconnects on disconnect with a 3000ms delay.

## 4. Existing Reusable Components
- Phase 1 introduced shared UI components in `frontend-shared/ui`: `Button`, `Card`, `Badge`, `ConfirmModal`, `EmptyState`, `Input`, `Select`, `Skeleton`.
- Global layouts are handled in `Layout.tsx` which provides standard sidebars and headers.

## 5. Existing Styling Approach
- Uses **Tailwind CSS v4** configured globally via `frontend-shared/global.css`.
- Global CSS uses `@theme` variables leveraging HSL color formats (`--primary`, `--background`, etc.).
- Basic legacy CSS classes (`.card`, `.btn-primary`) are still present in `global.css` for backward compatibility but need to be phased out in favor of the new shared components.

## 6. Existing Supported Functionality
- Viewing documents, requesting triage, live-chat with doctors, viewing notifications, managing consent, live simulated vitals monitoring, audit log viewing.

## 7. Existing Unsupported Functionality
- Advanced profile editing, document uploads from the patient side (currently uploaded by hospital/doctor), and complex multi-doctor chat views.

## 8. Current UX Problems
- **Dashboard**: Monolithic and mixes distinct tasks (Triage, Vitals, Chat).
- **Technical Jargon**: UI exposes raw database IDs (e.g., `Doctor ID: 3`, `Hospital ID: 2` in AccessRequests).
- **Vitals Simulation**: Development tools (simulate vitals button) are mixed into the primary patient UX.
- **Visual Hierarchy**: Cards lack proper distinction, spacing is generic, and there are no cohesive animations or polished empty/loading states.
- **Access Requests**: The approval flow lacks clear confirmation modals describing the implications of granting access.

## 9. Refactoring Candidates
- All page views (`DashboardView.tsx`, `Documents.tsx`, `AccessRequests.tsx`, `AccessHistory.tsx`, `Profile.tsx`, `Notifications.tsx`) are prime candidates for complete visual rewrites using the new `@shared/ui` components without altering the underlying logic defined in `Layout.tsx`.
