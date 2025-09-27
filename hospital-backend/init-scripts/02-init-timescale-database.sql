-- TimescaleDB Initialization for Hospital Management System
-- Optimized for time-series patient vital signs data

-- Create TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create application user if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'timescale_app') THEN
        CREATE ROLE timescale_app WITH LOGIN ENCRYPTED PASSWORD 'timescale_app_secure_2024';
    END IF;
END
$$;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE hospital_timeseries TO timescale_app;
GRANT USAGE ON SCHEMA public TO timescale_app;
GRANT CREATE ON SCHEMA public TO timescale_app;

-- Performance optimizations for time-series data
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET shared_buffers = '128MB';
ALTER SYSTEM SET effective_cache_size = '512MB';
ALTER SYSTEM SET maintenance_work_mem = '32MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '8MB';

-- TimescaleDB specific settings
ALTER SYSTEM SET timescaledb.max_background_workers = 8;
ALTER SYSTEM SET timescaledb.restoring = 'off';

-- Create vital signs table optimized for time-series data
CREATE TABLE IF NOT EXISTS public.vital_signs (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50),
    "heartRate" INTEGER,
    "bloodPressureSystolic" INTEGER,
    "bloodPressureDiastolic" INTEGER,
    "oxygenSaturation" DECIMAL(5,2),
    "bodyTemperature" DECIMAL(4,1),
    "respiratoryRate" INTEGER,
    "bloodGlucose" DECIMAL(5,1),
    "ecgData" JSONB,
    "alertLevel" VARCHAR(20) DEFAULT 'normal',
    "dataQuality" VARCHAR(20) DEFAULT 'good',
    metadata JSONB
);

