# MedFlow Guardian Actual Architecture

## Backend Stack
- **Framework**: FastAPI (Python 3.11)
- **Database**: Supabase PostgreSQL
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Storage**: Supabase Storage via `storage3` Python client
- **Authentication**: Custom local JWT implementation (`jose`)
- **Real-Time**: FastAPI WebSockets

## Frontend Stack
- **Patient App**: React 18, Vite, TypeScript, Tailwind CSS v4, React Router
- **Doctor Portal**: React 18, Vite, TypeScript, Tailwind CSS v4, React Router

## Implemented Flows
- **Authentication**: Users log in via `/api/auth/login`, receive a standard JWT. The frontend stores this token in `localStorage` and appends it to requests.
- **Hospital Isolation**: `HospitalStaff` entities bind `User`s to `Hospital`s. Some isolation exists in explicit queries, but there is no generic tenant isolation middleware.
- **Access Requests**: Doctors can request access to specific documents via `DocumentAccessRequest`. Patients can grant this via `DocumentAccessGrant`.
- **Documents**: Uploaded directly to a private Supabase bucket. Access is mediated by backend signed-url generation.
- **WebSockets**: Allows broadcasting live updates (e.g., Triage, New Messages). Connection relies on query param `?token=`.

## Deviations from Design Document
- **No Consent Lifecycle**: There is no overarching `Consent` policy versioning or `consentStateId` verification in the request lifecycle.
- **No Stale Enforcement Checks**: The backend evaluates permissions directly against `DocumentAccessGrant`.
- **No OIDC**: Auth0/OIDC is not integrated. Identity resolution is entirely internal.
- **Tech Stack**: Uses FastAPI instead of NestJS; uses SQLAlchemy instead of Prisma.
