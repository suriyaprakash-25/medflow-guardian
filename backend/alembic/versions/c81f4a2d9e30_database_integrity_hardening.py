"""database integrity hardening

Revision ID: c81f4a2d9e30
Revises: 7b2c91e4d6a8
Create Date: 2026-09-12

The constraints are introduced NOT VALID so existing production rows do not
turn this additive deployment into an outage. PostgreSQL still enforces them
for every insert or update performed after this migration. A later, separately
observed cleanup can validate each constraint once legacy data is certified.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c81f4a2d9e30"
down_revision: Union[str, None] = "7b2c91e4d6a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FK_INDEXES = (
    ("ix_access_grant_documents_document_id", "access_grant_documents", "document_id"),
    ("ix_access_request_documents_document_id", "access_request_documents", "document_id"),
    ("ix_audit_logs_consent_state_id", "audit_logs", "consent_state_id"),
    ("ix_appointments_patient_id", "appointments", "patient_id"),
    ("ix_appointments_doctor_id", "appointments", "doctor_id"),
    ("ix_appointments_hospital_id", "appointments", "hospital_id"),
    ("ix_clinical_notes_patient_id", "clinical_notes", "patient_id"),
    ("ix_clinical_notes_doctor_id", "clinical_notes", "doctor_id"),
    ("ix_clinical_notes_hospital_id", "clinical_notes", "hospital_id"),
    ("ix_hospital_staff_hospital_id", "hospital_staff", "hospital_id"),
    ("ix_lab_results_patient_id", "lab_results", "patient_id"),
    ("ix_lab_results_doctor_id", "lab_results", "doctor_id"),
    ("ix_lab_results_hospital_id", "lab_results", "hospital_id"),
    ("ix_messages_sender_id", "messages", "sender_id"),
    ("ix_messages_receiver_id", "messages", "receiver_id"),
    ("ix_notifications_user_id", "notifications", "user_id"),
    ("ix_notifications_related_document_id", "notifications", "related_document_id"),
    ("ix_notifications_related_request_id", "notifications", "related_request_id"),
    ("ix_patient_profiles_assigned_doctor_id", "patient_profiles", "assigned_doctor_id"),
    ("ix_patient_readings_patient_id", "patient_readings", "patient_id"),
    ("ix_prescriptions_patient_id", "prescriptions", "patient_id"),
    ("ix_prescriptions_doctor_id", "prescriptions", "doctor_id"),
    ("ix_prescriptions_medication_id", "prescriptions", "medication_id"),
    ("ix_prescriptions_hospital_id", "prescriptions", "hospital_id"),
    ("ix_triage_requests_patient_id", "triage_requests", "patient_id"),
    ("ix_triage_requests_hospital_id", "triage_requests", "hospital_id"),
    ("ix_visits_patient_id", "visits", "patient_id"),
    ("ix_visits_hospital_id", "visits", "hospital_id"),
    ("ix_visits_doctor_id", "visits", "doctor_id"),
)


CHECK_CONSTRAINTS = (
    (
        "ck_access_requests_status",
        "document_access_requests",
        "status IN ('pending', 'approved', 'rejected', 'cancelled', 'expired', 'revoked')",
    ),
    (
        "ck_access_grants_status",
        "document_access_grants",
        "status IN ('active', 'revoked', 'expired')",
    ),
    (
        "ck_access_grants_consent_required",
        "document_access_grants",
        "consent_id IS NOT NULL",
    ),
    (
        "ck_access_grants_expiry_after_grant",
        "document_access_grants",
        "expires_at > granted_at",
    ),
    ("ck_audit_logs_decision", "audit_logs", "decision IN ('ALLOW', 'DENY')"),
    (
        "ck_consents_provenance_pair",
        "consents",
        "(source_system IS NULL) = (source_resource_id IS NULL)",
    ),
    (
        "ck_consents_status",
        "consents",
        "status IN ('draft', 'active', 'suspended', 'revoked', 'expired', 'superseded', 'cancelled')",
    ),
    (
        "ck_consent_policy_version_positive",
        "consent_policy_versions",
        "version_number > 0",
    ),
    (
        "ck_consent_policy_versions_status",
        "consent_policy_versions",
        "status IN ('active', 'superseded')",
    ),
    (
        "ck_consent_states_status",
        "consent_states",
        "status IN ('draft', 'active', 'suspended', 'revoked', 'expired', 'superseded', 'cancelled')",
    ),
    ("ck_medical_documents_file_size", "medical_documents", "file_size >= 0"),
)


def upgrade() -> None:
    for name, table, column in FK_INDEXES:
        op.create_index(name, table, [column], unique=False)

    for name, table, condition in CHECK_CONSTRAINTS:
        op.create_check_constraint(
            name,
            table,
            condition,
            postgresql_not_valid=True,
        )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION medflow_reject_immutable_history_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only', TG_TABLE_NAME
                USING ERRCODE = '55000';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_logs_append_only
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION medflow_reject_immutable_history_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_consent_states_append_only
        BEFORE UPDATE OR DELETE ON consent_states
        FOR EACH ROW EXECUTE FUNCTION medflow_reject_immutable_history_mutation()
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION medflow_protect_consent_policy_version()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.consent_id IS DISTINCT FROM OLD.consent_id
                OR NEW.version_number IS DISTINCT FROM OLD.version_number
                OR NEW.policy_payload IS DISTINCT FROM OLD.policy_payload
                OR NEW.created_at IS DISTINCT FROM OLD.created_at
            THEN
                RAISE EXCEPTION 'consent policy version content is immutable'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_consent_policy_versions_immutable
        BEFORE UPDATE ON consent_policy_versions
        FOR EACH ROW EXECUTE FUNCTION medflow_protect_consent_policy_version()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_consent_policy_versions_immutable ON consent_policy_versions")
    op.execute("DROP FUNCTION IF EXISTS medflow_protect_consent_policy_version()")
    op.execute("DROP TRIGGER IF EXISTS trg_consent_states_append_only ON consent_states")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_append_only ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS medflow_reject_immutable_history_mutation()")

    for name, table, _condition in reversed(CHECK_CONSTRAINTS):
        op.drop_constraint(name, table, type_="check")

    for name, table, _column in reversed(FK_INDEXES):
        op.drop_index(name, table_name=table)
