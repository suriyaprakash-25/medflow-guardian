# ADR-001 — External OIDC federation

**Status:** Accepted — implemented

**Date:** 2026-09-14

## Context

MedFlow now requires optional external OIDC federation for enterprise identity-provider interoperability while preserving the existing Model A security boundary. Federation is an authentication mechanism only: it must not become a source of MedFlow authorization roles, organization membership, consent, purpose, or protected-resource policy.

The existing authentication model already supports backend-issued sessions, rotating refresh cookies and MFA. The safest integration therefore terminates validated OIDC identity at the backend and issues the same MedFlow session artifacts used by native authentication.

## Decision

Implement allowlisted OIDC federation for **Auth0, Microsoft Entra ID and Okta** with the following constraints:

- Provider configuration is server-owned through explicit issuer/client/audience/discovery settings.
- Discovery issuer must exactly match the configured issuer.
- Discovery/JWKS endpoints must use HTTPS in production; redirects are not followed.
- ID tokens must use `RS256`, resolve an exact `kid` from provider JWKS, and pass issuer, audience, expiry, issued-at and nonce validation.
- Multi-audience tokens must identify the configured client through `azp`.
- State and nonce are generated server-side; state is bound to a short-lived signed HttpOnly cookie.
- Federation never auto-provisions a MedFlow account. A validated upstream subject may bind only to an already-existing active MedFlow user, using verified email/bootstrap identity rules on first binding.
- Once a subject is bound, `(provider, issuer, subject)` is the durable identity key; later email changes cannot silently rebind it.
- MedFlow roles, organization membership, consent and CAE authorization continue to come exclusively from MedFlow's authoritative database and `AuthorizationService`/`ConsentService`.
- If the MedFlow account requires MFA, the upstream token must demonstrate MFA in `amr`; federation does not bypass the local account's MFA policy.
- Successful OIDC authentication terminates into the existing MedFlow `Session`/refresh-token family and normal access JWT rather than creating a parallel token class.

## Consequences

- Auth0, Entra ID and Okta can authenticate existing MedFlow accounts without weakening Model A authorization.
- Provider discovery/JWKS/token failures fail closed.
- Private provider keys are never stored by MedFlow; only public JWKS are consumed for verification.
- Identity bindings are stored in `oidc_identities`, protected by the same Supabase public-schema default-deny posture as other application tables.
- Native password/MFA login remains available unless product policy disables it separately.
- Provider logout/front-channel single logout is not treated as authorization state; MedFlow session revocation remains authoritative for MedFlow access.
