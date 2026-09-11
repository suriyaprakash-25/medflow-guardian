# Disaster Recovery & RTO/RPO

**Date:** 2026-09-11

## 1. Recovery Objectives

### RTO (Recovery Time Objective)
- **TARGET RTO**: 4 Hours.
- **Evidence**: Restoring a Supabase database from a PITR backup typically takes <1 hour depending on size. Redeploying the Render backend takes <5 minutes.

### RPO (Recovery Point Objective)
- **TARGET RPO**: 5 Minutes.
- **Evidence**: Supabase Pro/Enterprise plans utilize continuous WAL (Write-Ahead Logging) archiving, meaning data loss in the event of a catastrophic cluster failure is limited to the last synced WAL segment (typically <5 minutes).

*Note: These are targets. Actual RTO/RPO cannot be guaranteed without full physical redundancy (Multi-AZ) and verified recovery drills.*

## 2. Infrastructure Failure Scenarios

### 2.1 Backend Compute Failure
- **Impact**: Render region outage.
- **Action**: Render automatically shifts load across its edge. If the underlying AWS region fails, the service can be redeployed to a secondary Render region connected to the same Supabase instance.

### 2.2 Database Failure (Primary Instance Down)
- **Impact**: Application fails closed. No authorization decisions can be made.
- **Action**: Supabase manages Postgres. If the primary fails, Supabase automation should recover it. If corruption occurs, initiate a Point-In-Time Restore from the Supabase dashboard.

### 2.3 Storage Failure
- **Impact**: Documents cannot be uploaded or downloaded.
- **Action**: MedFlow relies entirely on Supabase Storage (backed by S3). S3 provides 99.999999999% durability. If accidental deletion occurs, recovery depends on Supabase Storage backup configurations (currently UNVERIFIED).
