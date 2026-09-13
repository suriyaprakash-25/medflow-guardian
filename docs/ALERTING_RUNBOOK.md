# Alerting Runbook

**Date:** 2026-09-11
**Owner:** Platform Engineering

## 1. Alert Tiers & Thresholds

### Tier 1: CRITICAL (Immediate Pager)
- **Database Unreachable**: `/ready` endpoint returns 503 for > 1 minute.
- **Sustained 5xx Spike**: >5% of all requests return HTTP 500+ over a 5-minute window.
- **Storage Write Failure**: >10 consecutive document upload failures.

### Tier 2: HIGH (Slack Notification, Next-Day Review)
- **Elevated 403 / Authorization Denials**: Indicates a potential misconfiguration in the CAE, or a user actively probing boundaries.
- **Elevated MFA Failures**: Multiple failures for the same user account over 15 minutes.
- **Malware Detected**: `scan_status` flagged as `malicious`. Requires immediate deletion of the quarantined file and review of the uploader.
- **Connection Pool High**: Connection utilization >80% for 5+ minutes.

### Tier 3: WARNING (Dashboard Only)
- **High 401 Unauthorized**: Normal behavior (e.g., expired token before refresh), but a massive spike could indicate a credential stuffing attack. 

## 2. Noise Reduction
Alerts MUST NOT fire for normal operational failures:
- A single 403 from a doctor querying a patient they don't have access to is normal.
- A single 401 when an access token expires is normal.
- Alerts should only trigger on *rate anomalies* or *systemic backend failures*.
# Production alert response

Every alert requires an incident owner, UTC timestamps, correlation IDs, an
impact assessment, and a link to preserved evidence. Never paste PHI, tokens,
cookies, request bodies, or database rows into tickets or chat.

## MedFlowApiUnavailable

Page operations immediately. Confirm Render service state and recent deploys,
then use `/health`. Roll back the most recent release if availability did not
recover within five minutes.

## MedFlowApiNotReady

Page operations and database owners. Check Supabase availability, connection
pool saturation, SSL configuration, and migration state. Do not route traffic
to an instance returning `503` from `/ready`.

## MedFlowHighServerErrorRate

Page the backend owner. Group structured logs by normalized route and request
ID. If one release introduced the failures, execute the rollback runbook.

## MedFlowHighLatency

Notify the backend and database owners. Compare route p95 with PostgreSQL query,
lock, and connection metrics; capture `EXPLAIN (ANALYZE, BUFFERS)` only against
sanitized or approved data.

## MedFlowAuthorizationDenialSpike

Notify security. Break down the bounded metric by resource, operation, and
reason, then correlate request IDs with authorization audit records. Treat
unexplained cross-tenant, consent, or session denial spikes as a potential
security incident.

## Closure

Close only after the metric is healthy, the underlying cause is documented,
temporary credentials are revoked, and corrective work has an owner and due
date. Follow `docs/INCIDENT_RESPONSE_RUNBOOK.md` for suspected compromise.
