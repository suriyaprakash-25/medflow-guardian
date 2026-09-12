**MedFlow Guardian — Complete Technical Context**

**1\. Project Identity**

**Project**

**MedFlow Guardian**

**Core idea**

MedFlow Guardian is a **healthcare data-flow governance and consent-enforcement platform** designed to solve a fundamental problem:

Healthcare data is fragmented across different healthcare parties and systems, while the ability to safely move the right information between those parties is inconsistent.

The fundamental principle is:

**Right Data → Right Party → Right Purpose → Right Time**

But MedFlow does not treat that as merely a UI/data-sharing concept.

The technical contribution is making that principle **continuously enforceable** through:

**patient consent → machine-readable policy → versioned consent state → authenticated request → contextual policy evaluation → authorization → enforcement → state verification → data release/prevention → audit**

That chain is the heart of the system.

**2\. Core Problem**

Healthcare information can exist across:

- patients
- doctors/practitioners
- hospitals
- clinics
- laboratories
- pharmacies
- other healthcare organizations
- distributed healthcare repositories

These systems can have different:

- identities
- repositories
- authorization mechanisms
- data representations
- interfaces
- organizational boundaries

Therefore, having healthcare data available somewhere does **not** automatically mean that it can safely be moved to another party.

The deeper problem is:

**How do we ensure that healthcare data reaches the appropriate party, for the appropriate purpose, at the appropriate time, while the patient's current consent remains continuously enforceable across distributed systems?**

A particularly important failure occurs when:

1. a user was previously authorized,
2. patient consent subsequently changes,
3. the authorization/enforcement layer still has an older state,
4. the old permission is accidentally honored.

MedFlow Guardian is designed around preventing this **stale authorization / stale consent enforcement problem**.

**3\. Core Innovation**

The project should **not** be described merely as:

"A healthcare consent management application."

That undersells it.

The important architecture is:

**Version-controlled consent + contextual authorization + continuous enforcement-state verification.**

A patient's consent is not treated as a permanent checkbox.

Instead, consent has a **state and version lifecycle**.

When consent changes, the system can create a new authoritative policy state.

An access request must be evaluated against the appropriate current state.

The enforcement point then verifies that the state it is enforcing corresponds to the authoritative state.

If the enforcement state is stale/divergent, access should not simply continue as though nothing changed.

**4\. High-Level Architecture**

The system can be viewed as six major layers.

┌───────────────────────────┐

│ CLIENT LAYER │

│ │

│ Patient Mobile │

│ Doctor Portal │

│ Admin Portal │

└─────────────┬─────────────┘

│

▼

┌───────────────────────────┐

│ IDENTITY LAYER │

│ │

│ OIDC / Auth0 │

│ JWT Access Tokens │

│ Identity Resolution │

└─────────────┬─────────────┘

│

▼

┌───────────────────────────┐

│ API LAYER │

│ │

│ NestJS REST API │

│ Request Context │

│ Authentication │

└─────────────┬─────────────┘

│

▼

┌─────────────────────────────────────────────┐

│ CONSENT / AUTHORIZATION CORE │

│ │

│ Consent Policy Management │

│ Consent Policy Store │

│ Policy Evaluation │

│ Authorization │

│ Access Requests │

│ Enforcement │

│ Enforcement-State Verification │

└──────────────────────┬──────────────────────┘

│

┌──────────────┴───────────────┐

▼ ▼

┌────────────────────┐ ┌────────────────────┐

│ Protected Resources│ │ Audit / Monitoring │

│ │ │ │

│ Medical Documents │ │ Audit Events │

│ Healthcare Data │ │ Decisions │

│ S3/Object Storage │ │ Correlation │

└────────────────────┘ └────────────────────┘

│

▼

┌────────────────────────────┐

│ PostgreSQL + Prisma │

│ │

│ Users / Identity │

│ Organizations │

│ Consent │

│ Authorization │

│ Access Requests │

│ Documents │

│ Audit │

│ Enforcement State │

