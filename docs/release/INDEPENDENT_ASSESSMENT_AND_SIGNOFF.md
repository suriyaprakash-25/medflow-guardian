# Independent security assessment and production sign-off

## Automated evidence required

- complete PostgreSQL-backed CI and Newman endpoint certification;
- official HL7 FHIR validator OperationOutcomes with zero fatal/errors;
- Bandit high-confidence/high-severity gate;
- `pip-audit` with no known vulnerable Python dependency;
- production-only npm dependency audits with no high/critical finding;
- Gitleaks full-history scan using the pinned 8.29.1 container digest;
- credentialed production smoke test and passive OWASP ZAP report;
- successful restore drill and observability alert-routing proof.

## Independent penetration test

The assessor must be organizationally independent from the implementation
team. Scope includes every production hostname, FastAPI route, WebSocket,
authentication/session flow, all three portals, organization isolation, IDOR,
consent/purpose enforcement, FHIR import/export, Supabase Storage, file upload
and ClamAV boundaries, rate limits, secret exposure, and business-logic abuse.

Every finding records an identifier, severity/CVSS, affected component,
reproduction evidence, owner, remediation commit, retest evidence, assessor
acceptance, and residual-risk approver. Critical/high findings block release;
medium residual risks require dated acceptance by security and clinical owners.

## Sign-off record

| Role | Named approver | Organization | Evidence reviewed | Decision | UTC date |
| --- | --- | --- | --- | --- | --- |
| Independent penetration tester | UNASSIGNED | External | Pending | BLOCKED | — |
| Security owner | UNASSIGNED | — | Pending | BLOCKED | — |
| Privacy/legal owner | UNASSIGNED | — | Pending | BLOCKED | — |
| Clinical safety owner | UNASSIGNED | — | Pending | BLOCKED | — |
| Operations owner | UNASSIGNED | — | Pending | BLOCKED | — |

No repository author may replace these names with a synthetic approval. A
production release is not signed off until accountable humans complete this
table and all blocking findings are independently retested.
