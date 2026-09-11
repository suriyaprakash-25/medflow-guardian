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
