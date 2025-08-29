"""Create comprehensive audit logs table

Revision ID: create_audit_logs_table
Revises: 
Create Date: 2024-08-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_audit_logs_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Create audit_logs table in TimescaleDB"""
    
    # Create the audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        # Event Classification
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_category', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        
        # Entity Information
        sa.Column('user_id', sa.String(length=50), nullable=True),
        sa.Column('patient_id', sa.String(length=50), nullable=True),
        sa.Column('device_id', sa.String(length=50), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        
        # Event Details
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('source_ip', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('endpoint', sa.String(length=200), nullable=True),
        sa.Column('http_method', sa.String(length=10), nullable=True),
        sa.Column('http_status', sa.Integer(), nullable=True),
        
        # Data and Context
        sa.Column('request_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('response_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('device_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('additional_context', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        
        # Performance and Monitoring
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        
        # Compliance and Security
        sa.Column('data_classification', sa.String(length=20), nullable=True),
        sa.Column('retention_policy', sa.String(length=50), nullable=True),
        sa.Column('hipaa_relevant', sa.Boolean(), default=False),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for optimal query performance
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('idx_audit_logs_event_category', 'audit_logs', ['event_category'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_severity', 'audit_logs', ['severity'])
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_patient_id', 'audit_logs', ['patient_id'])
    op.create_index('idx_audit_logs_device_id', 'audit_logs', ['device_id'])
    op.create_index('idx_audit_logs_session_id', 'audit_logs', ['session_id'])
    
    # Create composite indexes for common query patterns
    op.create_index('idx_audit_logs_category_timestamp', 'audit_logs', ['event_category', 'timestamp'])
    op.create_index('idx_audit_logs_user_timestamp', 'audit_logs', ['user_id', 'timestamp'])
    op.create_index('idx_audit_logs_patient_timestamp', 'audit_logs', ['patient_id', 'timestamp'])
    op.create_index('idx_audit_logs_device_timestamp', 'audit_logs', ['device_id', 'timestamp'])
    op.create_index('idx_audit_logs_severity_timestamp', 'audit_logs', ['severity', 'timestamp'])
    op.create_index('idx_audit_logs_hipaa_timestamp', 'audit_logs', ['hipaa_relevant', 'timestamp'])
    
    # Convert table to hypertable for TimescaleDB time-series optimization
    op.execute("SELECT create_hypertable('audit_logs', 'timestamp');")
    
    # Create data retention policy - keep detailed logs for 7 years for HIPAA compliance
    op.execute("""
        SELECT add_retention_policy('audit_logs', INTERVAL '7 years');
    """)
    
    # Create continuous aggregate for hourly audit summaries
    op.execute("""
        CREATE MATERIALIZED VIEW audit_logs_hourly
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 hour', timestamp) AS hour,
            event_type,
            event_category,
            severity,
            COUNT(*) as event_count,
            COUNT(*) FILTER (WHERE success = false) as error_count,
            COUNT(DISTINCT user_id) as unique_users,
            COUNT(DISTINCT patient_id) as unique_patients,
            COUNT(DISTINCT device_id) as unique_devices
        FROM audit_logs
        GROUP BY hour, event_type, event_category, severity
        WITH NO DATA;
    """)
    
    # Enable real-time aggregation
    op.execute("""
        SELECT add_continuous_aggregate_policy('audit_logs_hourly',
            start_offset => INTERVAL '3 hours',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 hour');
    """)


def downgrade():
    """Drop audit logs table and related objects"""
    
    # Drop continuous aggregate policy and view
    op.execute("SELECT remove_continuous_aggregate_policy('audit_logs_hourly');")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS audit_logs_hourly;")
    
    # Drop retention policy
    op.execute("SELECT remove_retention_policy('audit_logs');")
    
    # Drop indexes
    op.drop_index('idx_audit_logs_hipaa_timestamp')
    op.drop_index('idx_audit_logs_severity_timestamp')
    op.drop_index('idx_audit_logs_device_timestamp')
    op.drop_index('idx_audit_logs_patient_timestamp')
    op.drop_index('idx_audit_logs_user_timestamp')
    op.drop_index('idx_audit_logs_category_timestamp')
    op.drop_index('idx_audit_logs_session_id')
    op.drop_index('idx_audit_logs_device_id')
    op.drop_index('idx_audit_logs_patient_id')
    op.drop_index('idx_audit_logs_user_id')
    op.drop_index('idx_audit_logs_severity')
    op.drop_index('idx_audit_logs_action')
    op.drop_index('idx_audit_logs_event_category')
    op.drop_index('idx_audit_logs_event_type')
    op.drop_index('idx_audit_logs_timestamp')
    
    # Drop table
    op.drop_table('audit_logs')