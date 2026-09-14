# P0 Release Blockers Completion

**Architecture decision:** Model A collocated PDP and PEP is authoritative.

## Acceptance checklist

- [x] Patient, clinician and administrator production builds compile.
- [x] Patient and clinician requests use their configured API clients.
- [x] Patient UI creates consents and immutable policy versions and performs
  lifecycle transitions.
- [x] Model A enforcement and its no-divergence rationale are documented.
- [x] Consent validity bounds are persisted as `timestamptz` values and enforced
  synchronously using a start-inclusive/end-exclusive interval.
- [x] Authorization audit rows populate request ID, correlation ID,
  authorization ID, enforcement point and enforcement state.
- [x] Authenticated browser workflow verified: login, request, approval,
  protected download, revocation, subsequent denial and correlated audit.

## Verification evidence

`ui-tests/tests/p0-secure-workflow.spec.ts` runs against the real React portals
and FastAPI application with deterministic test-only fixtures. It also exercises
the patient consent UI for creation, immutable versioning, suspension,
reactivation and revocation. The 2026-09-14 release run passed on Chromium at the
desktop breakpoint. Production Supabase migration remains a deployment action;
the configured external pooler was unreachable from the verification host.
