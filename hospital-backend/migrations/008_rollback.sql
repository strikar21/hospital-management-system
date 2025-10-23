-- ============================================================================
-- Migration 008 Rollback: Restore Redundant Device Assignment Fields
-- ============================================================================
-- Date: 2025-10-13
-- Purpose: Rollback migration 008 if needed
--
-- WARNING: This rollback restores the redundant columns but the application
-- code has been updated to NOT use them. If you rollback this migration,
-- you'll also need to rollback code changes from Phases 1-2.
--
-- WHEN TO USE THIS ROLLBACK:
--   - Migration 008 caused unexpected issues
--   - Need to revert to old schema temporarily
--   - Testing/debugging purposes
--
-- IMPORTANT: After running this rollback, the restored columns will be
-- populated from deviceassignments, but future updates may not maintain them
-- unless code is also rolled back.
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Restore devices.assignedPatientId Column
-- ============================================================================

-- Add column back if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'assignedPatientId'
    ) THEN
        ALTER TABLE devices ADD COLUMN "assignedPatientId" TEXT;
        RAISE NOTICE '✓ Restored column devices.assignedPatientId';
    ELSE
        RAISE NOTICE '⊘ Column devices.assignedPatientId already exists';
    END IF;
END $$;

-- ============================================================================
-- STEP 2: Restore patients.assignedDeviceId Column
-- ============================================================================

-- Add column back if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'patients' AND column_name = 'assignedDeviceId'
    ) THEN
        ALTER TABLE patients ADD COLUMN "assignedDeviceId" TEXT;
        RAISE NOTICE '✓ Restored column patients.assignedDeviceId';
    ELSE
        RAISE NOTICE '⊘ Column patients.assignedDeviceId already exists';
    END IF;
END $$;

-- ============================================================================
-- STEP 3: Repopulate Redundant Fields from deviceassignments
-- ============================================================================
-- Populate the restored columns with current assignment data

-- Populate devices.assignedPatientId from active assignments
UPDATE devices d
SET "assignedPatientId" = da."patientId"
FROM deviceassignments da
WHERE d.id = da."deviceId"
  AND da.status = 'active';

-- Report how many devices were updated
DO $$
DECLARE
    updated_devices INTEGER;
BEGIN
    SELECT COUNT(*) INTO updated_devices
    FROM devices
    WHERE "assignedPatientId" IS NOT NULL;

    RAISE NOTICE '✓ Populated devices.assignedPatientId for % devices', updated_devices;
END $$;

-- Populate patients.assignedDeviceId from active assignments
UPDATE patients p
SET "assignedDeviceId" = da."deviceId"
FROM deviceassignments da
WHERE p.id = da."patientId"
  AND da.status = 'active';

-- Report how many patients were updated
DO $$
DECLARE
    updated_patients INTEGER;
BEGIN
    SELECT COUNT(*) INTO updated_patients
    FROM patients
    WHERE "assignedDeviceId" IS NOT NULL;

    RAISE NOTICE '✓ Populated patients.assignedDeviceId for % patients', updated_patients;
END $$;

-- ============================================================================
-- STEP 4: Drop Performance Indices (Since we're going back to redundant design)
-- ============================================================================

DROP INDEX IF EXISTS idx_deviceassignments_patient_active;
DROP INDEX IF EXISTS idx_deviceassignments_device_active;

RAISE NOTICE '✓ Dropped deviceassignments performance indices';

-- ============================================================================
-- STEP 5: Verify Rollback
-- ============================================================================

DO $$
DECLARE
    devices_has_col BOOLEAN;
    patients_has_col BOOLEAN;
    devices_populated INTEGER;
    patients_populated INTEGER;
BEGIN
    -- Check columns exist
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'assignedPatientId'
    ) INTO devices_has_col;

    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'patients' AND column_name = 'assignedDeviceId'
    ) INTO patients_has_col;

    -- Count populated values
    SELECT COUNT(*) INTO devices_populated
    FROM devices WHERE "assignedPatientId" IS NOT NULL;

    SELECT COUNT(*) INTO patients_populated
    FROM patients WHERE "assignedDeviceId" IS NOT NULL;

    -- Report results
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Rollback 008 Verification Results:';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'devices.assignedPatientId restored: %', devices_has_col;
    RAISE NOTICE 'patients.assignedDeviceId restored: %', patients_has_col;
    RAISE NOTICE 'Devices with assignedPatientId: %', devices_populated;
    RAISE NOTICE 'Patients with assignedDeviceId: %', patients_populated;

    IF devices_has_col AND patients_has_col THEN
        RAISE NOTICE '✓ SUCCESS: Rollback complete, redundant columns restored';
        RAISE WARNING '⚠ REMINDER: Application code still uses JOINs - may need code rollback too';
    ELSE
        RAISE WARNING '⚠ INCOMPLETE: Some columns not restored';
    END IF;
    RAISE NOTICE '========================================';
END $$;

COMMIT;

-- ============================================================================
-- Rollback Complete
-- ============================================================================
-- Summary:
--   - Restored devices.assignedPatientId
--   - Restored patients.assignedDeviceId
--   - Repopulated fields from deviceassignments
--   - Removed performance indices
--
-- WARNING: Application code changes from Phases 1-2 are still in effect.
-- The code now uses JOINs and does not write to these redundant fields.
-- Consider whether code rollback is also needed.
-- ============================================================================
