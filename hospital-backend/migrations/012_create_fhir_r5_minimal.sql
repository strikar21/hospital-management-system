-- Migration 012: Create Minimal FHIR R5 Tables (AI-Focused)
-- Purpose: Store only device data + cached clinical context for AI vitals analysis
-- Strategy: Patient/Practitioner demographics from external HMS via FHIR APIs
-- Date: 2025-11-18

-- ============================================================================
-- Patient Clinical Context (Cached from HMS for AI)
-- ============================================================================
CREATE TABLE IF NOT EXISTS patient_clinical_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity (reference to external HMS)
    abhaNumber TEXT UNIQUE,  -- ABDM Health ID
    mrn TEXT,  -- Hospital Medical Record Number
    externalPatientUrl TEXT,  -- FHIR endpoint: "https://hms.hospital.com/fhir/Patient/123"
    externalEncounterUrl TEXT,  -- Current admission/encounter

    -- Demographics (cached for AI analysis)
    birthDate DATE NOT NULL,  -- Calculate age dynamically
    gender TEXT NOT NULL,  -- male, female, other

    -- Physical measurements (for AI vitals analysis)
    weight NUMERIC(5,2),  -- kg (updated during admission)
    height NUMERIC(5,2),  -- cm (updated during admission)
    bmi NUMERIC(4,1) GENERATED ALWAYS AS (
        CASE
            WHEN height > 0 THEN weight / ((height/100) * (height/100))
            ELSE NULL
        END
    ) STORED,

    -- Clinical context (for AI baseline adjustments)
    isPregnant BOOLEAN DEFAULT false,
    comorbidities JSONB DEFAULT '{}',  -- {"diabetes": true, "hypertension": true, "ckd": false}
    currentMedications JSONB DEFAULT '[]',  -- ["Metformin", "Lisinopril"]
    allergies JSONB DEFAULT '[]',  -- ["Penicillin"]

    -- Admission context (for device assignment)
    roomNumber TEXT,
    bedNumber TEXT,
    admissionDate TIMESTAMPTZ,
    expectedDischargeDate TIMESTAMPTZ,
    admissionStatus TEXT DEFAULT 'admitted',  -- admitted, discharged, transferred

    -- Sync metadata
    lastSyncedFromHms TIMESTAMPTZ,
    syncSource TEXT,  -- 'hms_push', 'manual_entry', 'abdm_pull'

    -- Metadata
    active BOOLEAN DEFAULT true,
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_gender CHECK (gender IN ('male', 'female', 'other', 'unknown')),
    CONSTRAINT check_admission_status CHECK (admissionStatus IN ('admitted', 'discharged', 'transferred', 'on-leave'))
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_patient_context_abha ON patient_clinical_context(abhaNumber) WHERE abhaNumber IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_patient_context_mrn ON patient_clinical_context(mrn) WHERE mrn IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_patient_context_room_bed ON patient_clinical_context(roomNumber, bedNumber) WHERE admissionStatus = 'admitted';
CREATE INDEX IF NOT EXISTS idx_patient_context_active ON patient_clinical_context(active, admissionStatus);
CREATE INDEX IF NOT EXISTS idx_patient_context_comorbidities ON patient_clinical_context USING GIN(comorbidities);

-- Function to calculate age from birthDate
CREATE OR REPLACE FUNCTION get_patient_age(birth_date DATE)
RETURNS INTEGER AS $$
BEGIN
    RETURN EXTRACT(YEAR FROM AGE(birth_date));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- FHIR R5 Device Resource (IoT Devices - YOUR Core Data)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fhir_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource JSONB NOT NULL,

    -- Extracted fields for fast queries
    deviceId TEXT UNIQUE NOT NULL,  -- fit-00001, ESP32_WATCH_002
    macAddress TEXT UNIQUE,  -- BLE MAC address
    displayName TEXT,
    manufacturer TEXT,
    modelNumber TEXT,
    serialNumber TEXT,
    deviceType TEXT NOT NULL,  -- watch, tablet, doorScanner
    status TEXT DEFAULT 'active',  -- active, inactive, entered-in-error, unknown

    -- Device health
    batteryLevel INTEGER,
    firmwareVersion TEXT,
    lastSeen TIMESTAMPTZ,

    -- Calibration & maintenance
    lastCalibrationDate TIMESTAMPTZ,
    calibrationDueDate TIMESTAMPTZ,
    maintenanceStatus TEXT DEFAULT 'ok',  -- ok, needs-calibration, needs-maintenance, retired

    -- Metadata
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_fhir_device_resource CHECK (resource->>'resourceType' = 'Device'),
    CONSTRAINT check_device_status CHECK (status IN ('active', 'inactive', 'entered-in-error', 'unknown')),
    CONSTRAINT check_device_type CHECK (deviceType IN ('watch', 'tablet', 'doorScanner', 'sensor', 'other')),
    CONSTRAINT check_battery_level CHECK (batteryLevel >= 0 AND batteryLevel <= 100)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fhir_devices_deviceid ON fhir_devices(deviceId);
CREATE INDEX IF NOT EXISTS idx_fhir_devices_mac ON fhir_devices(macAddress) WHERE macAddress IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fhir_devices_type_status ON fhir_devices(deviceType, status);
CREATE INDEX IF NOT EXISTS idx_fhir_devices_last_seen ON fhir_devices(lastSeen DESC) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_fhir_devices_calibration_due ON fhir_devices(calibrationDueDate) WHERE calibrationDueDate IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fhir_devices_resource ON fhir_devices USING GIN(resource);

