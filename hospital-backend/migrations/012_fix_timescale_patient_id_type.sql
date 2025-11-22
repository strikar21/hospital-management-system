-- Migration 012: Fix TimescaleDB patientId column type from UUID to TEXT
-- This fixes the error: "invalid UUID 'PAT0001': length must be between 32..36 characters"
--
-- Root Cause: PostgreSQL patients table uses TEXT for id, but TimescaleDB tables used UUID
-- Impact: Patient vitals queries were failing silently
-- Fix: Change patientId columns from UUID to TEXT in all TimescaleDB tables

-- ========================================
-- STEP 1: Drop existing hypertables
-- ========================================
-- Note: We need to drop and recreate because PostgreSQL doesn't allow
-- changing column type from UUID to TEXT on existing data

DROP TABLE IF EXISTS vitals_realtime CASCADE;
DROP TABLE IF EXISTS waveform_snapshots CASCADE;
DROP TABLE IF EXISTS neural_events CASCADE;

-- ========================================
-- STEP 2: Recreate vitals_realtime with TEXT patientId
-- ========================================
CREATE TABLE vitals_realtime (
    time TIMESTAMPTZ NOT NULL,
    "patientId" TEXT NOT NULL,  -- Changed from UUID to TEXT
    "deviceId" VARCHAR(50) NOT NULL,
    mode VARCHAR(10) NOT NULL CHECK (mode IN ('ecg', 'eeg')),

    -- Standard vitals
    "heartRate" INTEGER,
    "respiratoryRate" INTEGER,
    "skinTemperature" NUMERIC(4,1),
    "oxygenSaturation" INTEGER,
    "systolicPressure" INTEGER CHECK ("systolicPressure" >= 60 AND "systolicPressure" <= 200),
    "diastolicPressure" INTEGER CHECK ("diastolicPressure" >= 40 AND "diastolicPressure" <= 130),

    -- Device status
    "batteryLevel" INTEGER,
    "signalQuality" NUMERIC(3,2),

    -- ECG metrics
    "rrInterval" INTEGER,
    "qrsDuration" INTEGER,
    "qtInterval" INTEGER,
    axis INTEGER,
    rhythm VARCHAR(50),
    "stSegment" VARCHAR(20),

    -- EEG metrics
    "alphaPower" NUMERIC(5,2),
    "betaPower" NUMERIC(5,2),
    "thetaPower" NUMERIC(5,2),
    "deltaPower" NUMERIC(5,2),
    "gammaPower" NUMERIC(5,2),
    "dominantFrequency" NUMERIC(5,2),
    "seizureActivity" BOOLEAN,

    -- New sensor vitals (v5.2.13+)
    tremor NUMERIC(4,2) CHECK (tremor >= 0.0 AND tremor <= 10.0),
    bioimpedance NUMERIC(5,2) CHECK (bioimpedance >= 20.0 AND bioimpedance <= 50.0),
    "imuFallRisk" NUMERIC(4,2) CHECK ("imuFallRisk" >= 0.0 AND "imuFallRisk" <= 10.0),
    "perfusionIndex" NUMERIC(5,2) CHECK ("perfusionIndex" >= 0.0 AND "perfusionIndex" <= 20.0),
    "stepCount" INTEGER,
    "watchWorn" BOOLEAN,
    "lastMovementTime" INTEGER,

    -- Metadata
    quality JSONB,
    sequence INTEGER,
    metadata JSONB
);

-- Convert to hypertable
SELECT create_hypertable('vitals_realtime', 'time', if_not_exists => TRUE);

