-- Migration 013: Create FHIR R5 Observations in TimescaleDB
-- Purpose: Time-series storage for vitals with AI analysis context
-- Date: 2025-11-18
-- Database: TimescaleDB (hospitaltimescale)

-- ============================================================================
-- FHIR R5 Observation Resource (Vitals Time-Series)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fhir_observations (
    id UUID DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,  -- effectiveDateTime from FHIR
    resource JSONB NOT NULL,

    -- Patient & Device references
    patientContextId UUID NOT NULL,  -- References patient_clinical_context in main DB
    deviceId UUID NOT NULL,  -- References fhir_devices in main DB
    abhaNumber TEXT,  -- Denormalized for fast queries

    -- Observation classification
    category TEXT NOT NULL DEFAULT 'vital-signs',  -- vital-signs, laboratory, imaging, etc.
    code TEXT NOT NULL,  -- LOINC code: 8867-4 (heart-rate), 2708-6 (spo2), etc.
    codeDisplay TEXT,  -- "Heart rate", "Oxygen saturation"

    -- Value (extracted from FHIR for fast queries)
    valueQuantity NUMERIC,  -- 72, 98, 37.5
    valueUnit TEXT,  -- beats/min, %, °C
    valueString TEXT,  -- For non-numeric observations

    -- Status
    status TEXT DEFAULT 'final',  -- registered, preliminary, final, amended, corrected, cancelled

    -- AI Analysis Results (added by your system)
    aiAnalysis JSONB DEFAULT '{}',  -- {"severity": "normal", "trend": "stable", "alerts": []}
    isAbnormal BOOLEAN DEFAULT false,
    alertGenerated BOOLEAN DEFAULT false,

    -- Quality indicators
    dataQuality TEXT DEFAULT 'good',  -- good, questionable, artifact, sensor-error
    signalStrength INTEGER,  -- 0-100 for wireless devices

    PRIMARY KEY (id, timestamp)
);

-- Convert to hypertable (partitioned by time)
SELECT create_hypertable('fhir_observations', 'timestamp', if_not_exists => TRUE);

-- ============================================================================
-- Indexes for Fast Time-Series Queries
-- ============================================================================

