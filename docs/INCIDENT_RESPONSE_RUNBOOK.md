# Incident Response Runbook

**Date:** 2026-09-11
**Owner:** Security Operations Team

## 1. Credential Compromise

### 1.1 JWT `SECRET_KEY` Compromise
**Detection:** Exposed in source code, log leak, or reported by internal team.
**Containment:** 
1. Rotate `SECRET_KEY` in the Render environment variables.
2. Redeploy the Backend Web Service.
**Validation:** Since all JWTs use the same `SECRET_KEY`, rotating it instantly invalidates all active sessions (both short-lived and refresh tokens) across the entire platform. Users will be forced to log in again.
**Investigation:** Review audit logs for unauthorized API access during the window of compromise.

### 1.2 `SUPABASE_SERVICE_ROLE_KEY` Compromise
**Detection:** Unauthorized modification of raw database rows, bypassing FastAPI.
**Containment:** 
1. Immediately roll the service role key in the Supabase Dashboard.
2. Update the key in Render environment variables.
3. Redeploy the Backend.
**Investigation:** Query Supabase internal logs to determine what data was accessed/exfiltrated.

## 2. PHI Exposure / Unauthorized Access

### 2.1 Doctor Accessing Patient Data Without Consent
**Detection:** Anomaly detected in Audit Logs (stale enforcement, or bypass if the CAE failed).
**Containment:** 
1. Revoke the Doctor's active session (`DELETE FROM sessions WHERE user_id = X`).
2. Lock the Doctor's account (`UPDATE users SET is_active = false WHERE id = X`).
**Investigation:** Review the Audit Log (`SELECT * FROM audit_logs WHERE actor_id = X`). Determine exactly which documents were retrieved.
**Legal:** Trigger HIPAA breach notification protocol.

## 3. Malware / Malicious Upload

### 3.1 Zip Bomb / Malicious File Uploaded
**Detection:** Background scan flags `scan_status = 'malicious'`, or storage metrics spike abnormally.
**Containment:** 
1. The backend automatically blocks downloads of `malicious` files.
2. Hard delete the file from the Supabase bucket.
**Investigation:** Identify the uploader. Check if they attempted to bypass the frontend limits by calling the API directly.

## 4. Admin Account Compromise
**Containment:** 
1. Immediately disable the Admin account.
2. Expire all their sessions.
3. Review audit logs for *every* administrative action performed over the last 72 hours (e.g., policy updates, user creations).
