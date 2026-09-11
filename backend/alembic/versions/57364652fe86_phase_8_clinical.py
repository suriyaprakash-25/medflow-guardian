"""phase_8_clinical

Revision ID: 57364652fe86
Revises: 5d3c23e97acd
Create Date: 2026-09-10 23:24:40.662164

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57364652fe86'
down_revision: Union[str, Sequence[str], None] = '5d3c23e97acd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('medications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_medications_id'), 'medications', ['id'], unique=False)
    op.create_index(op.f('ix_medications_name'), 'medications', ['name'], unique=False)

    op.create_table('prescriptions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('doctor_id', sa.Integer(), nullable=False),
    sa.Column('medication_id', sa.Integer(), nullable=False),
    sa.Column('hospital_id', sa.Integer(), nullable=False),
    sa.Column('dosage', sa.String(), nullable=False),
    sa.Column('frequency', sa.String(), nullable=False),
    sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
    sa.ForeignKeyConstraint(['medication_id'], ['medications.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prescriptions_id'), 'prescriptions', ['id'], unique=False)

    op.create_table('lab_results',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('doctor_id', sa.Integer(), nullable=False),
    sa.Column('hospital_id', sa.Integer(), nullable=False),
    sa.Column('test_name', sa.String(), nullable=False),
    sa.Column('result_value', sa.String(), nullable=False),
    sa.Column('unit', sa.String(), nullable=True),
    sa.Column('reference_range', sa.String(), nullable=True),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('test_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lab_results_id'), 'lab_results', ['id'], unique=False)

    op.create_table('clinical_notes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('doctor_id', sa.Integer(), nullable=False),
    sa.Column('hospital_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('note_type', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clinical_notes_id'), 'clinical_notes', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_clinical_notes_id'), table_name='clinical_notes')
    op.drop_table('clinical_notes')
    op.drop_index(op.f('ix_lab_results_id'), table_name='lab_results')
    op.drop_table('lab_results')
    op.drop_index(op.f('ix_prescriptions_id'), table_name='prescriptions')
    op.drop_table('prescriptions')
    op.drop_index(op.f('ix_medications_name'), table_name='medications')
    op.drop_index(op.f('ix_medications_id'), table_name='medications')
    op.drop_table('medications')
