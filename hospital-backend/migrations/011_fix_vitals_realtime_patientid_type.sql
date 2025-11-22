-- Migration 011: Fix vitals_realtime.patientId type from UUID to TEXT
-- Date: 2025-11-19
-- Reason: Schema mismatch - PostgreSQL patients.id is TEXT ("PAT0001"), but TimescaleDB vitals_realtime.patientId is UUID
-- Impact: Outbreak detection broken, system-level alerts non-functional
-- Fix: Convert patientId column from UUID to TEXT to align with patients table

-- IMPORTANT: This migration runs on TimescaleDB (port 5433, database: hospitaltimescale)

-- Step 1: Drop existing vitals_realtime table and recreate with correct schema
-- Reason: Existing data has UUID patient IDs that don't match any patients in PostgreSQL
--         All 533,946 rows are orphaned (no matching patients exist)
--         Clean slate is better than trying to migrate invalid data

DROP TABLE IF EXISTS vitals_realtime CASCADE;

-- Step 2: Recreate vitals_realtime table with TEXT patientId (camelCase columns)
CREATE TABLE vitals_realtime (
    time TIMESTAMPTZ NOT NULL,
    "patientId" TEXT NOT NULL,
    "deviceId" VARCHAR(100) NOT NULL,
    mode VARCHAR(20),

    -- Core vitals
    "heartRate" INTEGER,
    "respiratoryRate" INTEGER,
    "skinTemperature" NUMERIC(4, 1),
    "oxygenSaturation" INTEGER,
    "batteryLevel" INTEGER,
    "signalQuality" NUMERIC(4, 2),

    -- ECG metrics
    "rrInterval" INTEGER,
    "qrsDuration" INTEGER,
    "qtInterval" INTEGER,
    axis INTEGER,
    rhythm VARCHAR(50),
    "stSegment" VARCHAR(50),

    -- EEG/Neural metrics
    "alphaPower" NUMERIC(10, 4),
    "betaPower" NUMERIC(10, 4),
    "thetaPower" NUMERIC(10, 4),
    "deltaPower" NUMERIC(10, 4),
    "gammaPower" NUMERIC(10, 4),
    "dominantFrequency" NUMERIC(6, 2),
    "seizureActivity" BOOLEAN DEFAULT FALSE,

    -- Quality/metadata
    quality JSONB,
    sequence INTEGER,
    metadata JSONB,

    -- Blood pressure (NIBP)
    "systolicPressure" INTEGER,
    "diastolicPressure" INTEGER,

    -- Additional sensors
    tremor NUMERIC(6, 3),
    bioimpedance NUMERIC(10, 2),
    "imuFallRisk" NUMERIC(4, 2),
    "perfusionIndex" NUMERIC(5, 2),
    "stepCount" INTEGER,
    "watchWorn" BOOLEAN DEFAULT TRUE,
    "lastMovementTime" INTEGER
);

-- Step 3: Convert to TimescaleDB hypertable
SELECT create_hypertable('vitals_realtime', 'time', if_not_exists => TRUE);

-- Step 4: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_vitals_realtime_patient_time
    ON vitals_realtime ("patientId", time DESC);

CREATE INDEX IF NOT EXISTS idx_vitals_realtime_device_time
    ON vitals_realtime ("deviceId", time DESC);

-- Step 5: Set compression policy (compress data older than 7 days)
ALTER TABLE vitals_realtime SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = '"patientId", "deviceId"'
);

SELECT add_compression_policy('vitals_realtime', INTERVAL '7 days', if_not_exists => TRUE);

-- Step 6: Set retention policy (keep data for 90 days)
SELECT add_retention_policy('vitals_realtime', INTERVAL '90 days', if_not_exists => TRUE);

-- Verification queries (run manually after migration):
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'vitals_realtime' AND column_name = 'patientId';
-- Should return: patientId | text
