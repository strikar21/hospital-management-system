-- Migration 010: Create Neural Waveform Tables (8-12 Channel ECG/EEG)
-- Purpose: Store multi-channel ECG/EEG waveform data with TimescaleDB optimization
-- Date: 2025-10-15

-- ============================================
-- WAVEFORM SNAPSHOTS TABLE (Main Storage)
-- ============================================
CREATE TABLE IF NOT EXISTS public.waveform_snapshots (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50) NOT NULL,
    mode VARCHAR(10) NOT NULL,  -- 'ecg' or 'eeg'
    "sampleRate" INTEGER NOT NULL,
    duration INTEGER NOT NULL,  -- seconds

    -- ECG channels (12-lead) - stored as JSONB for flexibility
    "ecgLimbLeads" JSONB,        -- {leadI: {baseline, deltas}, leadII, leadIII}
    "ecgPrecordialLeads" JSONB,  -- {v1: {baseline, deltas}, v2, v3, v4, v5}
    "ecgDerivedLeads" JSONB,     -- {aVR, aVL, aVF, v6}
    "ecgEvents" JSONB,           -- [{timestamp, type, confidence, location}]

    -- EEG channels (8-channel) - stored as JSONB
    "eegFrontalChannels" JSONB,  -- {Fp1, Fp2, F3, F4}
    "eegCentralChannels" JSONB,  -- {C3, C4}
    "eegOccipitalChannels" JSONB, -- {O1, O2}
    "eegAnalysis" JSONB,         -- {bandPowers, asymmetry, dominantFrequency}

    -- Quality metrics
    quality JSONB,               -- {overall, leadOff, noise, impedance}

    -- Metadata
    sequence INTEGER,
    compression VARCHAR(20),
    metadata JSONB,

    -- Constraints
    CONSTRAINT waveform_mode_check CHECK (mode IN ('ecg', 'eeg'))
);

-- Convert to hypertable for time-series optimization (optional - requires TimescaleDB extension)
DO $$
BEGIN
    -- Check if TimescaleDB extension exists
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('waveform_snapshots', 'time',
            chunk_time_interval => INTERVAL '1 hour',
            if_not_exists => TRUE
        );
        RAISE NOTICE 'waveform_snapshots converted to hypertable';
    ELSE
        RAISE NOTICE 'TimescaleDB not available - using regular table for waveform_snapshots';
    END IF;
END $$;

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_waveform_snapshots_patient_mode_time
    ON waveform_snapshots ("patientId", mode, time DESC);

CREATE INDEX IF NOT EXISTS idx_waveform_snapshots_device_time
    ON waveform_snapshots ("deviceId", time DESC);

CREATE INDEX IF NOT EXISTS idx_waveform_snapshots_mode_time
    ON waveform_snapshots (mode, time DESC);

-- ============================================
-- COMPRESSION AND RETENTION POLICIES
-- ============================================
-- Note: Compression policies require columnstore to be enabled first
-- This can be done later if needed with:
-- ALTER TABLE waveform_snapshots SET (timescaledb.compress);
-- SELECT add_compression_policy('waveform_snapshots', INTERVAL '24 hours');

-- Retention policy - keep data for 7 years (HIPAA compliance)
DO $$
BEGIN
    PERFORM add_retention_policy('waveform_snapshots', INTERVAL '7 years', if_not_exists => true);
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Could not add retention policy to waveform_snapshots: %', SQLERRM;
END $$;

-- ============================================
-- REAL-TIME VITALS TABLE (High-Frequency Updates)
-- ============================================
CREATE TABLE IF NOT EXISTS public.vitals_realtime (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50) NOT NULL,
    mode VARCHAR(10) NOT NULL,

    -- Basic vitals
    "heartRate" INTEGER,
    "respiratoryRate" INTEGER,
    "skinTemperature" DECIMAL(4,1),
    "oxygenSaturation" INTEGER,
    "batteryLevel" INTEGER,
    "signalQuality" DECIMAL(3,2),

    -- ECG analysis
    "rrInterval" INTEGER,
    "qrsDuration" INTEGER,
    "qtInterval" INTEGER,
    axis INTEGER,
    rhythm VARCHAR(50),
    "stSegment" VARCHAR(20),

    -- EEG analysis
    "alphaPower" DECIMAL(5,2),
    "betaPower" DECIMAL(5,2),
    "thetaPower" DECIMAL(5,2),
    "deltaPower" DECIMAL(5,2),
    "gammaPower" DECIMAL(5,2),
    "dominantFrequency" DECIMAL(5,2),
    "seizureActivity" BOOLEAN,

    -- Quality
    quality JSONB,

    -- Metadata
    sequence INTEGER,
    metadata JSONB,

    -- Constraints
    CONSTRAINT vitals_mode_check CHECK (mode IN ('ecg', 'eeg'))
);

