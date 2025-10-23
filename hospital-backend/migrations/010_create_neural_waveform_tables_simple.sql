-- Migration 010: Create Neural Waveform Tables (Simplified - No TimescaleDB Required)
-- Purpose: Store multi-channel ECG/EEG waveform data
-- Date: 2025-10-15

-- ============================================
-- WAVEFORM SNAPSHOTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS public.waveform_snapshots (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50) NOT NULL,
    mode VARCHAR(10) NOT NULL,
    "sampleRate" INTEGER NOT NULL,
    duration INTEGER NOT NULL,

    -- ECG channels (12-lead)
    "ecgLimbLeads" JSONB,
    "ecgPrecordialLeads" JSONB,
    "ecgDerivedLeads" JSONB,
    "ecgEvents" JSONB,

    -- EEG channels (8-channel)
    "eegFrontalChannels" JSONB,
    "eegCentralChannels" JSONB,
    "eegOccipitalChannels" JSONB,
    "eegAnalysis" JSONB,

    -- Quality metrics
    quality JSONB,

    -- Metadata
    sequence INTEGER,
    compression VARCHAR(20),
    metadata JSONB,

    CONSTRAINT waveform_mode_check CHECK (mode IN ('ecg', 'eeg'))
);

CREATE INDEX IF NOT EXISTS idx_waveform_snapshots_patient_mode_time
    ON waveform_snapshots ("patientId", mode, time DESC);

CREATE INDEX IF NOT EXISTS idx_waveform_snapshots_device_time
    ON waveform_snapshots ("deviceId", time DESC);

-- ============================================
-- REAL-TIME VITALS TABLE
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

    CONSTRAINT vitals_mode_check CHECK (mode IN ('ecg', 'eeg'))
);

CREATE INDEX IF NOT EXISTS idx_vitals_realtime_patient_time
    ON vitals_realtime ("patientId", time DESC);

CREATE INDEX IF NOT EXISTS idx_vitals_realtime_device_time
    ON vitals_realtime ("deviceId", time DESC);

-- ============================================
-- NEURAL EVENTS TABLE
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

    CONSTRAINT neural_events_mode_check CHECK (mode IN ('ecg', 'eeg')),
    CONSTRAINT neural_events_severity_check CHECK (severity IN ('low', 'medium', 'high', 'critical'))
);

CREATE INDEX IF NOT EXISTS idx_neural_events_patient_time
    ON neural_events ("patientId", time DESC);

CREATE INDEX IF NOT EXISTS idx_neural_events_type_severity
    ON neural_events ("eventType", severity, time DESC);

CREATE INDEX IF NOT EXISTS idx_neural_events_unresolved
    ON neural_events (resolved, time DESC) WHERE NOT resolved;