-- Create performance indexes
CREATE INDEX idx_vitals_realtime_patient_time ON vitals_realtime ("patientId", time DESC);
CREATE INDEX idx_vitals_realtime_device_time ON vitals_realtime ("deviceId", time DESC);
CREATE INDEX idx_vitals_tremor ON vitals_realtime ("patientId", tremor) WHERE tremor > 5.0;
CREATE INDEX idx_vitals_fall_risk ON vitals_realtime ("patientId", "imuFallRisk") WHERE "imuFallRisk" > 7.0;
CREATE INDEX idx_vitals_perfusion ON vitals_realtime ("patientId", "perfusionIndex") WHERE "perfusionIndex" < 0.5;
CREATE INDEX idx_vitals_watch_off ON vitals_realtime ("patientId", "watchWorn", time) WHERE "watchWorn" = false;
CREATE INDEX idx_vitals_bp ON vitals_realtime ("patientId", "systolicPressure", "diastolicPressure") WHERE "systolicPressure" IS NOT NULL;

-- ========================================
-- STEP 3: Recreate waveform_snapshots with TEXT patientId
-- ========================================
CREATE TABLE waveform_snapshots (
    time TIMESTAMPTZ NOT NULL,
    "patientId" TEXT NOT NULL,  -- Changed from UUID to TEXT
    "deviceId" VARCHAR(50) NOT NULL,
    mode VARCHAR(10) NOT NULL CHECK (mode IN ('ecg', 'eeg')),
    "sampleRate" INTEGER NOT NULL,
    duration NUMERIC(5,2) NOT NULL,

    -- ECG channels (JSONB arrays of samples)
    "ecgLimbLeads" JSONB,
    "ecgPrecordialLeads" JSONB,
    "ecgDerivedLeads" JSONB,
    "ecgEvents" JSONB,

    -- EEG channels (JSONB arrays of samples)
    "eegFrontalChannels" JSONB,
    "eegCentralChannels" JSONB,
    "eegOccipitalChannels" JSONB,
    "eegAnalysis" JSONB,

    -- Metadata
    quality JSONB,
    sequence INTEGER,
    compression VARCHAR(20),
    metadata JSONB
);

-- Convert to hypertable
SELECT create_hypertable('waveform_snapshots', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX idx_waveform_snapshots_patient_mode_time ON waveform_snapshots ("patientId", mode, time DESC);
CREATE INDEX idx_waveform_snapshots_device_time ON waveform_snapshots ("deviceId", time DESC);
CREATE INDEX idx_waveform_snapshots_mode_time ON waveform_snapshots (mode, time DESC);

-- ========================================
-- STEP 4: Recreate neural_events with TEXT patientId
-- ========================================
CREATE TABLE neural_events (
    time TIMESTAMPTZ NOT NULL,
    "patientId" TEXT NOT NULL,  -- Changed from UUID to TEXT
    "deviceId" VARCHAR(50) NOT NULL,
    "eventType" VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    confidence NUMERIC(3,2) NOT NULL,
    mode VARCHAR(10) NOT NULL CHECK (mode IN ('ecg', 'eeg')),

    -- Event details
    "sampleRate" INTEGER,
    duration NUMERIC(5,2),
    context JSONB,
    waveform JSONB,
    actions JSONB,

    -- Resolution tracking
    acknowledged BOOLEAN DEFAULT false,
    "acknowledgedBy" VARCHAR(100),
    "acknowledgedAt" TIMESTAMPTZ,
    resolved BOOLEAN DEFAULT false,
    "resolvedAt" TIMESTAMPTZ,

    metadata JSONB
);

-- Convert to hypertable
SELECT create_hypertable('neural_events', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX idx_neural_events_patient_time ON neural_events ("patientId", time DESC);
CREATE INDEX idx_neural_events_type_severity ON neural_events ("eventType", severity, time DESC);
CREATE INDEX idx_neural_events_unresolved ON neural_events (resolved, time DESC) WHERE NOT resolved;

-- ========================================
-- VERIFICATION
-- ========================================
-- Check column types
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name IN ('vitals_realtime', 'waveform_snapshots', 'neural_events')
    AND column_name = 'patientId'
ORDER BY table_name;

-- Expected output:
--     table_name      | column_name | data_type
-- --------------------+-------------+-----------
--  neural_events      | patientId   | text
--  vitals_realtime    | patientId   | text
--  waveform_snapshots | patientId   | text
