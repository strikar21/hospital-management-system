-- Migration 012: Create FHIR R5 Tables
-- Purpose: Implement FHIR R5 resource storage for future-proof healthcare interoperability
-- Date: 2025-11-18

-- ============================================================================
-- FHIR R5 Patient Resource
-- ============================================================================
CREATE TABLE IF NOT EXISTS fhir_patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource JSONB NOT NULL,

    -- Extracted fields for fast queries (denormalized from JSONB)
    abhaNumber TEXT UNIQUE, -- ABDM/ABHA unique identifier
    mrn TEXT UNIQUE, -- Medical Record Number (hospital-specific)
    familyName TEXT,
    givenName TEXT,
    gender TEXT,
    birthDate DATE,
    phoneNumber TEXT,

    -- Metadata
    active BOOLEAN DEFAULT true,
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_fhir_patient_resource CHECK (resource->>'resourceType' = 'Patient')
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_fhir_patients_abha ON fhir_patients(abhaNumber) WHERE abhaNumber IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fhir_patients_mrn ON fhir_patients(mrn) WHERE mrn IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fhir_patients_name ON fhir_patients(familyName, givenName);
CREATE INDEX IF NOT EXISTS idx_fhir_patients_active ON fhir_patients(active, createdAt DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_patients_resource ON fhir_patients USING GIN(resource);

-- ============================================================================
-- FHIR R5 Practitioner Resource (Staff)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fhir_practitioners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource JSONB NOT NULL,

    -- Extracted fields
    hprId TEXT UNIQUE, -- Health Professional Registry ID (ABDM)
    staffId TEXT UNIQUE, -- Internal staff ID (DOC0001, NUR0001, etc.)
    familyName TEXT,
    givenName TEXT,
    email TEXT,
    phoneNumber TEXT,
    qualification TEXT, -- Primary qualification (MD, MBBS, etc.)

    -- Metadata
    active BOOLEAN DEFAULT true,
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_fhir_practitioner_resource CHECK (resource->>'resourceType' = 'Practitioner')
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fhir_practitioners_hpr ON fhir_practitioners(hprId) WHERE hprId IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fhir_practitioners_staff ON fhir_practitioners(staffId) WHERE staffId IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fhir_practitioners_email ON fhir_practitioners(email);
CREATE INDEX IF NOT EXISTS idx_fhir_practitioners_active ON fhir_practitioners(active, createdAt DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_practitioners_resource ON fhir_practitioners USING GIN(resource);

-- ============================================================================
-- FHIR R5 Organization Resource (Hospital)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fhir_organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource JSONB NOT NULL,

    -- Extracted fields
    organizationId TEXT UNIQUE, -- HFR ID (Health Facility Registry - ABDM)
    name TEXT NOT NULL,
    type TEXT, -- hospital, clinic, diagnostic-center
    phoneNumber TEXT,
    email TEXT,

    -- Metadata
    active BOOLEAN DEFAULT true,
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_fhir_organization_resource CHECK (resource->>'resourceType' = 'Organization')
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fhir_organizations_orgid ON fhir_organizations(organizationId) WHERE organizationId IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fhir_organizations_name ON fhir_organizations(name);
CREATE INDEX IF NOT EXISTS idx_fhir_organizations_resource ON fhir_organizations USING GIN(resource);

-- ============================================================================
-- FHIR R5 Device Resource (IoT Devices)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fhir_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource JSONB NOT NULL,

    -- Extracted fields
    deviceId TEXT UNIQUE NOT NULL, -- fit-00001, ESP32_WATCH_002, etc.
    macAddress TEXT UNIQUE, -- BLE MAC address
    displayName TEXT,
    manufacturer TEXT,
    modelNumber TEXT,
    serialNumber TEXT,
    type TEXT, -- watch, tablet, doorScanner
    status TEXT DEFAULT 'active', -- active, inactive, entered-in-error
    batteryLevel INTEGER,
    firmwareVersion TEXT,

    -- Metadata
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW(),
    lastSeen TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT check_fhir_device_resource CHECK (resource->>'resourceType' = 'Device'),
    CONSTRAINT check_device_status CHECK (status IN ('active', 'inactive', 'entered-in-error', 'unknown'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fhir_devices_deviceid ON fhir_devices(deviceId);
CREATE INDEX IF NOT EXISTS idx_fhir_devices_mac ON fhir_devices(macAddress) WHERE macAddress IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fhir_devices_type ON fhir_devices(type, status);
CREATE INDEX IF NOT EXISTS idx_fhir_devices_status ON fhir_devices(status, lastSeen DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_devices_resource ON fhir_devices USING GIN(resource);

-- ============================================================================
-- FHIR R5 DeviceMetric Resource (Sensor Capabilities)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fhir_device_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource JSONB NOT NULL,

    -- Extracted fields
    deviceId UUID REFERENCES fhir_devices(id) ON DELETE CASCADE,
    metricType TEXT NOT NULL, -- heart-rate, spo2, temperature, etc. (LOINC codes)
    operationalStatus TEXT DEFAULT 'on', -- on, off, standby

    -- Metadata
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_fhir_device_metric_resource CHECK (resource->>'resourceType' = 'DeviceMetric')
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

    -- Extracted fields
    patientId UUID REFERENCES fhir_patients(id) ON DELETE CASCADE,
    deviceId UUID REFERENCES fhir_devices(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'attached', -- attached, entered-in-error, unknown
    periodStart TIMESTAMPTZ,
    periodEnd TIMESTAMPTZ,
    operatorId UUID REFERENCES fhir_practitioners(id) ON DELETE SET NULL, -- Who assigned it

    -- Metadata
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_fhir_device_association_resource CHECK (resource->>'resourceType' = 'DeviceAssociation'),
    CONSTRAINT check_association_status CHECK (status IN ('attached', 'entered-in-error', 'unknown'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fhir_device_assoc_patient ON fhir_device_associations(patientId, periodStart DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_device_assoc_device ON fhir_device_associations(deviceId, periodStart DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_device_assoc_status ON fhir_device_associations(status, periodStart DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_device_assoc_active ON fhir_device_associations(patientId, deviceId) WHERE periodEnd IS NULL;
CREATE INDEX IF NOT EXISTS idx_fhir_device_assoc_resource ON fhir_device_associations USING GIN(resource);

-- ============================================================================
-- FHIR R5 DeviceUsage Resource (Usage Tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fhir_device_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource JSONB NOT NULL,

    -- Extracted fields
    patientId UUID REFERENCES fhir_patients(id) ON DELETE CASCADE,
    deviceId UUID REFERENCES fhir_devices(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'active', -- active, completed, entered-in-error, intended, stopped, on-hold
    periodStart TIMESTAMPTZ,
    periodEnd TIMESTAMPTZ,

    -- Metadata
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_fhir_device_usage_resource CHECK (resource->>'resourceType' = 'DeviceUsage')
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fhir_device_usage_patient ON fhir_device_usage(patientId, periodStart DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_device_usage_device ON fhir_device_usage(deviceId, periodStart DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_device_usage_status ON fhir_device_usage(status);
CREATE INDEX IF NOT EXISTS idx_fhir_device_usage_resource ON fhir_device_usage USING GIN(resource);

-- ============================================================================
-- FHIR R5 MedicationRequest Resource (Prescriptions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fhir_medication_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource JSONB NOT NULL,

    -- Extracted fields
    patientId UUID REFERENCES fhir_patients(id) ON DELETE CASCADE,
    practitionerId UUID REFERENCES fhir_practitioners(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'active', -- active, on-hold, cancelled, completed, entered-in-error, stopped, draft, unknown
    intent TEXT DEFAULT 'order', -- proposal, plan, order, original-order, reflex-order, filler-order, instance-order, option
    medicationCode TEXT, -- RxNorm code
    medicationDisplay TEXT, -- Drug name
    authoredOn TIMESTAMPTZ,

    -- Metadata
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_fhir_medication_request_resource CHECK (resource->>'resourceType' = 'MedicationRequest')
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fhir_medrq_patient ON fhir_medication_requests(patientId, authoredOn DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_medrq_practitioner ON fhir_medication_requests(practitionerId);
CREATE INDEX IF NOT EXISTS idx_fhir_medrq_status ON fhir_medication_requests(status, authoredOn DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_medrq_medication ON fhir_medication_requests(medicationCode);
CREATE INDEX IF NOT EXISTS idx_fhir_medrq_resource ON fhir_medication_requests USING GIN(resource);

-- ============================================================================
-- FHIR R5 Encounter Resource (Patient visits/admissions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fhir_encounters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource JSONB NOT NULL,

    -- Extracted fields
    patientId UUID REFERENCES fhir_patients(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'in-progress', -- planned, in-progress, on-hold, discharged, completed, cancelled, entered-in-error, unknown
    class TEXT, -- inpatient, outpatient, emergency, etc.
    periodStart TIMESTAMPTZ,
    periodEnd TIMESTAMPTZ,

    -- Metadata
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_fhir_encounter_resource CHECK (resource->>'resourceType' = 'Encounter')
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fhir_encounters_patient ON fhir_encounters(patientId, periodStart DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_encounters_status ON fhir_encounters(status, periodStart DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_encounters_class ON fhir_encounters(class);
CREATE INDEX IF NOT EXISTS idx_fhir_encounters_resource ON fhir_encounters USING GIN(resource);

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

CREATE TRIGGER trigger_fhir_patients_updated_at BEFORE UPDATE ON fhir_patients FOR EACH ROW EXECUTE FUNCTION update_fhir_updated_at();
CREATE TRIGGER trigger_fhir_practitioners_updated_at BEFORE UPDATE ON fhir_practitioners FOR EACH ROW EXECUTE FUNCTION update_fhir_updated_at();
CREATE TRIGGER trigger_fhir_organizations_updated_at BEFORE UPDATE ON fhir_organizations FOR EACH ROW EXECUTE FUNCTION update_fhir_updated_at();
CREATE TRIGGER trigger_fhir_devices_updated_at BEFORE UPDATE ON fhir_devices FOR EACH ROW EXECUTE FUNCTION update_fhir_updated_at();
CREATE TRIGGER trigger_fhir_device_metrics_updated_at BEFORE UPDATE ON fhir_device_metrics FOR EACH ROW EXECUTE FUNCTION update_fhir_updated_at();
CREATE TRIGGER trigger_fhir_device_associations_updated_at BEFORE UPDATE ON fhir_device_associations FOR EACH ROW EXECUTE FUNCTION update_fhir_updated_at();
CREATE TRIGGER trigger_fhir_device_usage_updated_at BEFORE UPDATE ON fhir_device_usage FOR EACH ROW EXECUTE FUNCTION update_fhir_updated_at();
CREATE TRIGGER trigger_fhir_medication_requests_updated_at BEFORE UPDATE ON fhir_medication_requests FOR EACH ROW EXECUTE FUNCTION update_fhir_updated_at();
CREATE TRIGGER trigger_fhir_encounters_updated_at BEFORE UPDATE ON fhir_encounters FOR EACH ROW EXECUTE FUNCTION update_fhir_updated_at();

-- ============================================================================
-- Verification
-- ============================================================================
SELECT 'FHIR R5 tables created successfully' as status;
SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'fhir_%' ORDER BY tablename;
