# Database Connection Operations

**Date:** 2026-09-11

## Architecture & Problem Statement
MedFlow Guardian relies on Supabase PostgreSQL. Supabase utilizes PgBouncer for connection pooling to allow serverless/edge environments to connect without exhausting backend database memory. However, transient pooler drops were observed in Phase 10 during integration testing under high churn.

## Mitigations Implemented (Phase 12)

### 1. Hardened SQLAlchemy Connection Pool Bounds
- **`pool_size=10`**: Establishes a baseline of 10 persistent connections per FastAPI worker process.
- **`max_overflow=5`**: Restricts the maximum temporary connections to 5. This strict upper bound ensures horizontal scaling of backend instances does not exponentially overwhelm the Supabase pooler.
- **`pool_pre_ping=True`**: Forces SQLAlchemy to verify the connection (`SELECT 1`) before dispatching it. If the connection was silently dropped by Supabase PgBouncer or a network partition, it will be transparently recycled.
- **`pool_recycle=1800`**: Automatically discards connections older than 30 minutes to prevent stale NAT states and idle transaction timeouts.

### 2. Leaked Transaction Prevention
- **`statement_timeout=30000`**: All queries are now subjected to a strict 30-second execution limit. If a complex JOIN or locked row blocks execution, the database will aggressively terminate the query and return an error. This prevents the connection pool from being exhausted by long-running zombie transactions.

## Operational Constraints
- If horizontal scaling is implemented (e.g. running 10 FastAPI instances), the total maximum database connections will be `10 instances * (10 pool_size + 5 max_overflow) = 150 connections`. 
- Supabase PgBouncer must be configured with a `pool_size` > 150 to accommodate this.
