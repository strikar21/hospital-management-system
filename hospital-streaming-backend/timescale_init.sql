-- TimescaleDB initialization for hospital vitals data
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create hypertable for vital readings
CREATE TABLE IF NOT EXISTS vitalReadings (
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deviceId TEXT NOT NULL,
    patientId TEXT NOT NULL,
    vitalType TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT,
    qualityIndicator TEXT,
    metadata JSONB,
    PRIMARY KEY (timestamp, deviceId, vitalType)
);

-- Convert to hypertable (TimescaleDB)
SELECT create_hypertable('vitalReadings', 'timestamp', if_not_exists => TRUE);

-- Create hypertable for device alerts
CREATE TABLE IF NOT EXISTS deviceAlertsTs (
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deviceId TEXT NOT NULL,
    patientId TEXT,
    alertType TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT,
    resolvedAt TIMESTAMPTZ,
    acknowledged BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    PRIMARY KEY (timestamp, deviceId, alertType)
);

SELECT create_hypertable('deviceAlertsTs', 'timestamp', if_not_exists => TRUE);

-- Create hypertable for device status logs
CREATE TABLE IF NOT EXISTS deviceStatusLog (
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deviceId TEXT NOT NULL,
    status TEXT NOT NULL,
    batteryLevel INTEGER,
    signalStrength INTEGER,
    metadata JSONB,
    PRIMARY KEY (timestamp, deviceId)
);

SELECT create_hypertable('deviceStatusLog', 'timestamp', if_not_exists => TRUE);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_vitalReadings_device_time ON vitalReadings (deviceId, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vitalReadings_patient_time ON vitalReadings (patientId, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vitalReadings_type_time ON vitalReadings (vitalType, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_deviceAlerts_device_time ON deviceAlertsTs (deviceId, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_deviceAlerts_severity_time ON deviceAlertsTs (severity, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_deviceStatus_device_time ON deviceStatusLog (deviceId, timestamp DESC);

-- Create continuous aggregates for common queries
CREATE MATERIALIZED VIEW IF NOT EXISTS vitalReadingsHourly
WITH (timescaledb.continuous) AS
SELECT
    deviceId,
    patientId,
    vitalType,
    time_bucket('1 hour', timestamp) AS bucket,
    AVG(value) AS avgValue,
    MIN(value) AS minValue,
    MAX(value) AS maxValue,
    COUNT(*) AS readingCount
FROM vitalReadings
GROUP BY deviceId, patientId, vitalType, bucket;

-- Enable automatic refresh for the continuous aggregate
SELECT add_continuous_aggregate_policy('vitalReadingsHourly',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- Data retention policy (optional - keeps 1 year of raw data)
-- Uncomment if you want automatic data cleanup
-- SELECT add_retention_policy('vitalReadings', INTERVAL '1 year', if_not_exists => TRUE);
-- SELECT add_retention_policy('deviceAlertsTs', INTERVAL '2 years', if_not_exists => TRUE);
-- SELECT add_retention_policy('deviceStatusLog', INTERVAL '6 months', if_not_exists => TRUE);

-- Create view for latest vital readings per device
CREATE OR REPLACE VIEW latestVitals AS
SELECT DISTINCT ON (deviceId, vitalType)
    deviceId,
    patientId,
    vitalType,
    value,
    unit,
    timestamp,
    qualityIndicator
FROM vitalReadings
ORDER BY deviceId, vitalType, timestamp DESC;

-- TimescaleDB hypertables ready for real-time vital signs data