# BACKUP & RESTORE VALIDATION

## Backup Strategy
- Database: use Supabase managed daily backups on an eligible paid plan; PITR
  must be explicitly enabled and evidenced if the approved RPO requires it.
- Take an independent encrypted logical backup before every production migration.
- Supabase database backups do not constitute proof that Storage objects are
  recoverable. Export the private bucket to an approved encrypted backup target.

## Restore Validation

CI continuously restores a PostgreSQL custom-format dump into a clean database
and runs migration/schema-integrity tests. This proves repository-level logical
restore compatibility, not a completed production disaster-recovery drill.

For the live drill, restore the latest approved database and Storage export into
an isolated staging project, rotate copied secrets, run the complete smoke/API
suite, and record UTC start/end times. RTO and RPO are **unverified until this
live drill is executed**; do not reuse estimates from an earlier run.