└────────────────────────────┘

**5\. Client Applications**

There are three application surfaces.

**A. Patient Mobile**

Technology:

- React Native
- TypeScript

Purpose:

The patient is the central data owner/consent authority.

The patient-side experience is intended to provide capabilities around:

- patient identity
- consent management
- consent lifecycle
- viewing/controlling permissions
- access-related visibility
- healthcare-data sharing context

The mobile application communicates with the backend rather than directly deciding authorization.

**6\. Doctor Portal**

Technology:

- Next.js
- TypeScript

Purpose:

The doctor/practitioner is a **requester/consumer of healthcare information**.

The existing portal contains areas for:

- Dashboard
- Patient Discovery
- Access Requests
- Logout
- patient-related access workflows

The important architectural point:

The Doctor Portal does not independently decide whether a doctor is allowed to access a patient's healthcare data.

It sends the request to the backend.

The backend evaluates the authorization and consent conditions.

**7\. Admin Portal**

Technology:

- Next.js
- TypeScript

Purpose:

Administrative/organizational oversight.

Existing architecture includes functionality around:

- organizations
- audit
- administrative views
- organization-level management

Again, authorization must ultimately be enforced by the backend.

The admin UI is **not the security boundary**.

**8\. Backend**

Technology:

**NestJS + TypeScript**

The backend is the authoritative security layer.

Major modules already present in the project include:

AppModule

├── PrismaModule

├── PassportModule

├── AuthModule

├── IdentityModule

├── ConsentModule

├── AuthorizationModule

├── EnforcementModule

├── AuditModule

├── AccessRequestModule

├── DocumentModule

├── NotificationModule

└── ApiModule

This is important because the system is deliberately modular.

**9\. Database Architecture**

Database:

**PostgreSQL**

ORM:

**Prisma**

The database is responsible for persistent authoritative state.

The project has the migration chain:

00000000000000_init

↓

00000000000001_phase3

↓

00000000000002_phase7

↓

20260909000000_add_audit_action

The real PostgreSQL environment was successfully connected during validation and Prisma reported:

Database schema is up to date!

So the database layer is not merely mocked.

**10\. Identity Architecture**

MedFlow uses an external OIDC identity provider.

The current staging setup uses **Auth0**.

The architecture is intentionally based on standard OIDC/JWT concepts rather than making the authorization system itself dependent on a particular vendor.

The important values are:

Issuer

Audience

JWKS

JWT signature

The backend validates access tokens.

The backend then resolves the authenticated external identity to the MedFlow internal identity context.

Conceptually:

Auth0

│

│ JWT

▼

NestJS JWT Strategy

│

├── verify signature using JWKS

├── verify issuer

├── verify audience

│

▼

Identity Service

│

▼

MedFlow User / Organization / Role context

**11\. Identity Is Not Authorization**

This distinction is extremely important for explaining your project.

Auth0 answers:

**Who is this user?**

MedFlow answers:

**What is this user allowed to access, for what purpose, under which current consent state?**

So:

Authentication

↓

Who are you?

↓

Identity Context

↓

Authorization

↓

Are you allowed to do this?

↓

Consent + policy + context

↓

Enforcement

**12\. Consent Architecture**

Consent is a **first-class domain object**.

It is not just a boolean field such as:

consent = true

Instead, MedFlow models a lifecycle.

The consent states established in the design are:

DRAFT

ACTIVE

SUSPENDED

REVOKED

EXPIRED

SUPERSEDED

CANCELLED

This matters because healthcare consent can change over time.

For example:

ACTIVE

↓

SUSPENDED

↓

ACTIVE

or:

ACTIVE

↓

REVOKED

or:

ACTIVE

↓

EXPIRED

or:

ACTIVE

↓

SUPERSEDED

**13\. Consent Policy Version**

A key design decision is that consent policy versions are treated as **immutable versions**.

Conceptually:

Consent

│

├── Policy Version 1

│

├── Policy Version 2

│

└── Policy Version 3

