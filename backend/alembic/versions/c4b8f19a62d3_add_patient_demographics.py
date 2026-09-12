"""add patient demographic fields missing from the baseline migration

Revision ID: c4b8f19a62d3
Revises: 9d7a4c2e81b0
"""

from alembic import op
import sqlalchemy as sa


revision = "c4b8f19a62d3"
down_revision = "9d7a4c2e81b0"
branch_labels = None
depends_on = None


DEMOGRAPHIC_COLUMNS = (
    "date_of_birth",
    "address",
    "emergency_contact_name",
    "emergency_contact_phone",
    "blood_type",
    "allergies",
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {column["name"] for column in inspector.get_columns("patient_profiles")}
    for name in DEMOGRAPHIC_COLUMNS:
        if name not in existing:
            op.add_column("patient_profiles", sa.Column(name, sa.String(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {column["name"] for column in inspector.get_columns("patient_profiles")}
    for name in reversed(DEMOGRAPHIC_COLUMNS):
        if name in existing:
            op.drop_column("patient_profiles", name)
