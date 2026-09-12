"""remove redundant refresh token unique constraint

Revision ID: f13b8d6e2a40
Revises: e42a7c9b1d60
Create Date: 2026-09-13

The refresh-token hash already has a unique index matching the ORM model. The
additional generated UNIQUE constraint duplicated that index and caused
Alembic schema-drift checks to fail.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f13b8d6e2a40"
down_revision: Union[str, None] = "e42a7c9b1d60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "refresh_token_history_refresh_token_hash_key",
        "refresh_token_history",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "refresh_token_history_refresh_token_hash_key",
        "refresh_token_history",
        ["refresh_token_hash"],
    )
