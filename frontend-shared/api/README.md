# Shared frontend API contracts

`contracts.ts` is the common TypeScript transport-contract surface for the patient, clinician and admin portals.

The FastAPI/Pydantic backend remains the authoritative runtime API implementation. These shared TypeScript types reduce portal drift and are compile-time contracts only; they never grant access, select consent, or carry trusted enforcement state.

When a backend response shape changes, update the shared contract first and migrate all consuming portals in the same pull request. Portal-specific view models may extend a shared transport type, but core auth/identity/visit/document/access/audit/consent/FHIR shapes should not be redefined independently.
