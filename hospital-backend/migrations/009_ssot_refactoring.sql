-- Migration 009: Single Source of Truth Refactoring
-- Purpose: Remove redundant fields, create unified view, add constraints
-- Date: 2025-10-13
-- Author: Senior Backend Architect

BEGIN;

-- ============================================================================
-- PART 1: REMOVE REDUNDANT FIELDS FROM DEVICES TABLE
-- ============================================================================

-- Check if assignedPatient column exists before dropping
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'assignedPatient'
    ) THEN
        -- Remove redundant assignedPatient field (use deviceassignments table instead)
        ALTER TABLE devices DROP COLUMN "assignedPatient";
        RAISE NOTICE 'Dropped devices.assignedPatient column';
    ELSE
        RAISE NOTICE 'Column devices.assignedPatient does not exist, skipping';
    END IF;
END $$;

-- ============================================================================
-- PART 2: CREATE ENRICHED VIEW FOR UNIFIED DEVICE DATA
-- ============================================================================

-- Drop view if it exists (to allow recreation)
DROP VIEW IF EXISTS devices_enriched CASCADE;

-- Create comprehensive view that joins devices with assignments and patients
CREATE VIEW devices_enriched AS
SELECT
    -- All device fields
    d.id,
    d."deviceType",
    d.name,
    d."serialNumber",
    d."macAddress",
    d."firmwareVersion",
    d.status,
    d.location,
    d.description,
    d."batteryLevel",
    d."lastSeen",
    d."calibrationDate",
    d."nextMaintenanceDate",
    d."createdAt",
    d."updatedAt",
    d.model,
    d.manufacturer,

    -- Current assignment info (if assigned)
    da.id as "assignmentId",
    da."patientId" as "assignedPatientId",
    da."assignedBy",
    da."assignedAt",
    da."unassignedBy",
    da."unassignedAt",
    da."unassignmentReason",
    da.status as "assignmentStatus",

    -- Patient info (if assigned)
    p."firstName" as "patientFirstName",
    p."lastName" as "patientLastName",
    p."roomNumber",
    p."bedNumber",
    CONCAT(p."firstName", ' ', p."lastName") as "patientName",
    CONCAT('Room ', p."roomNumber", ', Bed ', p."bedNumber") as "patientLocation",

    -- Computed connection status (based on lastSeen timestamp)
    CASE
        WHEN d."lastSeen" IS NULL THEN 'offline'
        WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
        WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
        ELSE 'offline'
    END as "connectionStatus",

    -- Computed battery status
    CASE
        WHEN d."batteryLevel" IS NULL THEN 'unknown'
        WHEN d."batteryLevel" >= 80 THEN 'excellent'
        WHEN d."batteryLevel" >= 60 THEN 'good'
        WHEN d."batteryLevel" >= 40 THEN 'fair'
        WHEN d."batteryLevel" >= 20 THEN 'low'
        ELSE 'critical'
    END as "batteryStatus",

    -- Minutes since last seen (useful for alerting)
    CASE
        WHEN d."lastSeen" IS NULL THEN NULL
        ELSE EXTRACT(EPOCH FROM (NOW() - d."lastSeen")) / 60
    END as "minutesSinceLastSeen"

FROM devices d
LEFT JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
LEFT JOIN patients p ON da."patientId" = p.id;

-- Add comment to view
COMMENT ON VIEW devices_enriched IS 'Unified view of devices with current assignments and computed fields. Single source of truth for device queries.';

-- ============================================================================
-- PART 3: ADD DATA INTEGRITY CONSTRAINTS
-- ============================================================================

-- Ensure device status is valid (prevent invalid statuses)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'check_device_status'
    ) THEN
        ALTER TABLE devices ADD CONSTRAINT check_device_status
            CHECK (status IN ('available', 'assigned', 'maintenance', 'retired', 'offline'));
        RAISE NOTICE 'Added check_device_status constraint';
    END IF;
END $$;

-- Ensure device type is valid
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'check_device_type'
    ) THEN
        ALTER TABLE devices ADD CONSTRAINT check_device_type
            CHECK ("deviceType" IN ('tablet', 'watch', 'sensor', 'medicalEquipment', 'doorScanner', 'vitalMonitor', 'infusionPump', 'other'));
        RAISE NOTICE 'Added check_device_type constraint';
    END IF;
END $$;

-- Ensure only one active assignment per device (prevent double-assignment)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_unique_active_device_assignment'
    ) THEN
        CREATE UNIQUE INDEX idx_unique_active_device_assignment
            ON deviceassignments ("deviceId")
            WHERE status = 'active';
        RAISE NOTICE 'Added unique index on active device assignments';
    END IF;
END $$;

-- Ensure only one active assignment per patient (one device per patient)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_unique_active_patient_assignment'
    ) THEN
        CREATE UNIQUE INDEX idx_unique_active_patient_assignment
            ON deviceassignments ("patientId")
            WHERE status = 'active';
        RAISE NOTICE 'Added unique index on active patient assignments';
    END IF;
END $$;

-- Ensure assignment status is valid
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'check_assignment_status'
    ) THEN
        ALTER TABLE deviceassignments ADD CONSTRAINT check_assignment_status
            CHECK (status IN ('active', 'inactive', 'forceRemoved'));
        RAISE NOTICE 'Added check_assignment_status constraint';
    END IF;
END $$;

-- ============================================================================
-- PART 4: CREATE PERFORMANCE INDEXES
-- ============================================================================

-- Index on devices.lastSeen for connection status queries
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_devices_last_seen'
    ) THEN
        CREATE INDEX idx_devices_last_seen ON devices ("lastSeen");
        RAISE NOTICE 'Added index on devices.lastSeen';
    END IF;
END $$;

-- Index on deviceassignments.status for active assignment queries
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_deviceassignments_status'
    ) THEN
        CREATE INDEX idx_deviceassignments_status ON deviceassignments (status);
        RAISE NOTICE 'Added index on deviceassignments.status';
    END IF;
END $$;

-- Composite index on devices (deviceType, status) for filtered queries
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_devices_type_status'
    ) THEN
        CREATE INDEX idx_devices_type_status ON devices ("deviceType", status);
        RAISE NOTICE 'Added composite index on devices (deviceType, status)';
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES (Run these after migration)
-- ============================================================================

-- Verify view was created successfully
SELECT COUNT(*) as "Total Devices in Enriched View" FROM devices_enriched;

-- Check for devices with active assignments
SELECT COUNT(*) as "Currently Assigned Devices"
FROM devices_enriched
WHERE "assignmentStatus" = 'active';

-- Verify constraints were added
SELECT conname, contype
FROM pg_constraint
WHERE conrelid = 'devices'::regclass
ORDER BY conname;

-- Show sample enriched device data
SELECT id, name, status, "connectionStatus", "batteryStatus", "patientName", "patientLocation"
FROM devices_enriched
LIMIT 5;