Rather than silently modifying history, the system can represent a new policy state/version.

This gives the system historical traceability.

**14\. Consent State ID**

A particularly important technical element is:

consentStateId

Authorization references the relevant consent state.

Therefore an authorization isn't merely:

Doctor X can access Patient Y

It is closer to:

Doctor X

-

Patient Y

-

resource

-

operation

-

consentStateId

That is important because the authorization can be associated with the **specific consent state that justified it**.

**15\. Authorization**

Authorization is separate from consent.

Consent says what the patient has permitted under a policy.

Authorization determines whether a particular requester is permitted to perform an operation under that policy/context.

Authorization states:

ACTIVE

REVOKED

EXPIRED

SUPERSEDED

And operations include:

READ

DOWNLOAD

SHARE

**16\. Access Request**

There is also a separate access-request lifecycle.

States:

PENDING

APPROVED

REJECTED

EXPIRED

CANCELLED

So the flow can be:

Doctor needs patient data

↓

Access Request

↓

Patient/authorized workflow

↓

Approved / rejected

↓

Authorization

↓

Policy evaluation

↓

Enforcement

This is different from simply allowing every authenticated doctor to read every patient.

**17\. Request Context**

Every protected request needs context.

Conceptually:

Requester

Recipient

Patient

Organization

Resource

Purpose

Operation

Time

The request context is used by the policy decision process.

For example:

Requester:

Doctor A

Patient:

Patient B

Resource:

Lab Report

Operation:

READ

Purpose:

Treatment

Time:

Current time

Organization:

Hospital X

The policy engine evaluates this context against the consent policy.

**18\. Policy Decision**

The policy decision component evaluates whether the request satisfies the consent/policy conditions.

Conceptually:

Request Context

-

Current Consent Policy

-

Authorization

-

Identity/Organization context

↓

Policy Decision

↓

ALLOW / DENY

This is where the **Right Data / Right Party / Right Purpose / Right Time** principle becomes machine-enforceable.

**19\. Enforcement**

A policy decision alone isn't sufficient.

The system needs an enforcement component that actually prevents or allows access.

Therefore:

Policy Decision

↓

Enforcement Point

↓

Release resource

OR

Block resource

This distinction is critical.

A system that merely says:

"The user should not access this"

but still returns the medical document is not secure.

MedFlow's architecture puts enforcement between the decision and protected resource release.

**20\. Enforcement State**

This is one of the most important pieces of the project.

The system doesn't assume that the enforcement component is automatically synchronized forever.

It maintains enforcement state.

Conceptually:

Authoritative Consent State

│

│

▼

ConsentStateId = 42

│

│

▼

Enforcement Component

│

▼

Enforced ConsentStateId = 42

Everything is aligned.

But imagine:

Authoritative:

ConsentStateId = 43

Enforcement:

ConsentStateId = 42

Now there is a **state divergence**.

The enforcement layer is stale.

MedFlow's architecture is designed to detect this rather than blindly trusting the stale state.

**21\. The Critical Security Chain**

This is the heart of MedFlow Guardian.

PATIENT CONSENT

│

▼

Consent Policy Version

│

▼

Authoritative State

│

▼

consentStateId = X

│

│

REQUEST ───────────────┤

▼

Request Context

│

▼

Policy Evaluation

│

┌────────┴────────┐

│ │

ALLOW DENY

│

▼

Authorization

│

▼

Enforcement Point

│

▼

Verify enforcement state

│

┌─────┴─────┐

│ │

MATCH DIVERGENCE

│ │

▼ ▼

RELEASE RE-EVALUATE /

DATA BLOCK / SYNC

│

▼

AUDIT

That is the architecture you should understand extremely well for your presentation.

**22\. Document Protection**

The Document module protects medical documents.

The system has functionality around:

- listing documents
- controlled access
- signed download URLs
- authorization-aware document access

The important principle:

The frontend should never simply receive unrestricted storage credentials and fetch medical files directly.

The backend should first evaluate authorization/enforcement and then provide controlled access to the resource.

