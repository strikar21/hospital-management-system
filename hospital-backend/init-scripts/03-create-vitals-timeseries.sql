-- Vitals TimeSeries Table for ESP32 Watch Data
-- Created: 2025-10-07
-- Purpose: Store real-time vitals data from ESP32 watches in time-series format

-- ============================================
-- TABLE CREATION
-- ============================================

CREATE TABLE IF NOT EXISTS public.vitals_timeseries (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50),
    vitaltype VARCHAR(50) NOT NULL,  -- 'ecg', 'heartrate', 'oxygensaturation', 'temperature', etc.
    value DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20),
    quality INTEGER DEFAULT 95,  -- Signal quality percentage (0-100)
    metadata JSONB  -- Additional data like signal artifacts, confidence, etc.
);

-- ============================================
-- TIMESCALEDB HYPERTABLE
-- ============================================

-- Convert to hypertable for time-series optimization
-- Chunk size: 1 hour (optimized for real-time monitoring)
SELECT create_hypertable('vitals_timeseries', 'time',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Patient + Time index (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_vitals_ts_patient_time
    ON vitals_timeseries ("patientId", time DESC);

-- Vital Type + Patient + Time index (for specific vital queries)
CREATE INDEX IF NOT EXISTS idx_vitals_ts_vitaltype
    ON vitals_timeseries (vitaltype, "patientId", time DESC);

-- Device + Time index (for device monitoring)
CREATE INDEX IF NOT EXISTS idx_vitals_ts_device_time
    ON vitals_timeseries ("deviceId", time DESC);

-- ============================================
-- COMPRESSION POLICY
-- ============================================

-- Compress data older than 24 hours to save storage
-- Compressed chunks are read-only but significantly smaller
SELECT add_compression_policy('vitals_timeseries', INTERVAL '24 hours', if_not_exists => true);

-- ============================================
-- RETENTION POLICY
-- ============================================

-- Keep data for 7 years (compliant with Medical Council of India regulations)
-- After 7 years, data is automatically purged
SELECT add_retention_policy('vitals_timeseries', INTERVAL '7 years', if_not_exists => true);

-- ============================================
-- PERMISSIONS
-- ============================================

-- Grant permissions to application user
GRANT SELECT, INSERT, UPDATE, DELETE ON vitals_timeseries TO hospital_user;

-- ============================================
-- SUCCESS MESSAGE
-- ============================================

DO $$
BEGIN
    RAISE NOTICE 'vitals_timeseries table created successfully';
    RAISE NOTICE 'TimescaleDB hypertable configured with 1-hour chunks';
    RAISE NOTICE 'Compression policy: 24 hours';
    RAISE NOTICE 'Retention policy: 7 years';
END
$$;
