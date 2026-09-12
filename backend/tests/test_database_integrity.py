from sqlalchemy import inspect, text

from app.core.database import engine
from app.models import Base


EXPECTED_CHECK_CONSTRAINTS = {
    "ck_access_requests_status",
    "ck_access_grants_status",
    "ck_access_grants_consent_required",
    "ck_access_grants_expiry_after_grant",
    "ck_audit_logs_decision",
    "ck_consents_provenance_pair",
    "ck_consents_status",
    "ck_consent_policy_version_positive",
    "ck_consent_policy_versions_status",
    "ck_consent_states_status",
    "ck_medical_documents_file_size",
}

EXPECTED_HISTORY_TRIGGERS = {
    "trg_audit_logs_append_only",
    "trg_consent_states_append_only",
    "trg_consent_policy_versions_immutable",
}

APPLICATION_TABLES = set(Base.metadata.tables)


def _indexed_column_sequences(inspector, table_name: str) -> set[tuple[str, ...]]:
    sequences = {
        tuple(index["column_names"])
        for index in inspector.get_indexes(table_name)
        if index.get("column_names")
    }

    primary_key = inspector.get_pk_constraint(table_name).get("constrained_columns")
    if primary_key:
        sequences.add(tuple(primary_key))

    for constraint in inspector.get_unique_constraints(table_name):
        columns = constraint.get("column_names")
        if columns:
            sequences.add(tuple(columns))

    return sequences


def test_every_foreign_key_has_a_supporting_index():
    """Prevent unindexed FKs from reintroducing join and cascade table scans."""
    inspector = inspect(engine)
    missing: list[str] = []

    for table_name in inspector.get_table_names():
        indexed_sequences = _indexed_column_sequences(inspector, table_name)
        for foreign_key in inspector.get_foreign_keys(table_name):
            columns = tuple(foreign_key["constrained_columns"])
            if not any(sequence[: len(columns)] == columns for sequence in indexed_sequences):
                missing.append(f"{table_name}({', '.join(columns)})")

    assert not missing, "Foreign keys without a supporting left-prefix index: " + ", ".join(missing)


def test_security_critical_check_constraints_are_installed():
    inspector = inspect(engine)
    actual = {
        constraint["name"]
        for table_name in inspector.get_table_names()
        for constraint in inspector.get_check_constraints(table_name)
    }

    assert EXPECTED_CHECK_CONSTRAINTS <= actual


def test_security_history_is_database_protected():
    with engine.connect() as connection:
        trigger_names = set(
            connection.execute(
                text(
                    """
                    SELECT trigger_name
                    FROM information_schema.triggers
                    WHERE trigger_schema = 'public'
                    """
                )
            ).scalars()
        )

    assert EXPECTED_HISTORY_TRIGGERS <= trigger_names


def test_every_application_table_is_default_deny_under_rls():
    with engine.connect() as connection:
        rls_tables = set(
            connection.execute(
                text(
                    """
                    SELECT c.relname
                    FROM pg_class AS c
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public'
                      AND c.relkind IN ('r', 'p')
                      AND c.relrowsecurity
                    """
                )
            ).scalars()
        )
        direct_policy_tables = set(
            connection.execute(
                text(
                    """
                    SELECT DISTINCT tablename
                    FROM pg_policies
                    WHERE schemaname = 'public'
                    """
                )
            ).scalars()
        )

    assert APPLICATION_TABLES <= rls_tables
    assert not (APPLICATION_TABLES & direct_policy_tables), (
        "MedFlow authorization must remain behind FastAPI/Model A; direct Data API "
        "policies were found for: " + ", ".join(sorted(APPLICATION_TABLES & direct_policy_tables))
    )


def test_supabase_browser_roles_have_no_direct_table_or_sequence_access():
    with engine.connect() as connection:
        available_roles = set(
            connection.execute(
                text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')")
            ).scalars()
        )
        leaked_table_privileges = set()
        leaked_sequence_privileges = set()
        for role in available_roles:
            leaked_table_privileges.update(
                connection.execute(
                    text(
                        """
                        SELECT table_name
                        FROM information_schema.role_table_grants
                        WHERE grantee = :role
                          AND table_schema = 'public'
                          AND table_name = ANY(:tables)
                        """
                    ),
                    {"role": role, "tables": sorted(APPLICATION_TABLES)},
                ).scalars()
            )
            leaked_sequence_privileges.update(
                connection.execute(
                    text(
                        """
                        SELECT object_name
                        FROM information_schema.role_usage_grants
                        WHERE grantee = :role
                          AND object_schema = 'public'
                          AND object_type = 'SEQUENCE'
                        """
                    ),
                    {"role": role},
                ).scalars()
            )

    assert not leaked_table_privileges
    assert not leaked_sequence_privileges


def test_integrity_constraints_enforce_new_writes(db_session):
    """NOT VALID preserves legacy rows but must still reject invalid new data."""
    from app.core.security import get_password_hash
    from app.models.consent import Consent
    from app.models.user import User

    patient = User(
        email="database-integrity-patient@example.com",
        hashed_password=get_password_hash("password123"),
        role="patient",
        is_active=True,
    )
    db_session.add(patient)
    db_session.flush()

    db_session.add(
        Consent(
            patient_id=patient.id,
            status="active",
            source_system="https://external.example/fhir",
            source_resource_id=None,
        )
    )

    import pytest
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        db_session.flush()
