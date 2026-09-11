# Phase 11 Authentication Threat Model

This document maps the primary threats to the current Authentication Architecture and how they will be mitigated in Phase 11.

### 1. Stolen Access Token (via XSS or Network Intercept)
- **Current Control**: Token stored in `localStorage` (vulnerable to XSS). Lifespan is 7 days.
- **Gap**: If stolen, an attacker has 7 days of uninterrupted access.
- **Mitigation**: Reduce Access Token lifetime to 15 minutes. Store Refresh Token in an `HttpOnly` secure cookie.
- **Verification**: Ensure the API correctly rejects access tokens older than 15 minutes.

### 2. Stolen Refresh Token & Replayed Refresh Token
- **Current Control**: N/A (Refresh tokens don't exist).
- **Gap**: Introduction of refresh tokens creates a new theft target.
- **Mitigation**: Refresh token rotation. When a refresh token is used, a new one is issued. If a token is reused (replayed), the system detects the anomaly and revokes the entire `token_family` (or session).
- **Verification**: Replaying a used refresh token must result in an immediate 401 and session termination.

### 3. Stale JWT after Account Deactivation or Role Downgrade
- **Current Control**: `get_current_active_user` and `AuthorizationService` check live database state.
- **Gap**: The current system actually handles this well at the Authorization layer, but the Authentication session (JWT) technically remains cryptographically valid.
- **Mitigation**: Access token lifetimes are drastically shortened. The refresh endpoint checks `is_active` and current roles.
- **Verification**: Removing a role or deactivating a user instantly blocks new access tokens from being issued, and existing ones expire within minutes.

### 4. Privilege Escalation (Organization Boundary Manipulation)
- **Current Control**: Database foreign key constraints and `HospitalStaff` queries strictly associate users to hospitals.
- **Gap**: No immediate gap, but authentication logic must not bypass the CAE.
- **Mitigation**: Ensure JWTs do not contain embedded "organization permissions" that the frontend might try to authoritative rely on.
- **Verification**: An Admin of Hospital A cannot perform Admin actions in Hospital B.

### 5. Brute Force Login & Password Compromise
- **Current Control**: `bcrypt` hashing exists. Rate limiting is missing.
- **Gap**: Attackers can brute-force passwords indefinitely or use credential stuffing.
- **Mitigation**: Implement MFA (TOTP) for Privileged roles (Admin, Doctor) to neutralize stolen passwords. (Rate limiting is deferred to Phase 12 WAF).
- **Verification**: Doctor accounts cannot log in with just a password once MFA is enabled.

### 6. WebSocket Authentication Token Leakage
- **Current Control**: JWT is sent over WebSockets.
- **Gap**: Tokens might leak in access logs if sent via query parameters (e.g., `?token=...`).
- **Mitigation**: Tokens are short-lived. WebSockets will re-evaluate state dynamically.
- **Verification**: WebSocket connection should be rejected if the token is invalid or expired.