The storage layer is designed around S3-compatible object storage.

**23\. Storage Architecture**

Conceptually:

Client

│

▼

NestJS API

│

├── Authentication

├── Authorization

├── Consent

├── Enforcement

│

▼

Document Service

│

▼

S3-compatible object storage

The database stores metadata/reference information such as storage keys rather than putting large medical files directly into normal relational rows.

**24\. Audit Architecture**

Audit is a first-class component.

An audit event can capture information such as:

actorId

patient/resource context

organization

resourceId

requestId

authorizationId

consentStateId

enforcementPoint

correlationId

action

outcome

timestamp

This allows you to answer:

Who attempted the access?

What resource was involved?

Under which consent state?

Under which authorization?

Where was it enforced?

Was it allowed or denied?

When did it happen?

This is much stronger than a simple application log saying:

Doctor accessed document.

**25\. Organization Isolation**

Healthcare data cannot simply be globally accessible.

The backend maintains organization context.

The important security principle is:

**Organization isolation is enforced server-side.**

It must not depend on a frontend hiding records.

Therefore an attacker cannot legitimately obtain another organization's records simply by modifying a patient ID or organization ID in a request.

**26\. API Structure**

The backend currently exposes API areas including:

/api/v1/consents

/api/v1/access-requests

/api/v1/documents

/api/v1/identity

/api/v1/admin

/api/v1/patients

Examples from the running backend:

GET /api/v1/identity/me

GET /api/v1/consents

GET /api/v1/consents/:id

POST /api/v1/consents/draft

PUT /api/v1/consents/:id/state

PUT /api/v1/consents/:id/modify

POST /api/v1/access-requests

PUT /api/v1/access-requests/:id/status

GET /api/v1/access-requests

GET /api/v1/documents

GET /api/v1/documents/:id/access

GET /api/v1/patients/me

GET /api/v1/patients/search

GET /api/v1/admin/audit

GET /api/v1/admin/organizations

These routes were observed directly when the NestJS backend started.

**27\. Complete End-to-End Workflow**

Now the most important part.

**Scenario: Doctor needs access to patient data**

**Step 1 — Authentication**

Doctor opens the Doctor Portal.

Doctor Portal

↓

OIDC Provider

↓

Login

↓

JWT Access Token

**Step 2 — API Request**

The portal sends the authenticated request to the backend.

Doctor

↓

Authorization header

↓

NestJS

**Step 3 — JWT Validation**

Backend verifies:

signature

issuer

audience

token validity

JWKS is used to obtain the public signing keys.

**Step 4 — Identity Resolution**

The token identifies the external user.

MedFlow resolves:

OIDC subject

↓

Internal User

↓

Role

Organization

Identity Context

**Step 5 — Patient Discovery / Access Request**

Doctor identifies a patient and requests the necessary healthcare information.

Doctor

↓

Patient

↓

Resource

↓

Purpose

↓

Operation

**Step 6 — Access Request**

If the workflow requires explicit access approval:

PENDING

↓

patient/authorized decision

↓

APPROVED

or:

PENDING

↓

REJECTED

**Step 7 — Consent Evaluation**

The backend retrieves the relevant consent policy/state.

Example:

ConsentStateId = 17

State = ACTIVE

**Step 8 — Context Evaluation**

The system evaluates:

WHO?

Doctor

FOR WHOM?

Patient

WHAT?

Medical document

WHY?

Treatment

WHICH OPERATION?

READ

WHEN?

Current time

UNDER WHICH ORGANIZATION?

Hospital

**Step 9 — Authorization**

The system verifies that the authorization corresponds to the required consent state and current conditions.

**Step 10 — Enforcement**

The enforcement component checks the actual state it is enforcing.

If:

Authoritative consentStateId = 17

Enforcement consentStateId = 17

the state is aligned.

**Step 11 — Resource Release**

If all conditions are satisfied:

ALLOW

↓

Document Service

↓

Controlled document access

Otherwise:

DENY

↓

No protected resource released

