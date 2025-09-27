-- Hospital Management System - Production Database Initialization
-- This script sets up the production database with proper security and performance configurations

-- Create extensions for security and performance
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create application user if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'hospital_app') THEN
        CREATE ROLE hospital_app WITH LOGIN ENCRYPTED PASSWORD 'hospital_app_secure_2024';
    END IF;
END
$$;

-- Grant necessary permissions to application user
GRANT CONNECT ON DATABASE hospitaldb TO hospital_app;
GRANT USAGE ON SCHEMA public TO hospital_app;
GRANT CREATE ON SCHEMA public TO hospital_app;

-- Set up row-level security for HIPAA compliance
ALTER DATABASE hospitaldb SET row_security = on;

-- Performance optimization settings
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;

-- Security settings
ALTER SYSTEM SET ssl = 'on';
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';
ALTER SYSTEM SET log_checkpoints = 'on';
ALTER SYSTEM SET log_lock_waits = 'on';
ALTER SYSTEM SET log_statement = 'mod';
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- Audit logging for HIPAA compliance
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';
ALTER SYSTEM SET log_statement_stats = 'off';
ALTER SYSTEM SET log_parser_stats = 'off';
ALTER SYSTEM SET log_planner_stats = 'off';
ALTER SYSTEM SET log_executor_stats = 'off';

-- Create audit schema for compliance
CREATE SCHEMA IF NOT EXISTS audit;

-- Create audit function for tracking changes
CREATE OR REPLACE FUNCTION audit.audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit.audit_log (
            schema_name,
            table_name,
            operation,
            old_values,
            new_values,
            user_name,
            timestamp,
            client_addr
        ) VALUES (
            TG_TABLE_SCHEMA,
            TG_TABLE_NAME,
            TG_OP,
            row_to_json(OLD),
            NULL,
            current_user,
            current_timestamp,
            inet_client_addr()
        );
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit.audit_log (
            schema_name,
            table_name,
            operation,
            old_values,
            new_values,
            user_name,
            timestamp,
            client_addr
        ) VALUES (
            TG_TABLE_SCHEMA,
            TG_TABLE_NAME,
            TG_OP,
            row_to_json(OLD),
            row_to_json(NEW),
            current_user,
            current_timestamp,
            inet_client_addr()
        );
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit.audit_log (
            schema_name,
            table_name,
            operation,
            old_values,
            new_values,
            user_name,
            timestamp,
            client_addr
        ) VALUES (
            TG_TABLE_SCHEMA,
            TG_TABLE_NAME,
            TG_OP,
            NULL,
            row_to_json(NEW),
            current_user,
            current_timestamp,
            inet_client_addr()
        );
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit.audit_log (
    id SERIAL PRIMARY KEY,
    schema_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    old_values JSONB,
    new_values JSONB,
    user_name TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    client_addr INET
);

-- Create indexes for audit log performance
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit.audit_log (timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_table ON audit.audit_log (schema_name, table_name);
CREATE INDEX IF NOT EXISTS idx_audit_log_operation ON audit.audit_log (operation);

-- Grant permissions to application user for audit schema
GRANT USAGE ON SCHEMA audit TO hospital_app;
GRANT INSERT ON TABLE audit.audit_log TO hospital_app;
GRANT SELECT ON TABLE audit.audit_log TO hospital_app;

-- Create function to add audit triggers to tables
CREATE OR REPLACE FUNCTION audit.add_audit_trigger(target_table TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE format('
        CREATE TRIGGER %I_audit_trigger
        AFTER INSERT OR UPDATE OR DELETE ON %I
        FOR EACH ROW EXECUTE FUNCTION audit.audit_trigger();
    ', target_table, target_table);
END;
$$ LANGUAGE plpgsql;

-- Message indicating successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Hospital Management System - Production database initialized successfully';
    RAISE NOTICE 'HIPAA audit logging enabled';
    RAISE NOTICE 'Performance optimizations applied';
    RAISE NOTICE 'Security settings configured';
END
$$;