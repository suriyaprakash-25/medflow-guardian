# Backup Verification Protocol

**Date:** 2026-09-11

## 1. Actual Capabilities (Supabase)
- **Point-in-Time Recovery (PITR)**: Available on Pro/Enterprise plans. Allows restoring the database to any millisecond within the retention window (usually 7 days).
- **Daily Backups**: Automated snapshots taken every 24 hours.
- **Storage Backups**: Supabase Storage relies on underlying S3 durability but does *not* natively provide PITR for individual bucket objects out of the box unless explicitly configured with bucket versioning. **RISK: Object deletion may be permanent.**

## 2. Verification Status
- **Database Backup Verification**: IMPLEMENTED BUT UNVERIFIED. Relying on Supabase platform guarantees.
- **Storage Backup Verification**: UNVERIFIED.
- **Restore Testing**: BLOCKED. A non-production restore test has not been performed because a secondary staging environment has not yet been provisioned to receive the restored data.

## 3. Required Action
Before general availability, the operations team MUST perform a dry-run restore of a production backup into a staging project and verify that `alembic heads` match and the CAE resolves consent correctly.
