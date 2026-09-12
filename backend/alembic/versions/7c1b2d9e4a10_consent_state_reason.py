"""add consent state transition reason

Revision ID: 7c1b2d9e4a10
Revises: fb05e6d42f60
"""
from alembic import op
import sqlalchemy as sa

revision = "7c1b2d9e4a10"
down_revision = "fb05e6d42f60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consent_states", sa.Column("reason", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("consent_states", "reason")
