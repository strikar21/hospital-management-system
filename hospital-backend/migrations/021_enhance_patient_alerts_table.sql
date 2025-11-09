-- Migration 021: Enhance patient_alerts table for proper medical tracking and deduplication
-- Purpose: Add missing columns for alert lifecycle management and deduplication
-- Date: 2025-11-07

-- Add missing columns for medical context and tracking
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "vitalType" TEXT;
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "vitalValue" FLOAT;
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "thresholdValue" FLOAT;
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "createdBy" TEXT;  -- Device ID that created alert
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "resolvedAt" TIMESTAMP;
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS category TEXT;  -- 'cardiac', 'respiratory', etc.
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS confidence FLOAT;  -- 0.0-1.0 confidence score
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS context JSONB;  -- Additional metadata

-- Update status column comment to reflect new 'resolved' state
-- Status lifecycle: active (new alert) → acknowledged (staff aware) → resolved (condition cleared)
COMMENT ON COLUMN patient_alerts.status IS 'Alert lifecycle status: active (unacknowledged), acknowledged (staff aware, ongoing), resolved (condition cleared)';

-- Add indexes for efficient deduplication queries
-- This index speeds up "find existing active/acknowledged alert of same type" queries
CREATE INDEX IF NOT EXISTS idx_patient_alerts_dedup
    ON patient_alerts("patientId", type, status)
    WHERE status IN ('active', 'acknowledged');

-- Add index for vital-specific alert lookups (e.g., find all tachycardia alerts)
CREATE INDEX IF NOT EXISTS idx_patient_alerts_vital
    ON patient_alerts("patientId", "vitalType", status)
    WHERE "vitalType" IS NOT NULL;

-- Add index for resolution queries (find alerts to auto-resolve)
CREATE INDEX IF NOT EXISTS idx_patient_alerts_resolution
    ON patient_alerts("patientId", status, "updatedAt")
    WHERE status IN ('active', 'acknowledged');

-- Update table comment
COMMENT ON TABLE patient_alerts IS 'Persistent clinical alert storage with full lifecycle tracking (active → acknowledged → resolved). Supports deduplication and auto-resolution.';

-- Add comments for new columns
COMMENT ON COLUMN patient_alerts."vitalType" IS 'Vital sign that triggered alert (e.g., heartRate, respiratoryRate, oxygenSaturation)';
COMMENT ON COLUMN patient_alerts."vitalValue" IS 'Actual vital reading that triggered alert';
COMMENT ON COLUMN patient_alerts."thresholdValue" IS 'Threshold value that was exceeded';
COMMENT ON COLUMN patient_alerts."createdBy" IS 'Device ID that created the alert';
COMMENT ON COLUMN patient_alerts."resolvedAt" IS 'Timestamp when alert condition cleared';
COMMENT ON COLUMN patient_alerts.category IS 'Alert category: cardiac, respiratory, neurological, device, metabolic, etc.';
COMMENT ON COLUMN patient_alerts.confidence IS 'Algorithm confidence score (0.0 = uncertain, 1.0 = certain)';
COMMENT ON COLUMN patient_alerts.context IS 'Additional alert metadata as JSON (e.g., ECG analysis results, trend data)';
