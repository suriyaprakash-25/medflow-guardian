"""privacy request and legal hold

Revision ID: 6a4f2c8d901e
Revises: f13b8d6e2a40
Create Date: 2026-09-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "6a4f2c8d901e"
down_revision: Union[str, None] = "f13b8d6e2a40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _default_deny(table_name: str) -> None:
    op.execute(f'ALTER TABLE public."{table_name}" ENABLE ROW LEVEL SECURITY')
    op.execute(
        f"""
        DO $$
        DECLARE target_role text;
        BEGIN
            FOREACH target_role IN ARRAY ARRAY['anon', 'authenticated']
            LOOP
                IF to_regrole(target_role) IS NOT NULL THEN
                    EXECUTE format(
                        'REVOKE ALL PRIVILEGES ON TABLE public.%I FROM %I',
                        '{table_name}', target_role
                    );
                END IF;
            END LOOP;
        END;
        $$
        """
    )


def upgrade() -> None:
    op.create_table(
        "privacy_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("request_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("request_type IN ('export', 'deletion')", name="ck_privacy_requests_type"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'completed')", name="ck_privacy_requests_status"),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_privacy_requests_patient_id", "privacy_requests", ["patient_id"])
    op.create_index("ix_privacy_requests_reviewed_by_id", "privacy_requests", ["reviewed_by_id"])
    op.create_index("ix_privacy_requests_status", "privacy_requests", ["status"])
    op.create_index(
        "uq_privacy_requests_active_type",
        "privacy_requests",
        ["patient_id", "request_type"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'approved')"),
    )

    op.create_table(
        "privacy_legal_holds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("placed_by_id", sa.Integer(), nullable=False),
        sa.Column("released_by_id", sa.Integer(), nullable=True),
        sa.Column("placed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["placed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["released_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_privacy_legal_holds_active", "privacy_legal_holds", ["active"])
    op.create_index("ix_privacy_legal_holds_patient_id", "privacy_legal_holds", ["patient_id"])
    op.create_index("ix_privacy_legal_holds_placed_by_id", "privacy_legal_holds", ["placed_by_id"])
    op.create_index("ix_privacy_legal_holds_released_by_id", "privacy_legal_holds", ["released_by_id"])
    op.create_index(
        "uq_privacy_legal_holds_active_patient",
        "privacy_legal_holds",
        ["patient_id"],
        unique=True,
        postgresql_where=sa.text("active"),
    )

    _default_deny("privacy_requests")
    _default_deny("privacy_legal_holds")


def downgrade() -> None:
    op.drop_table("privacy_legal_holds")
    op.drop_table("privacy_requests")
