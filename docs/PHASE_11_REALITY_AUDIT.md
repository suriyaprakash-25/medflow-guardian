# Phase 11 Reality Audit

**Date:** 2026-09-11
**Objective:** Audit the current authentication and identity architecture.

## 1. Current State of Authentication Models & Configuration
- **User Model**: (`app/models/user.py`) Exists with `email`, `hashed_password`, `role`, and `is_active`.
- **JWT Secret**: Configured via `SECRET_KEY` in environment. Algorithm is `HS256`.
- **JWT Lifetime**: `ACCESS_TOKEN_EXPIRE_MINUTES` defaults to 7 days.
- **Refresh Tokens**: **MISSING**. No refresh token architecture exists.
- **Password Hashing**: `bcrypt` via `passlib`. Securely implemented in `app/core/security.py`.
- **MFA**: **MISSING**. No TOTP or SMS MFA infrastructure exists.

## 2. API Endpoints
- **POST `/api/auth/login`**: Exists. Uses `OAuth2PasswordRequestForm`. Returns a single long-lived access token.
- **GET `/api/auth/me`**: Exists. Returns the user profile and current organization memberships by querying the database in real-time.
- **POST `/api/auth/logout`**: **MISSING**.
- **POST `/api/auth/logout-all`**: **MISSING**.
- **POST `/api/auth/refresh`**: **MISSING**.
- **POST `/api/auth/change-password`**: **MISSING**.
- **POST `/api/auth/mfa/*`**: **MISSING**.

## 3. JWT Architecture
- **Algorithm**: `HS256` (Verified)
- **Claims Issued**: `sub` (email), `exp`. (Verified)
- **Claims Missing**: `jti` (JWT ID), `iss` (Issuer), `aud` (Audience), `token_type`, session ID.
- **Storage Strategy**: Both Patient App and Doctor Portal store the long-lived access token in `localStorage`.

## 4. Session & Invalidation Semantics
- **Session Revocation**: **PARTIALLY IMPLEMENTED**. The application relies heavily on `get_current_active_user`, which queries the live `users` table for `is_active`. If a user is deactivated, the next API request fails.
- **Role/Membership Change**: **VERIFIED**. The Authorization Engine evaluates membership live from `HospitalStaff`. Stale JWTs do not grant ongoing access if membership changes.
- **Access Token Revocation**: **MISSING**. Short-term token revocation is not implemented, relying purely on database state checks on every request.

## 5. Front-End Handling
- **Patient App / Doctor Portal**: Axios interceptor retrieves token from `localStorage`.
- **Refresh Flow**: **MISSING**. If a 401 is received, it blindly redirects to `/login` and wipes the token. No queue or refresh logic exists.

## Conclusion
The backend successfully maintains a strong security boundary because the Authorization Engine does not blindly trust JWT claims—it queries the database. However, the Authentication layer itself is fragile. It lacks MFA, uses insecure long-lived access tokens, and has no mechanism to cryptographically rotate or revoke a user's session without merely disabling their entire account.
