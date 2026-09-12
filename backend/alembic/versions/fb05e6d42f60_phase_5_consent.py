"""phase_5_consent

Revision ID: fb05e6d42f60
Revises: ac0b5631ab13
Create Date: 2026-09-10 20:12:22.516372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb05e6d42f60'
down_revision: Union[str, Sequence[str], None] = 'ac0b5631ab13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clear existing grants to avoid constraint issues during this greenfield phase
    op.execute("DELETE FROM access_grant_documents")
    op.execute("DELETE FROM document_access_grants")

    # Create consents table
    op.create_table(
        'consents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=True),
        sa.Column('hospital_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
        sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_consents_id'), 'consents', ['id'], unique=False)
    op.create_index(op.f('ix_consents_doctor_id'), 'consents', ['doctor_id'], unique=False)
    op.create_index(op.f('ix_consents_hospital_id'), 'consents', ['hospital_id'], unique=False)
    op.create_index(op.f('ix_consents_patient_id'), 'consents', ['patient_id'], unique=False)

    # Create consent_policy_versions table
    op.create_table(
        'consent_policy_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('consent_id', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('policy_payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['consent_id'], ['consents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_consent_policy_versions_id'), 'consent_policy_versions', ['id'], unique=False)
    op.create_index(op.f('ix_consent_policy_versions_consent_id'), 'consent_policy_versions', ['consent_id'], unique=False)

    # Create consent_states table
    op.create_table(
        'consent_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('consent_id', sa.Integer(), nullable=False),
        sa.Column('policy_version_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['consent_id'], ['consents.id'], ),
        sa.ForeignKeyConstraint(['policy_version_id'], ['consent_policy_versions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_consent_states_id'), 'consent_states', ['id'], unique=False)
    op.create_index(op.f('ix_consent_states_consent_id'), 'consent_states', ['consent_id'], unique=False)
    op.create_index(op.f('ix_consent_states_policy_version_id'), 'consent_states', ['policy_version_id'], unique=False)

    # Add consent_id to document_access_grants
    op.add_column('document_access_grants', sa.Column('consent_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_document_access_grants_consent_id'), 'document_access_grants', ['consent_id'], unique=False)
    op.create_foreign_key('fk_doc_access_grant_consent', 'document_access_grants', 'consents', ['consent_id'], ['id'])

def downgrade() -> None:
    op.drop_constraint('fk_doc_access_grant_consent', 'document_access_grants', type_='foreignkey')
    op.drop_index(op.f('ix_document_access_grants_consent_id'), table_name='document_access_grants')
    op.drop_column('document_access_grants', 'consent_id')
    
    op.drop_index(op.f('ix_consent_states_policy_version_id'), table_name='consent_states')
    op.drop_index(op.f('ix_consent_states_consent_id'), table_name='consent_states')
    op.drop_index(op.f('ix_consent_states_id'), table_name='consent_states')
    op.drop_table('consent_states')
    
    op.drop_index(op.f('ix_consent_policy_versions_consent_id'), table_name='consent_policy_versions')
    op.drop_index(op.f('ix_consent_policy_versions_id'), table_name='consent_policy_versions')
    op.drop_table('consent_policy_versions')
    
    op.drop_index(op.f('ix_consents_patient_id'), table_name='consents')
    op.drop_index(op.f('ix_consents_hospital_id'), table_name='consents')
    op.drop_index(op.f('ix_consents_doctor_id'), table_name='consents')
    op.drop_index(op.f('ix_consents_id'), table_name='consents')
    op.drop_table('consents')
