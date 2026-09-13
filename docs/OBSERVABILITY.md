# Observability Strategy

## Logging
- **Format**: Structured JSON logging.
- **Engine**: Python standard `logging` intercepted by a custom `JSONFormatter`.
- **PHI Redaction**: Explicit redaction of fields like `password`, `token`, and any HTTP request bodies. The log format only exposes `timestamp`, `level`, `module`, `funcName`, and safe `message`.
- **Destination**: Output to stdout/stderr. Aggregated by a log shipper (e.g., Datadog, Fluentbit, CloudWatch) to a secure, centralized logging server.

## Audit Trails
- **System**: The MedFlow Guardian `AuditLog` table.
- **Purpose**: Tracks all sensitive `ALLOW`/`DENY` operations via the Central Authorization Engine.
- **Retention**: Audit logs are strictly append-only and retained indefinitely to satisfy healthcare compliance.
- *Note*: While not currently cryptographically hash-chained, the structure guarantees all decisions are typed, attributed to an actor, and tied to a specific `ConsentState`.

## Metrics
- FastAPI Prometheus middleware (optional phase) can track P99 latency of critical endpoints like `/download` and `/login`.
# Production observability contract

MedFlow emits JSON application logs to stdout in production. Render's log
stream is the initial centralized transport; production operators must attach a
retained log sink before release. Request telemetry contains only the HTTP
method, normalized route template, response status, duration, and correlation
ID. Query strings, request/response bodies, tokens, emails, patient IDs, and
document IDs are deliberately excluded.

Every response includes `X-Request-ID`. A caller-supplied ID is accepted only
when it is 8–128 characters from `[A-Za-z0-9._-]`; otherwise the service creates
a UUID. Operators can use this identifier to correlate an API response with the
JSON log stream without logging PHI.

## Metrics

`GET /internal/metrics` uses Prometheus text exposition. It is excluded from
OpenAPI and returns `404` unless called with:

```text
Authorization: Bearer <OBSERVABILITY_TOKEN>
```

The production token must be at least 32 characters. It is a collector secret,
not a frontend variable. Metrics labels are bounded to route templates,
methods, statuses, resource classes, operations, decisions, and denial reasons.

The dashboard is `ops/observability/grafana-dashboard.json`; alert rules are in
`ops/observability/alerts.yml`. The collector must scrape the private backend
endpoint over TLS and must not expose the token in its UI or logs.

## Uptime

`.github/workflows/production-uptime.yml` checks `/health` and `/ready` every
five minutes after the repository variable `PRODUCTION_API_URL` is configured.
A failed workflow is the external uptime signal and must notify the on-call
channel through GitHub Actions notifications. Keep a second provider outside
GitHub for production resilience.

## Release evidence

Before production sign-off, capture:

1. a successful authenticated metrics scrape;
2. the imported dashboard and active alert rules;
3. a synthetic alert routed to the on-call owner;
4. 24 hours of successful uptime runs;
5. proof that the log sink retention and access controls match policy.