-- Patient vitals queries (most common)
CREATE INDEX IF NOT EXISTS idx_fhir_obs_patient_time ON fhir_observations(patientContextId, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_obs_abha_time ON fhir_observations(abhaNumber, timestamp DESC) WHERE abhaNumber IS NOT NULL;

-- Device data queries
CREATE INDEX IF NOT EXISTS idx_fhir_obs_device_time ON fhir_observations(deviceId, timestamp DESC);

-- Vital type queries (e.g., all heart rate readings)
CREATE INDEX IF NOT EXISTS idx_fhir_obs_code_time ON fhir_observations(code, timestamp DESC);

-- Alert queries
CREATE INDEX IF NOT EXISTS idx_fhir_obs_abnormal ON fhir_observations(patientContextId, timestamp DESC) WHERE isAbnormal = true;
CREATE INDEX IF NOT EXISTS idx_fhir_obs_alerts ON fhir_observations(timestamp DESC) WHERE alertGenerated = true;

-- FHIR resource full-text search
CREATE INDEX IF NOT EXISTS idx_fhir_obs_resource ON fhir_observations USING GIN(resource);

-- AI analysis search
CREATE INDEX IF NOT EXISTS idx_fhir_obs_ai_analysis ON fhir_observations USING GIN(aiAnalysis);

-- ============================================================================
-- Continuous Aggregates (Pre-computed for Performance)
-- ============================================================================

-- 1-minute aggregates for real-time dashboards
CREATE MATERIALIZED VIEW IF NOT EXISTS fhir_observations_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', timestamp) AS bucket,
    patientContextId,
    deviceId,
    code,
    COUNT(*) AS reading_count,
    AVG(valueQuantity) AS avg_value,
    MIN(valueQuantity) AS min_value,
    MAX(valueQuantity) AS max_value,
    STDDEV(valueQuantity) AS stddev_value,
    SUM(CASE WHEN isAbnormal THEN 1 ELSE 0 END) AS abnormal_count
FROM fhir_observations
WHERE valueQuantity IS NOT NULL
GROUP BY bucket, patientContextId, deviceId, code;

-- Refresh policy: update every 1 minute
SELECT add_continuous_aggregate_policy('fhir_observations_1min',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE
);

-- 1-hour aggregates for historical analysis
CREATE MATERIALIZED VIEW IF NOT EXISTS fhir_observations_1hour
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS bucket,
    patientContextId,
    deviceId,
    code,
    COUNT(*) AS reading_count,
    AVG(valueQuantity) AS avg_value,
    MIN(valueQuantity) AS min_value,
    MAX(valueQuantity) AS max_value,
    STDDEV(valueQuantity) AS stddev_value,
    SUM(CASE WHEN isAbnormal THEN 1 ELSE 0 END) AS abnormal_count,
    SUM(CASE WHEN alertGenerated THEN 1 ELSE 0 END) AS alert_count
FROM fhir_observations
WHERE valueQuantity IS NOT NULL
GROUP BY bucket, patientContextId, deviceId, code;

-- Refresh policy: update every 10 minutes
SELECT add_continuous_aggregate_policy('fhir_observations_1hour',
    start_offset => INTERVAL '1 week',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '10 minutes',
    if_not_exists => TRUE
);

-- ============================================================================
-- Retention Policy (Auto-delete old data)
-- ============================================================================

-- Keep raw data for 90 days (configurable)
SELECT add_retention_policy('fhir_observations',
    drop_after => INTERVAL '90 days',
    if_not_exists => TRUE
);

-- Keep 1-minute aggregates for 30 days
SELECT add_retention_policy('fhir_observations_1min',
    drop_after => INTERVAL '30 days',
    if_not_exists => TRUE
);

-- Keep 1-hour aggregates for 1 year
SELECT add_retention_policy('fhir_observations_1hour',
    drop_after => INTERVAL '1 year',
    if_not_exists => TRUE
);

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Get latest vitals for a patient
CREATE OR REPLACE FUNCTION get_latest_vitals(patient_context_id UUID)
RETURNS TABLE (
    code TEXT,
    codeDisplay TEXT,
    value NUMERIC,
    unit TEXT,
    obs_timestamp TIMESTAMPTZ,
    isAbnormal BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT ON (o.code)
        o.code,
        o.codeDisplay,
        o.valueQuantity,
        o.valueUnit,
        o.timestamp,
        o.isAbnormal
    FROM fhir_observations o
    WHERE o.patientContextId = patient_context_id
      AND o.status = 'final'
      AND o.valueQuantity IS NOT NULL
    ORDER BY o.code, o.timestamp DESC;
END;
$$ LANGUAGE plpgsql;

-- Get vitals trend (last N hours)
CREATE OR REPLACE FUNCTION get_vitals_trend(
    patient_context_id UUID,
    vital_code TEXT,
    hours_back INTEGER DEFAULT 24
)
RETURNS TABLE (
    obs_timestamp TIMESTAMPTZ,
    value NUMERIC,
    unit TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        o.timestamp,
        o.valueQuantity,
        o.valueUnit
    FROM fhir_observations o
    WHERE o.patientContextId = patient_context_id
      AND o.code = vital_code
      AND o.timestamp >= NOW() - (hours_back || ' hours')::INTERVAL
      AND o.status = 'final'
    ORDER BY o.timestamp ASC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Verification
-- ============================================================================
SELECT 'FHIR R5 Observations hypertable created successfully' as status;

SELECT * FROM timescaledb_information.hypertables
WHERE hypertable_name = 'fhir_observations';

SELECT * FROM timescaledb_information.continuous_aggregates
WHERE view_name IN ('fhir_observations_1min', 'fhir_observations_1hour');
