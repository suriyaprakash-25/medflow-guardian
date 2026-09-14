"""add consent policy validity period

Revision ID: 8f3a2c7d91e4
Revises: 6a4f2c8d901e
"""

from alembic import op
import sqlalchemy as sa


revision = "8f3a2c7d91e4"
down_revision = "6a4f2c8d901e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "consent_policy_versions",
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "consent_policy_versions",
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_consent_policy_versions_valid_period",
        "consent_policy_versions",
        "valid_until IS NULL OR valid_from IS NULL OR valid_until > valid_from",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_consent_policy_versions_valid_period",
        "consent_policy_versions",
        type_="check",
    )
    op.drop_column("consent_policy_versions", "valid_until")
    op.drop_column("consent_policy_versions", "valid_from")
