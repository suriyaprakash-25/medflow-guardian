"""add user phone number missing from the baseline migration

Revision ID: 9d7a4c2e81b0
Revises: 1155411bf4e4
"""

from alembic import op
import sqlalchemy as sa


revision = "9d7a4c2e81b0"
down_revision = "1155411bf4e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Some existing deployments already have this model column from an older
    # manual schema sync, while clean databases built only from Alembic do not.
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "phone_number" not in columns:
        op.add_column("users", sa.Column("phone_number", sa.String(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "phone_number" in columns:
        op.drop_column("users", "phone_number")
