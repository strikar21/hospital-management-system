-- Migration 011: Add patient states table for duration-based alert tracking
-- Component 4: Duration/State Tracking

-- Patient states table for tracking prolonged conditions
CREATE TABLE IF NOT EXISTS patientStates (
    stateId SERIAL PRIMARY KEY,
    patientId TEXT NOT NULL UNIQUE,

    -- Tachycardia state (HR >100 for >15min)
    tachycardiaStartTime TIMESTAMP,
    tachycardiaAlertSent BOOLEAN DEFAULT FALSE,

    -- Bradycardia state (HR <60 for >10min)
    bradycardiaStartTime TIMESTAMP,
    bradycardiaAlertSent BOOLEAN DEFAULT FALSE,

    -- Hypotension state (Systolic BP <90 for >10min)
    hypotensionStartTime TIMESTAMP,
    hypotensionAlertSent BOOLEAN DEFAULT FALSE,

    -- Hypoxia state (SpO2 <90% for >5min)
    hypoxiaStartTime TIMESTAMP,
    hypoxiaAlertSent BOOLEAN DEFAULT FALSE,

    -- Fever state (Temp >38.3C for >1hr)
    feverStartTime TIMESTAMP,
    feverAlertSent BOOLEAN DEFAULT FALSE,

    -- Hypothermia state (Temp <35C for >30min)
    hypothermiaStartTime TIMESTAMP,
    hypothermiaAlertSent BOOLEAN DEFAULT FALSE,

    -- Last vitals received tracking
    lastVitalsTimestamp TIMESTAMP,
    noVitalsAlertSent BOOLEAN DEFAULT FALSE,

    -- Connection drop tracking (JSON array of timestamps)
    connectionDrops JSONB DEFAULT '[]'::jsonb,

    -- Timestamps
    createdAt TIMESTAMP DEFAULT NOW(),
    updatedAt TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY (patientId) REFERENCES patients(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_patientstates_patient ON patientStates(patientId);
CREATE INDEX IF NOT EXISTS idx_patientstates_updated ON patientStates(updatedAt);
CREATE INDEX IF NOT EXISTS idx_patientstates_lastvitals ON patientStates(lastVitalsTimestamp);

-- Trigger to automatically update updatedAt timestamp
CREATE OR REPLACE FUNCTION update_patientstates_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updatedAt = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_patientstates_timestamp
    BEFORE UPDATE ON patientStates
    FOR EACH ROW
    EXECUTE FUNCTION update_patientstates_timestamp();
