-- Migration 015: Create patient_alerts table for persistent alert storage
-- Fixes: mqtt_service.py:306 TODO - alerts were only broadcast via WebSocket, not persisted

-- Patient alerts table for storing all clinical and device alerts
CREATE TABLE IF NOT EXISTS patient_alerts (
    id TEXT PRIMARY KEY,
    "patientId" TEXT NOT NULL,
    "deviceId" TEXT,
    type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    source TEXT NOT NULL,  -- 'ESP32' or 'Backend'
    "alertTimestamp" TIMESTAMP NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',  -- 'active' or 'acknowledged'
    "acknowledgedBy" TEXT,
    "acknowledgedAt" TIMESTAMP,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    "updatedAt" TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY ("acknowledgedBy") REFERENCES staff(id) ON DELETE SET NULL
);

-- Indexes for performance (without DESC to avoid syntax issues)
CREATE INDEX IF NOT EXISTS idx_patient_alerts_patient ON patient_alerts("patientId");
CREATE INDEX IF NOT EXISTS idx_patient_alerts_status ON patient_alerts(status);
CREATE INDEX IF NOT EXISTS idx_patient_alerts_timestamp ON patient_alerts("alertTimestamp");
CREATE INDEX IF NOT EXISTS idx_patient_alerts_severity ON patient_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_patient_alerts_patient_status ON patient_alerts("patientId", status);

-- Trigger to automatically update updatedAt timestamp
CREATE OR REPLACE FUNCTION update_patient_alerts_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW."updatedAt" = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_patient_alerts_timestamp
    BEFORE UPDATE ON patient_alerts
    FOR EACH ROW
    EXECUTE FUNCTION update_patient_alerts_timestamp();

-- Add comment for documentation
COMMENT ON TABLE patient_alerts IS 'Stores all clinical and device alerts for patients. Replaces ephemeral WebSocket-only alerts with persistent storage.';
COMMENT ON COLUMN patient_alerts.source IS 'Alert source: ESP32 (device-level alerts) or Backend (clinical analysis alerts)';
COMMENT ON COLUMN patient_alerts.status IS 'Alert status: active (unacknowledged) or acknowledged';