-- ============================================================================
-- FHIR R5 DeviceMetric Resource (Sensor Capabilities)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fhir_device_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource JSONB NOT NULL,

    -- Extracted fields
    deviceId UUID NOT NULL REFERENCES fhir_devices(id) ON DELETE CASCADE,
    metricType TEXT NOT NULL,  -- LOINC codes: 8867-4 (heart-rate), 2708-6 (spo2)
    metricDisplay TEXT,  -- "Heart Rate", "Oxygen Saturation"
    operationalStatus TEXT DEFAULT 'on',  -- on, off, standby
    unit TEXT,  -- beats/min, %, °C

    -- Metadata
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_fhir_device_metric_resource CHECK (resource->>'resourceType' = 'DeviceMetric'),
    CONSTRAINT check_metric_status CHECK (operationalStatus IN ('on', 'off', 'standby'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fhir_device_metrics_device ON fhir_device_metrics(deviceId);
CREATE INDEX IF NOT EXISTS idx_fhir_device_metrics_type ON fhir_device_metrics(metricType);
CREATE INDEX IF NOT EXISTS idx_fhir_device_metrics_resource ON fhir_device_metrics USING GIN(resource);

-- ============================================================================
-- FHIR R5 DeviceAssociation Resource (Device-Patient Assignment)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fhir_device_associations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource JSONB NOT NULL,

    -- Relationships
    patientContextId UUID NOT NULL REFERENCES patient_clinical_context(id) ON DELETE CASCADE,
    deviceId UUID NOT NULL REFERENCES fhir_devices(id) ON DELETE CASCADE,

    -- Assignment details
    status TEXT DEFAULT 'attached',  -- attached, entered-in-error, unknown
    periodStart TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    periodEnd TIMESTAMPTZ,

    -- Who assigned it (reference to external HMS practitioner)
    operatorReference TEXT,  -- "https://hms.hospital.com/fhir/Practitioner/TEC001"
    assignmentReason TEXT,  -- "vitals monitoring", "post-surgery monitoring"

    -- Metadata
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_fhir_device_association_resource CHECK (resource->>'resourceType' = 'DeviceAssociation'),
    CONSTRAINT check_association_status CHECK (status IN ('attached', 'entered-in-error', 'unknown')),
    CONSTRAINT check_period CHECK (periodEnd IS NULL OR periodEnd > periodStart)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fhir_device_assoc_patient ON fhir_device_associations(patientContextId, periodStart DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_device_assoc_device ON fhir_device_associations(deviceId, periodStart DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_device_assoc_active ON fhir_device_associations(patientContextId, deviceId, status) WHERE periodEnd IS NULL;
CREATE INDEX IF NOT EXISTS idx_fhir_device_assoc_resource ON fhir_device_associations USING GIN(resource);

-- Unique constraint: One device can only be assigned to one patient at a time
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_single_active_assignment
ON fhir_device_associations(deviceId)
WHERE periodEnd IS NULL AND status = 'attached';

-- ============================================================================
-- Update Triggers (auto-update updatedAt timestamp)
-- ============================================================================
CREATE OR REPLACE FUNCTION update_fhir_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updatedAt = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_patient_context_updated_at
    BEFORE UPDATE ON patient_clinical_context
    FOR EACH ROW EXECUTE FUNCTION update_fhir_updated_at();

CREATE TRIGGER trigger_fhir_devices_updated_at
    BEFORE UPDATE ON fhir_devices
    FOR EACH ROW EXECUTE FUNCTION update_fhir_updated_at();

CREATE TRIGGER trigger_fhir_device_metrics_updated_at
    BEFORE UPDATE ON fhir_device_metrics
    FOR EACH ROW EXECUTE FUNCTION update_fhir_updated_at();

CREATE TRIGGER trigger_fhir_device_associations_updated_at
    BEFORE UPDATE ON fhir_device_associations
    FOR EACH ROW EXECUTE FUNCTION update_fhir_updated_at();

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- Active device assignments with patient context
CREATE OR REPLACE VIEW active_device_assignments AS
SELECT
    da.id AS assignmentId,
    da.deviceId,
    d.deviceId AS deviceCode,
    d.displayName AS deviceName,
    d.deviceType,
    d.batteryLevel,
    da.patientContextId,
    pc.abhaNumber,
    pc.mrn,
    pc.roomNumber,
    pc.bedNumber,
    get_patient_age(pc.birthDate) AS patientAge,
    pc.gender,
    pc.weight,
    pc.height,
    pc.bmi,
    pc.comorbidities,
    da.periodStart AS assignedAt,
    da.status
FROM fhir_device_associations da
JOIN fhir_devices d ON da.deviceId = d.id
JOIN patient_clinical_context pc ON da.patientContextId = pc.id
WHERE da.periodEnd IS NULL
  AND da.status = 'attached'
  AND pc.active = true;

-- Device availability status
CREATE OR REPLACE VIEW device_availability AS
SELECT
    d.id,
    d.deviceId,
    d.displayName,
    d.deviceType,
    d.status,
    d.batteryLevel,
    d.lastSeen,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM fhir_device_associations da
            WHERE da.deviceId = d.id
              AND da.periodEnd IS NULL
              AND da.status = 'attached'
        ) THEN 'assigned'
        ELSE 'available'
    END AS assignmentStatus,
    d.maintenanceStatus
FROM fhir_devices d
WHERE d.status = 'active';

-- ============================================================================
-- Verification
-- ============================================================================
SELECT 'FHIR R5 minimal tables (AI-focused) created successfully' as status;

SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND (tablename LIKE 'fhir_%' OR tablename = 'patient_clinical_context')
ORDER BY tablename;