**Step 12 — Audit**

The decision is recorded.

Doctor

Patient

Resource

Authorization

ConsentStateId

Decision

Timestamp

Correlation ID

**28\. What Happens When Patient Revokes Consent?**

This is the strongest demonstration of the system.

Suppose:

ConsentStateId = 17

State = ACTIVE

Doctor has valid authorization against state 17.

Patient then revokes consent.

The authoritative state becomes:

ConsentStateId = 18

State = REVOKED

The old state should no longer be treated as current.

If the enforcement layer still has:

17

while the authoritative state is:

18

the system identifies divergence.

The stale permission should not simply be honored.

The intended result is:

Doctor request

↓

Current consent = REVOKED

↓

DENY

↓

No document release

↓

Audit

This is one of the most important scenarios for your demonstration.

**29\. Consent Lifecycle Example**

A simple demonstration could be:

DRAFT

↓

ACTIVE

↓

SUSPENDED

↓

ACTIVE

↓

REVOKED

Or:

ACTIVE

↓

EXPIRED

Each state has different authorization implications.

**30\. Interoperability**

The architecture is intended to work with heterogeneous healthcare environments rather than requiring every healthcare organization to replace its existing data repository.

The design includes interoperability considerations such as standards-based consent representations, including **HL7 FHIR Consent** transformation into the internal policy model.

Conceptually:

FHIR Consent

↓

Consent Transformation

↓

MedFlow Policy Model

↓

Versioned Consent State

↓

Authorization / Enforcement

This allows MedFlow's internal enforcement model to remain consistent while interfacing with external healthcare systems.

**Important:** don't claim that a complete production FHIR interoperability network is currently implemented unless you actually verify that code. The architecture supports this direction, but that is different from saying the complete interoperability integration is finished.

**31\. Technology Stack**

**Frontend**

**Patient**

React Native

TypeScript

**Doctor**

Next.js

TypeScript

**Admin**

Next.js

TypeScript

**Backend**

NestJS

TypeScript

REST API

Passport / JWT

JWKS

OIDC

**Database**

PostgreSQL

Prisma ORM

**Supporting infrastructure**

Redis

S3-compatible object storage

OIDC identity provider

**Monorepo**

pnpm

Turborepo

**32\. Repository Architecture**

At a high level:

medflow/

│

├── apps/

│ ├── patient-mobile/

│ ├── doctor-portal/

│ └── admin-portal/

│

├── backend/

│ ├── prisma/

│ │ ├── schema.prisma

│ │ └── migrations/

│ │

│ └── src/

│ ├── auth/

│ ├── identity/

│ ├── consent/

│ ├── authorization/

│ ├── enforcement/

│ ├── access-request/

│ ├── document/

│ ├── audit/

│ ├── notification/

│ └── api/

│

├── packages/

│ ├── api-contracts/

│ ├── shared-types/

│ ├── validation/

│ └── shared-config/

│

├── infrastructure/

│ └── docker/

│

└── docs/

The exact package names may vary slightly by current repository state, but this is the established architectural structure.

**33\. Shared Contracts**

The frontend and backend share contracts/types rather than independently inventing API structures.

Conceptually:

Backend

│

├── API contract

│

▼

Shared Contracts

▲

│

├── Doctor Portal

├── Admin Portal

└── Patient Mobile

This reduces frontend/backend mismatch.

**34\. Security Model**

The security model follows several fundamental principles.

**Backend authoritative**

Frontend decisions are never sufficient.

**Least privilege**

Users should receive only the access required by the current policy.

**Consent-aware authorization**

Authorization is tied to consent state.

**Continuous enforcement**

Current state matters rather than relying indefinitely on historical approval.

**Organization isolation**

Tenant/organization boundaries are enforced on the server.

**Auditability**

Important access decisions are recorded.

**No frontend secrets**

OIDC client secrets must not be embedded into browser/mobile applications.

**Protected resources**

Documents are released only after backend authorization/enforcement.

**35\. High-Level Design vs Low-Level Design**

