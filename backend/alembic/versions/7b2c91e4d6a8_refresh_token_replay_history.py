"""add refresh token replay history

Revision ID: 7b2c91e4d6a8
Revises: c4b8f19a62d3
Create Date: 2026-09-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b2c91e4d6a8"
down_revision: Union[str, None] = "c4b8f19a62d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing sessions were issued with token families by the current auth code,
    # but normalize any historical null values before enforcing the invariant.
    op.execute("UPDATE sessions SET token_family = id::text WHERE token_family IS NULL")
    op.alter_column("sessions", "token_family", existing_type=sa.String(), nullable=False)

    op.create_table(
        "refresh_token_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_family", sa.String(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("refresh_token_hash"),
    )
    op.create_index(
        op.f("ix_refresh_token_history_id"),
        "refresh_token_history",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_refresh_token_history_user_id"),
        "refresh_token_history",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_refresh_token_history_token_family"),
        "refresh_token_history",
        ["token_family"],
        unique=False,
    )
    op.create_index(
        op.f("ix_refresh_token_history_refresh_token_hash"),
        "refresh_token_history",
        ["refresh_token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_refresh_token_history_refresh_token_hash"),
        table_name="refresh_token_history",
    )
    op.drop_index(
        op.f("ix_refresh_token_history_token_family"),
        table_name="refresh_token_history",
    )
    op.drop_index(
        op.f("ix_refresh_token_history_user_id"),
        table_name="refresh_token_history",
    )
    op.drop_index(
        op.f("ix_refresh_token_history_id"),
        table_name="refresh_token_history",
    )
    op.drop_table("refresh_token_history")
    op.alter_column("sessions", "token_family", existing_type=sa.String(), nullable=True)
