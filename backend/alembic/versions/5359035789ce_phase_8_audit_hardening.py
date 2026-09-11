"""phase_8_audit_hardening

Revision ID: 5359035789ce
Revises: fb05e6d42f60
Create Date: 2026-09-10 23:01:24.739850

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5359035789ce'
down_revision: Union[str, Sequence[str], None] = 'fb05e6d42f60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('operation', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('resource_type', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('resource_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('purpose', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('request_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('correlation_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('authorization_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('consent_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('consent_state_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('policy_version', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('enforcement_point', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('enforcement_state', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('decision', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('denial_reason', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True))

    op.execute("UPDATE audit_logs SET operation = COALESCE(action, 'UNKNOWN'), resource_type = 'UNKNOWN', decision = COALESCE(status, 'ALLOW'), timestamp = created_at")

    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.alter_column('operation', existing_type=sa.String(), nullable=False)
        batch_op.alter_column('resource_type', existing_type=sa.String(), nullable=False)
        batch_op.alter_column('decision', existing_type=sa.String(), nullable=False)
        
        batch_op.drop_column('hospital_id')
        batch_op.drop_column('action')
        batch_op.drop_column('document_id')
        batch_op.drop_column('access_request_id')
        batch_op.drop_column('access_grant_id')
        batch_op.drop_column('status')
        batch_op.drop_column('created_at')

        batch_op.create_foreign_key('fk_audit_org', 'hospitals', ['organization_id'], ['id'])
        batch_op.create_foreign_key('fk_audit_consent', 'consents', ['consent_id'], ['id'])
        batch_op.create_foreign_key('fk_audit_consent_state', 'consent_states', ['consent_state_id'], ['id'])
        
        batch_op.create_index(batch_op.f('ix_audit_logs_timestamp'), ['timestamp'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_resource_id'), ['resource_id'], unique=False)


def downgrade() -> None:
    pass