This distinction will help you in your presentation.

**High-Level Design**

The HLD answers:

**What major components exist and how do they communicate?**

Patient App

│

Doctor Portal

│

Admin Portal

│

▼

API Gateway / NestJS

│

┌───┼─────────────────────────────┐

│ │ │ │ │ │

▼ ▼ ▼ ▼ ▼ ▼

Auth Consent Authorization Enforcement Audit

│ │ │ │ │

└─────┴────────┴─────────┴────────┘

│

▼

PostgreSQL

│

▼

Document Storage

**36\. Low-Level Design**

The LLD answers:

**What happens inside each request and how are individual objects/states related?**

For a protected document request:

HTTP Request

↓

JWT Guard

↓

JWT Strategy

↓

Identity Resolution

↓

Request Context Construction

↓

Patient/Resource lookup

↓

Consent State lookup

↓

Authorization lookup

↓

Policy evaluation

↓

Enforcement State lookup

↓

State consistency verification

↓

ALLOW / DENY

↓

Document access / block

↓

Audit Event

**37\. Important Data Relationships**

Conceptually:

Organization

│

├── Users

│

├── Patients

│

└── Resources

Patient

│

└── Consent

│

└── Consent Policy Versions

│

└── Consent States

│

└── consentStateId

Authorization

│

├── requester

├── recipient

├── patient/resource context

└── consentStateId

Access Request

│

├── requester

├── recipient

└── status

Enforcement State

│

└── enforced consent state

Audit Event

│

├── actor

├── resource

├── request

├── authorization

├── consent state

├── enforcement point

└── outcome

**38\. Critical Security Scenario Matrix**

For your project demonstration, these are the scenarios that matter most:

| **Scenario**                  | **Expected result**               |
| ----------------------------- | --------------------------------- |
| No authentication             | ❌ Denied                         |
| Valid authentication          | ✅ Identity resolved              |
| Valid consent + authorization | ✅ Access                         |
| Consent revoked               | ❌ Access denied                  |
| Consent expired               | ❌ Access denied                  |
| Consent suspended             | ❌/restricted according to policy |
| Old consent state             | ❌ Must not bypass current state  |
| Enforcement state diverges    | ❌ Prevent/re-evaluate            |
| Wrong patient                 | ❌ Denied                         |
| Wrong organization            | ❌ Denied                         |
| Unauthorized operation        | ❌ Denied                         |
| Valid document access         | ✅ Controlled release             |
| Access decision               | 📝 Audited                        |

These are much more meaningful than simply showing that a dashboard loads.

**39\. What We Have Actually Verified**

This is important because you specifically told me not to hallucinate.

During the actual staging work, we verified:

**PostgreSQL**

✅ Running in Docker.

**Database connection**

✅ Host connection succeeded.

**Prisma**

✅ Prisma 5.22.0 installed.

**Migrations**

✅ All four migrations reported applied.

**NestJS**

✅ Backend compiled with zero TypeScript errors.

**Backend startup**

✅ NestJS successfully started.

**API**

✅ GET / returned:

Hello World!

**Authentication protection**

✅ Unauthenticated:

GET /api/v1/identity/me

returned:

401 Unauthorized

with:

{

"message": "Missing or invalid authentication token",

"error": "Unauthorized",

"statusCode": 401

}

That is a good security result.

**Auth0**

✅ Auth0 tenant created.

✅ MedFlow Guardian application created.

✅ MedFlow Guardian API created.

✅ OIDC discovery endpoint verified.

**Web applications**

✅ Doctor portal builds/runs.

✅ Admin portal builds/runs.

**Routing**

✅ Default Next.js root-page problem was identified.

✅ Root routes were changed to redirect to the actual dashboard.

**40\. What Is NOT Yet Fully Proven**

This is equally important.

We should **not** currently claim that the entire end-to-end workflow has been proven in a real runtime environment.

The remaining validation is:

Real Auth0 login

↓

Real access token

↓

Frontend

↓

Backend

