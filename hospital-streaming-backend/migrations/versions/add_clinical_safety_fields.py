"""Add clinical safety fields to patient model

Revision ID: add_clinical_safety_fields
Revises: 
Create Date: 2024-08-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_clinical_safety_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add clinical safety fields to existing tables"""
    
    # Add clinical safety fields to patients table
    op.add_column('patients', sa.Column('code_status', sa.String(), nullable=True, default='full_code'))
    op.add_column('patients', sa.Column('active_problems', sa.JSON(), nullable=True))
    op.add_column('patients', sa.Column('last_medication_time', sa.String(), nullable=True))
    op.add_column('patients', sa.Column('next_medication_due', sa.String(), nullable=True))
    
    # Create patient_allergies table
    op.create_table('patient_allergies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('patient_id', sa.String(), nullable=False),
        sa.Column('allergen', sa.String(), nullable=False),
        sa.Column('allergen_type', sa.String(), nullable=False),
        sa.Column('reaction', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('onset', sa.String(), nullable=True),
        sa.Column('verification_status', sa.String(), nullable=True, default='confirmed'),
        sa.Column('recorded_date', sa.String(), nullable=False),
        sa.Column('recorded_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_patient_allergies_id'), 'patient_allergies', ['id'], unique=False)
    
    # Create handoff_notes table
    op.create_table('handoff_notes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('patient_id', sa.String(), nullable=False),
        sa.Column('shift', sa.String(), nullable=False),
        sa.Column('from_nurse', sa.String(), nullable=False),
        sa.Column('to_nurse', sa.String(), nullable=True),
        sa.Column('priority', sa.String(), nullable=True, default='medium'),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), nullable=True, default=False),
        sa.Column('acknowledged_by', sa.String(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_handoff_notes_id'), 'handoff_notes', ['id'], unique=False)
    
    # Set default values for existing patients
    op.execute("UPDATE patients SET code_status = 'full_code' WHERE code_status IS NULL")
    op.execute("UPDATE patients SET active_problems = '[]' WHERE active_problems IS NULL")


def downgrade():
    """Remove clinical safety fields and tables"""
    
    # Drop new tables
    op.drop_index(op.f('ix_handoff_notes_id'), table_name='handoff_notes')
    op.drop_table('handoff_notes')
    op.drop_index(op.f('ix_patient_allergies_id'), table_name='patient_allergies')
    op.drop_table('patient_allergies')
    
    # Remove columns from patients table
    op.drop_column('patients', 'next_medication_due')
    op.drop_column('patients', 'last_medication_time')
    op.drop_column('patients', 'active_problems')
    op.drop_column('patients', 'code_status')