"""OIDC federation identities and access-request expiry

Revision ID: a17c5f6d9b42
Revises: 8f3a2c7d91e4
Create Date: 2026-09-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a17c5f6d9b42"
down_revision: Union[str, None] = "8f3a2c7d91e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_access_requests",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE document_access_requests
        SET expires_at = COALESCE(requested_at, CURRENT_TIMESTAMP) + INTERVAL '24 hours'
        WHERE expires_at IS NULL
        """
    )
    op.alter_column(
        "document_access_requests",
        "expires_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.create_index(
        "ix_document_access_requests_expires_at",
        "document_access_requests",
        ["expires_at"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_access_requests_expiry_after_request",
        "document_access_requests",
        "expires_at > requested_at",
    )

    op.create_table(
        "oidc_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("issuer", sa.String(length=512), nullable=False),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_login_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "issuer",
            "subject",
            name="uq_oidc_identity_provider_issuer_subject",
        ),
        sa.UniqueConstraint(
            "user_id",
            "provider",
            "issuer",
            name="uq_oidc_identity_user_provider_issuer",
        ),
    )
    op.create_index(
        "ix_oidc_identities_id",
        "oidc_identities",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_oidc_identities_user_id",
        "oidc_identities",
        ["user_id"],
        unique=False,
    )

    op.execute('ALTER TABLE public."oidc_identities" ENABLE ROW LEVEL SECURITY')
    op.execute(
        """
        DO $$
        DECLARE
            target_role text;
        BEGIN
            FOREACH target_role IN ARRAY ARRAY['anon', 'authenticated']
            LOOP
                IF to_regrole(target_role) IS NOT NULL THEN
                    EXECUTE format(
                        'REVOKE ALL PRIVILEGES ON TABLE public.oidc_identities FROM %I',
                        target_role
                    );
                END IF;
            END LOOP;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_oidc_identities_user_id", table_name="oidc_identities")
    op.drop_index("ix_oidc_identities_id", table_name="oidc_identities")
    op.drop_table("oidc_identities")

    op.drop_constraint(
        "ck_access_requests_expiry_after_request",
        "document_access_requests",
        type_="check",
    )
    op.drop_index(
        "ix_document_access_requests_expires_at",
        table_name="document_access_requests",
    )
    op.drop_column("document_access_requests", "expires_at")