↓

Identity resolution

↓

Consent

↓

Authorization

↓

Enforcement

↓

Document access

↓

Revocation

↓

Deny

↓

Audit

The architecture supports this.

A significant amount of the implementation exists.

But the complete chain needs to be runtime-tested before saying:

"Every feature is fully working end-to-end."

That's why our current phase should be **functionality validation**, not UI redesign.

**41\. Current Project Status**

The most honest status is:

**Foundation**

**Strong / working**

**Backend**

**Implemented and successfully starts**

**Database**

**Working**

**Core domain architecture**

**Implemented**

**Authentication infrastructure**

**Configured**

**Portals**

**Running**

**Complete E2E authentication + business workflow**

**Still needs final runtime verification**

**UI**

**Needs major reconstruction**

And that last part matches what you just showed me: the current UI is functional scaffolding, **not the final presentation-quality UI you want**.

**42\. The Complete MedFlow Story**

If you need to explain the project in front of a panel, don't start with:

"We used React Native, Next.js, NestJS, PostgreSQL..."

Start with the problem.

**Problem**

Healthcare data is fragmented across organizations and systems, making controlled movement of information difficult.

**Core requirement**

Healthcare information must reach:

**the right party, with the right data, for the right purpose, at the right time.**

**Security challenge**

Patient permissions can change over time, and distributed authorization/enforcement components can become stale.

**MedFlow approach**

MedFlow Guardian converts patient consent into **machine-evaluable, versioned policy state**.

**Decision**

Every protected request is evaluated using its context and the relevant consent/authorization state.

**Enforcement**

The decision is enforced before protected healthcare data is released.

**Consistency**

The enforcement state is checked against the authoritative consent state.

**Accountability**

The access decision is auditable.

**Result**

Fragmented Healthcare Data

↓

MedFlow Guardian

↓

Context + Consent + Authorization

↓

Continuous Enforcement

↓

Controlled Data Flow

↓

Right Data

Right Party

Right Purpose

Right Time

**43\. One Diagram You Should Put in Your Presentation**

I strongly recommend this as your **main architecture slide**:

MEDFLOW GUARDIAN

┌──────────────┐ ┌──────────────┐ ┌──────────────┐

│ PATIENT │ │ DOCTOR │ │ ADMIN │

│ React Native │ │ Next.js Web │ │ Next.js Web │

└──────┬───────┘ └──────┬───────┘ └──────┬───────┘

│ │ │

└────────────────────┼────────────────────┘

▼

┌─────────────────┐

│ OIDC / JWT │

│ Identity │

└────────┬────────┘

▼

┌─────────────────┐

│ NestJS API │

└────────┬────────┘

▼

┌────────────────────────────┐

│ REQUEST CONTEXT │

│ User • Patient • Resource │

│ Purpose • Operation • Time │

└─────────────┬──────────────┘

▼

┌────────────────────────────┐

│ POLICY EVALUATION │

│ │

│ Consent + Authorization │

└─────────────┬──────────────┘

▼

┌────────────────────────────┐

│ ENFORCEMENT │

│ │

│ Current State Verification │

└─────────────┬──────────────┘

│

┌────────┴────────┐

▼ ▼

ALLOW DENY

│ │

▼ ▼

Protected Data No Release

│

└────────┬────────┘

▼

┌───────────┐

│ AUDIT │

└───────────┘

RIGHT DATA

↓

RIGHT PARTY

↓

RIGHT PURPOSE

↓

RIGHT TIME

That diagram captures the **actual essence of MedFlow Guardian** far better than a generic "three-tier architecture" diagram.

**The most important distinction**

Your project has **two layers of value**:

**Product value**

**Make healthcare data flow safely between the appropriate parties despite fragmented healthcare systems.**

**Technical innovation**

**Continuously enforce versioned patient-consent policy at the access/enforcement layer and detect divergence between authoritative consent state and the state actually being enforced.**

That combination is what makes MedFlow Guardian more than a basic healthcare portal or CRUD consent application.