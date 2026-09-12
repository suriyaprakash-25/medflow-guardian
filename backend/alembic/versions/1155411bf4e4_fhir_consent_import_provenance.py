"""fhir consent import provenance

Revision ID: 1155411bf4e4
Revises: af6896e54190
Create Date: 2026-09-12 13:15:02.552245

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1155411bf4e4'
down_revision: Union[str, Sequence[str], None] = 'af6896e54190'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("consents", sa.Column("source_system", sa.String(length=255), nullable=True))
    op.add_column("consents", sa.Column("source_resource_id", sa.String(length=255), nullable=True))
    op.add_column("consent_states", sa.Column("reason", sa.String(length=500), nullable=True))
    op.create_unique_constraint(
        "uq_consents_source_system_resource_id",
        "consents",
        ["source_system", "source_resource_id"],
    )
    op.create_unique_constraint(
        "uq_consent_policy_versions_consent_version",
        "consent_policy_versions",
        ["consent_id", "version_number"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_consent_policy_versions_consent_version",
        "consent_policy_versions",
        type_="unique",
    )
    op.drop_constraint("uq_consents_source_system_resource_id", "consents", type_="unique")
    op.drop_column("consent_states", "reason")
    op.drop_column("consents", "source_resource_id")
    op.drop_column("consents", "source_system")
