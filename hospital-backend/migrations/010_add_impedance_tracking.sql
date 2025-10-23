-- Migration 010: Add Impedance Tracking Tables
-- Component 3: Impedance Trend Tracking (4 alerts)

-- Impedance readings table for tracking electrode connection quality
CREATE TABLE IF NOT EXISTS impedanceReadings (
    readingId SERIAL PRIMARY KEY,
    patientId TEXT NOT NULL,
    deviceId TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    impedance FLOAT NOT NULL,
    FOREIGN KEY (patientId) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (deviceId) REFERENCES devices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_impedance_patient_time ON impedanceReadings(patientId, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_impedance_device_time ON impedanceReadings(deviceId, timestamp DESC);

-- Watch removal events table for tracking patient behavior
CREATE TABLE IF NOT EXISTS watchRemovalEvents (
    eventId SERIAL PRIMARY KEY,
    patientId TEXT NOT NULL,
    deviceId TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    duration INTEGER,  -- seconds watch was off
    reason TEXT,  -- 'patient_removed', 'clinician_removed', 'automatic'
    FOREIGN KEY (patientId) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (deviceId) REFERENCES devices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_removal_patient_time ON watchRemovalEvents(patientId, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_removal_device_time ON watchRemovalEvents(deviceId, timestamp DESC);
