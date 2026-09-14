# ADR-001 — External OIDC federation

**Status:** Accepted — not implemented

**Date:** 2026-09-14

## Context

P1 asked for external OIDC integration only if federation remains a product requirement. The current MedFlow repository has no product requirement, configuration surface, identity-provider dependency, SSO UI, tenant federation model, or deployment secret set that requires OIDC.

The existing authentication model already supports backend-issued sessions, refresh-cookie rotation and MFA while keeping authorization inside the collocated Model A PDP+PEP boundary.

## Decision

Do **not** add external OIDC federation in this release.

Adding an identity provider without a product requirement would add callback/origin configuration, token-validation logic, key rotation, claim mapping and account-linking risk without delivering a required workflow.

## Consequences

- Current password/MFA authentication remains authoritative for this release.
- Authorization continues to derive roles/memberships from MedFlow's own database, not untrusted external claims.
- If federation becomes a product requirement, it must be introduced through a dedicated design/security phase covering issuer allowlisting, PKCE/state/nonce, JWKS rotation, claim mapping, account linking, logout/session revocation and tenant isolation.
