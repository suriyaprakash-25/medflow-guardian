# Penetration Test Scope

**Date:** 2026-09-11

This document defines the scope and focus areas for the upcoming MedFlow Guardian penetration test.

## 1. In-Scope Environments
- **Target**: `staging.medflow.com` (or equivalent URL).
- **Credentials**: The testing team will be provided with valid credentials for:
  - 2 Patient accounts
  - 2 Doctor accounts (in different Hospitals)
  - 1 Organization Admin
  - 1 Platform Admin

## 2. Out-of-Scope
- Production environment (`app.medflow.com`).
- Load/stress testing (DDoS simulation).
- Social engineering or phishing of MedFlow staff.
- Physical security of data centers.
- Supabase underlying infrastructure (PostgreSQL engine vulnerabilities not related to MedFlow RLS or logic).

## 3. Key Focus Areas

### 3.1 Authorization & Central Authorization Engine (CAE)
- **IDOR (Insecure Direct Object Reference)**: Attempt to access, modify, or delete `MedicalDocument`, `Visit`, or `Consent` records belonging to a different user or organization.
- **Bypass**: Attempt to bypass the CAE by hitting underlying database endpoints directly if exposed, or manipulating JWT payloads.

### 3.2 Consent & Enforcement
- **Stale Enforcement**: Attempt to download a document using an `enforcement_state_id` that belongs to a different document, or a consent state that has since been revoked.
- **Purpose Violation**: Attempt to access a document with a `purpose` string not permitted by the user's consent policy.

### 3.3 File Uploads & Malware
- Attempt to upload an executable (`.exe`, `.sh`) masquerading as a PDF.
- Attempt to bypass the 10MB file limit.
- Attempt to download a file while it is in the `pending` quarantine state.

### 3.4 Authentication & Sessions
- Attempt to replay an old `refresh_token`.
- Attempt to bypass the MFA `/mfa/verify` gate using the pre-auth access token to hit clinical endpoints.

### 3.5 Cross-Site Scripting (XSS)
- Attempt to inject malicious scripts into Document descriptions, Patient names, or Clinical Notes.
