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
