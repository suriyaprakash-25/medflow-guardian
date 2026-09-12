# Phase B1 Admin Reality Audit

This document inventories the actual, current state of the Admin Platform in MedFlow Guardian.

## A. Existing Admin API Endpoints
- `GET /api/admin/dashboard` - **PARTIALLY IMPLEMENTED** (Returns total_staff, active_consents, total_patients, recent_activity. Authorization is checked using `Operation.VIEW_DASHBOARD`/`MANAGE_STAFF`.)
- `GET /api/admin/staff` - **PARTIALLY IMPLEMENTED** (Lists staff for a given hospital. Authorization checked.)
- `GET /api/admin/audit` - **PARTIALLY IMPLEMENTED** (Lists audit logs. Authorization checked.)
- `POST /api/admin/staff` - **MISSING**
- `PUT /api/admin/staff/{id}` - **MISSING**
- `DELETE /api/admin/staff/{id}` - **MISSING**
- `POST /api/admin/organization` - **MISSING**
- `PUT /api/admin/organization/{id}` - **MISSING**

## B. Existing Admin Models
- `User`: Has `role` ("doctor", "patient"). Hardcoded "platform_admin" checks exist in the API but no dedicated role is officially mapped in model documentation. - **IMPLEMENTED**
- `Hospital`: Represents an organization. - **IMPLEMENTED**
- `HospitalStaff`: Maps a `User` to a `Hospital` with a `role` ("admin", "doctor", "staff"). - **IMPLEMENTED**
- `AuditLog`: Captures actor, org, patient, operation, decision, etc. - **IMPLEMENTED**

## C. Existing Admin Authorization Rules
- `Operation.MANAGE_STAFF`, `Operation.VIEW_AUDIT`, `Operation.VIEW_DASHBOARD` are defined in the CAE (`AuthorizationService`). - **IMPLEMENTED**
- The CAE correctly handles basic hospital context. - **IMPLEMENTED**
- However, full organization provisioning and complex role grants are not wired. - **MISSING**

## D. Existing Admin Frontend Routes
- `/` (Dashboard) - **IMPLEMENTED**
- `/staff` - **PARTIALLY IMPLEMENTED** (Read-only list. Search works. Provisioning is disabled/faked.)
- `/audit` - **PARTIALLY IMPLEMENTED** (Read-only list. UI relies on existing `GET /audit` endpoint.)
- `/settings` - **IMPLEMENTED**
- `/organizations` - **MISSING**

## E. Existing Admin Frontend Components
- `Layout.tsx` (Sidebar, Navbar) - **IMPLEMENTED**
- Loading/Empty States - **PARTIALLY IMPLEMENTED**
- Organization selector - **MISSING**
- Role mutation dialogs - **MISSING**

## F. Existing API Client Behavior
- Standard JWT bearer token auth in `lib/api.ts`. - **IMPLEMENTED**
- Centralized error handling. - **IMPLEMENTED**
- No client-enforcement bypasses found in the admin client. - **IMPLEMENTED**

## G. Existing Postman Collections
- `MedFlow-Security-Core.postman_collection.json` has basic auth and document workflows, but Admin specific endpoints are heavily lacking. - **MISSING**

## H. Existing Automated Admin Tests
- `test_admin_auth.py` exists but only covers basic access denial and maybe simple metrics/listing. - **PARTIALLY IMPLEMENTED**

## I. Existing Database Migrations
- `alembic` setup exists, tables are present. Provisioning logic for the very first platform admin usually happens in a seed script, not documented here. - **IMPLEMENTED**

## J. Existing Audit Capabilities
- `AuditLog` captures most fields required by the architecture (actor, org, resource, decision, context). Append-only nature is enforced by API logic, but cryptographic tamper-proofing is not present. - **PARTIALLY IMPLEMENTED**