-- Convert to hypertable with smaller chunks (30 minutes)
SELECT create_hypertable('vitals_realtime', 'time',
    chunk_time_interval => INTERVAL '30 minutes',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_vitals_realtime_patient_time
    ON vitals_realtime ("patientId", time DESC);

CREATE INDEX IF NOT EXISTS idx_vitals_realtime_device_time
    ON vitals_realtime ("deviceId", time DESC);

-- Compression and retention policies
-- Note: Compression disabled for now - can be enabled later if needed
DO $$
BEGIN
    PERFORM add_retention_policy('vitals_realtime', INTERVAL '90 days', if_not_exists => true);
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Could not add retention policy to vitals_realtime: %', SQLERRM;
END $$;

-- ============================================
-- CONTINUOUS AGGREGATES
-- ============================================
-- 1-minute aggregates for vitals
-- Note: Using WITH NO DATA to avoid transaction issues
DO $$
BEGIN
    CREATE MATERIALIZED VIEW vitals_1min
    WITH (timescaledb.continuous) AS
    SELECT
        time_bucket('1 minute', time) AS bucket,
        "patientId",
        "deviceId",
        mode,
        AVG("heartRate") as avg_heart_rate,
        MAX("heartRate") as max_heart_rate,
        MIN("heartRate") as min_heart_rate,
        AVG("respiratoryRate") as avg_respiratory_rate,
        AVG("skinTemperature") as avg_temperature,
        AVG("oxygenSaturation") as avg_oxygen_saturation,
        AVG("signalQuality") as avg_signal_quality,
        COUNT(*) as reading_count
    FROM vitals_realtime
    GROUP BY bucket, "patientId", "deviceId", mode
    WITH NO DATA;

    RAISE NOTICE 'Created continuous aggregate: vitals_1min';
EXCEPTION
    WHEN duplicate_table THEN
        RAISE NOTICE 'Continuous aggregate vitals_1min already exists';
    WHEN OTHERS THEN
        RAISE NOTICE 'Could not create vitals_1min: %', SQLERRM;
END $$;

-- Add refresh policy (refresh every minute)
DO $$
BEGIN
    PERFORM add_continuous_aggregate_policy('vitals_1min',
        start_offset => INTERVAL '1 hour',
        end_offset => INTERVAL '1 minute',
        schedule_interval => INTERVAL '1 minute',
        if_not_exists => true);
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Could not add refresh policy to vitals_1min: %', SQLERRM;
END $$;

-- ============================================
-- NEURAL EVENTS TABLE (Arrhythmia, Seizures)
-- ============================================
CREATE TABLE IF NOT EXISTS public.neural_events (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50) NOT NULL,

    "eventType" VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,

    mode VARCHAR(10) NOT NULL,
    "sampleRate" INTEGER,
    duration INTEGER,

    context JSONB,
    waveform JSONB,
    actions JSONB,

    acknowledged BOOLEAN DEFAULT FALSE,
    "acknowledgedBy" VARCHAR(100),
    "acknowledgedAt" TIMESTAMPTZ,

    resolved BOOLEAN DEFAULT FALSE,
    "resolvedAt" TIMESTAMPTZ,

    metadata JSONB,

    -- Constraints
    CONSTRAINT neural_events_mode_check CHECK (mode IN ('ecg', 'eeg')),
    CONSTRAINT neural_events_severity_check CHECK (severity IN ('low', 'medium', 'high', 'critical'))
);

-- Convert to hypertable
SELECT create_hypertable('neural_events', 'time',
    chunk_time_interval => INTERVAL '24 hours',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_neural_events_patient_time
    ON neural_events ("patientId", time DESC);

CREATE INDEX IF NOT EXISTS idx_neural_events_type_severity
    ON neural_events ("eventType", severity, time DESC);

CREATE INDEX IF NOT EXISTS idx_neural_events_unresolved
    ON neural_events (resolved, time DESC) WHERE NOT resolved;

-- Retention policy (keep 7 years)
DO $$
BEGIN
    PERFORM add_retention_policy('neural_events', INTERVAL '7 years', if_not_exists => true);
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Could not add retention policy to neural_events: %', SQLERRM;
END $$;

-- ============================================
-- GRANT PERMISSIONS
-- ============================================
-- Note: hospital_user already has superuser privileges
-- GRANT statements not needed for superuser role
-- If additional roles are created in the future, grant permissions here

-- ============================================
-- SUCCESS MESSAGE
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '>> Migration 010 completed: Neural waveform tables created';
    RAISE NOTICE '   - waveform_snapshots (8-12 channel storage)';
    RAISE NOTICE '   - vitals_realtime (high-frequency vitals)';
    RAISE NOTICE '   - vitals_1min (continuous aggregates)';
    RAISE NOTICE '   - neural_events (arrhythmia/seizure tracking)';
    RAISE NOTICE '   - TimescaleDB policies: retention, aggregates';
END
$$;