-- Convert to hypertable (time-series optimization)
SELECT create_hypertable('vital_signs', 'time',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_vital_signs_patient_time
    ON vital_signs ("patientId", time DESC);
CREATE INDEX IF NOT EXISTS idx_vital_signs_device_time
    ON vital_signs ("deviceId", time DESC);
CREATE INDEX IF NOT EXISTS idx_vital_signs_alert_level
    ON vital_signs ("alertLevel", time DESC);

-- Create compression policy for older data
SELECT add_compression_policy('vital_signs', INTERVAL '24 hours', if_not_exists => true);

-- Create retention policy for data management (keep 7 years for HIPAA)
SELECT add_retention_policy('vital_signs', INTERVAL '7 years', if_not_exists => true);

-- Create continuous aggregates for real-time analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS vital_signs_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    "patientId",
    "deviceId",
    AVG("heartRate") as avg_heart_rate,
    MAX("heartRate") as max_heart_rate,
    MIN("heartRate") as min_heart_rate,
    AVG("bloodPressureSystolic") as avg_bp_systolic,
    AVG("bloodPressureDiastolic") as avg_bp_diastolic,
    AVG("oxygenSaturation") as avg_oxygen_saturation,
    AVG("bodyTemperature") as avg_body_temperature,
    AVG("respiratoryRate") as avg_respiratory_rate,
    COUNT(*) as reading_count
FROM vital_signs
GROUP BY bucket, "patientId", "deviceId";

-- Add refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('vital_signs_1min',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => true);

-- Create hourly aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS vital_signs_1hour
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    "patientId",
    AVG("heartRate") as avg_heart_rate,
    MAX("heartRate") as max_heart_rate,
    MIN("heartRate") as min_heart_rate,
    AVG("bloodPressureSystolic") as avg_bp_systolic,
    AVG("bloodPressureDiastolic") as avg_bp_diastolic,
    AVG("oxygenSaturation") as avg_oxygen_saturation,
    AVG("bodyTemperature") as avg_body_temperature,
    AVG("respiratoryRate") as avg_respiratory_rate,
    COUNT(*) as reading_count
FROM vital_signs
GROUP BY bucket, "patientId";

-- Add refresh policy for hourly aggregate
SELECT add_continuous_aggregate_policy('vital_signs_1hour',
    start_offset => INTERVAL '24 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => true);

-- Create device status table for IoT monitoring
CREATE TABLE IF NOT EXISTS public.device_status (
    time TIMESTAMPTZ NOT NULL,
    "deviceId" VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    "batteryLevel" INTEGER,
    "signalStrength" INTEGER,
    "lastHeartbeat" TIMESTAMPTZ,
    location JSONB,
    metadata JSONB
);

-- Convert device status to hypertable
SELECT create_hypertable('device_status', 'time',
    chunk_time_interval => INTERVAL '6 hours',
    if_not_exists => TRUE
);

-- Create indexes for device status
CREATE INDEX IF NOT EXISTS idx_device_status_device_time
    ON device_status ("deviceId", time DESC);
CREATE INDEX IF NOT EXISTS idx_device_status_status
    ON device_status (status, time DESC);

-- Create alert events table
CREATE TABLE IF NOT EXISTS public.alert_events (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50),
    "alertType" VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT,
    "triggerValue" DECIMAL,
    "thresholdValue" DECIMAL,
    acknowledged BOOLEAN DEFAULT FALSE,
    "acknowledgedBy" VARCHAR(100),
    "acknowledgedAt" TIMESTAMPTZ,
    resolved BOOLEAN DEFAULT FALSE,
    "resolvedAt" TIMESTAMPTZ,
    metadata JSONB
);

-- Convert alert events to hypertable
SELECT create_hypertable('alert_events', 'time',
    chunk_time_interval => INTERVAL '24 hours',
    if_not_exists => TRUE
);

-- Create indexes for alert events
CREATE INDEX IF NOT EXISTS idx_alert_events_patient_time
    ON alert_events ("patientId", time DESC);
CREATE INDEX IF NOT EXISTS idx_alert_events_type_severity
    ON alert_events ("alertType", severity, time DESC);
CREATE INDEX IF NOT EXISTS idx_alert_events_unresolved
    ON alert_events (resolved, time DESC) WHERE NOT resolved;

-- Grant permissions to application user
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO timescale_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO timescale_app;

-- Create function for real-time vital signs alerts
CREATE OR REPLACE FUNCTION check_vital_signs_alerts()
RETURNS TRIGGER AS $$
DECLARE
    alert_msg TEXT;
    alert_type TEXT;
    alert_severity TEXT;
BEGIN
    -- Check heart rate alerts
    IF NEW."heartRate" IS NOT NULL THEN
        IF NEW."heartRate" > 120 OR NEW."heartRate" < 50 THEN
            alert_type := 'heart_rate_abnormal';
            alert_severity := CASE
                WHEN NEW."heartRate" > 150 OR NEW."heartRate" < 40 THEN 'critical'
                ELSE 'warning'
            END;
            alert_msg := format('Heart rate: %s BPM', NEW."heartRate");

            INSERT INTO alert_events (
                time, "patientId", "deviceId", "alertType",
                severity, message, "triggerValue"
            ) VALUES (
                NEW.time, NEW."patientId", NEW."deviceId",
                alert_type, alert_severity, alert_msg, NEW."heartRate"
            );
        END IF;
    END IF;

    -- Check oxygen saturation alerts
    IF NEW."oxygenSaturation" IS NOT NULL AND NEW."oxygenSaturation" < 95 THEN
        alert_type := 'oxygen_saturation_low';
        alert_severity := CASE
            WHEN NEW."oxygenSaturation" < 90 THEN 'critical'
            ELSE 'warning'
        END;
        alert_msg := format('Oxygen saturation: %s%%', NEW."oxygenSaturation");

        INSERT INTO alert_events (
            time, "patientId", "deviceId", "alertType",
            severity, message, "triggerValue"
        ) VALUES (
            NEW.time, NEW."patientId", NEW."deviceId",
            alert_type, alert_severity, alert_msg, NEW."oxygenSaturation"
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for real-time alerts
CREATE TRIGGER vital_signs_alert_trigger
    AFTER INSERT ON vital_signs
    FOR EACH ROW EXECUTE FUNCTION check_vital_signs_alerts();

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'TimescaleDB for Hospital Management System initialized successfully';
    RAISE NOTICE 'Hypertables created for time-series optimization';
    RAISE NOTICE 'Continuous aggregates configured for real-time analytics';
    RAISE NOTICE 'Real-time alert system enabled';
END
$$;