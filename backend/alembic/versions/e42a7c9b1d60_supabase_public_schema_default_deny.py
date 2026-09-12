"""supabase public schema default deny

Revision ID: e42a7c9b1d60
Revises: c81f4a2d9e30
Create Date: 2026-09-13

MedFlow exposes application behavior through FastAPI and Model A, not through
Supabase's generated Data API. Every application table in the exposed public
schema therefore enables RLS without direct client policies, and the browser
roles lose direct table and sequence privileges.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e42a7c9b1d60"
down_revision: Union[str, None] = "c81f4a2d9e30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


APPLICATION_TABLES = (
    "access_grant_documents",
    "access_request_documents",
    "appointments",
    "audit_logs",
    "clinical_notes",
    "consent_policy_versions",
    "consent_states",
    "consents",
    "document_access_grants",
    "document_access_requests",
    "hospital_staff",
    "hospitals",
    "lab_results",
    "medical_documents",
    "medications",
    "messages",
    "notifications",
    "patient_profiles",
    "patient_readings",
    "practitioner_profiles",
    "prescriptions",
    "refresh_token_history",
    "sessions",
    "triage_requests",
    "user_mfa",
    "users",
    "visits",
)


def upgrade() -> None:
    for table_name in APPLICATION_TABLES:
        op.execute(f'ALTER TABLE public."{table_name}" ENABLE ROW LEVEL SECURITY')

    # Vanilla PostgreSQL test environments do not define Supabase's browser
    # roles. Keep the migration portable while revoking access when those roles
    # are present in Supabase.
    op.execute(
        """
        DO $$
        DECLARE
            target_table text;
            target_role text;
        BEGIN
            FOREACH target_role IN ARRAY ARRAY['anon', 'authenticated']
            LOOP
                IF to_regrole(target_role) IS NOT NULL THEN
                    FOREACH target_table IN ARRAY ARRAY[
                        'access_grant_documents',
                        'access_request_documents',
                        'appointments',
                        'audit_logs',
                        'clinical_notes',
                        'consent_policy_versions',
                        'consent_states',
                        'consents',
                        'document_access_grants',
                        'document_access_requests',
                        'hospital_staff',
                        'hospitals',
                        'lab_results',
                        'medical_documents',
                        'medications',
                        'messages',
                        'notifications',
                        'patient_profiles',
                        'patient_readings',
                        'practitioner_profiles',
                        'prescriptions',
                        'refresh_token_history',
                        'sessions',
                        'triage_requests',
                        'user_mfa',
                        'users',
                        'visits'
                    ]
                    LOOP
                        EXECUTE format(
                            'REVOKE ALL PRIVILEGES ON TABLE public.%I FROM %I',
                            target_table,
                            target_role
                        );
                    END LOOP;

                    EXECUTE format(
                        'REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM %I',
                        target_role
                    );
                    EXECUTE format(
                        'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        'REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM %I',
                        target_role
                    );
                    EXECUTE format(
                        'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        'REVOKE USAGE, SELECT ON SEQUENCES FROM %I',
                        target_role
                    );
                END IF;
            END LOOP;
        END;
        $$
        """
    )


def downgrade() -> None:
    # Removing RLS is reversible for local migration testing. Revoked client
    # grants intentionally remain revoked; a rollback must never silently
    # reopen the generated Data API.
    for table_name in reversed(APPLICATION_TABLES):
        op.execute(f'ALTER TABLE public."{table_name}" DISABLE ROW LEVEL SECURITY')
