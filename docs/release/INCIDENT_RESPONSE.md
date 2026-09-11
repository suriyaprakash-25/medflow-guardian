# INCIDENT RESPONSE

## Response Procedures
- **Credential Compromise:** Invalidate sessions, rotate JWT secrets if necessary.
- **Data Breach/Leakage:** Suspend all non-essential API access, preserve forensic audit logs in `AuditLog` table.
- **Malware Upload Detected:** Quarantine S3 object, notify security team.

## Escalation
- Incidents must be escalated to the platform security lead immediately. Legal/regulatory notifications are required by organizational policies.
