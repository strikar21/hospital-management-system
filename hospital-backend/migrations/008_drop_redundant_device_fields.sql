-- ============================================================================
-- Migration 008: Drop Redundant Device Assignment Fields
-- ============================================================================
-- Date: 2025-10-13
-- Issue: Database denormalization - device-patient relationship stored in 3 places
-- Solution: deviceassignments table is single source of truth
--
-- REDUNDANCY PROBLEM:
-- Before this migration, device-patient assignments were stored in THREE places:
--   1. deviceassignments table (proper normalized JOIN table) ✅
--   2. devices.assignedPatientId (redundant duplicate)      ❌
--   3. patients.assignedDeviceId (redundant duplicate)      ❌
--
-- This migration removes #2 and #3, leaving deviceassignments as the single
-- source of truth (3NF - Third Normal Form).
--
-- SAFETY: Code has been updated in Phases 1-2 to:
--   - Use JOINs to deviceassignments for all reads
--   - Stop writing to redundant fields
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Pre-Migration Data Consistency Check
-- ============================================================================
-- This query checks if redundant fields are consistent with deviceassignments.
-- If this returns rows, it means there are data inconsistencies that should be
-- investigated before dropping columns.

DO $$
DECLARE
    inconsistent_count INTEGER;
BEGIN
    -- Check devices.assignedPatientId consistency
    SELECT COUNT(*) INTO inconsistent_count
    FROM devices d
    LEFT JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
    WHERE d."assignedPatientId" IS DISTINCT FROM da."patientId";

    IF inconsistent_count > 0 THEN
        RAISE WARNING 'Found % devices with inconsistent assignedPatientId', inconsistent_count;
    ELSE
        RAISE NOTICE '✓ All devices.assignedPatientId values are consistent with deviceassignments';
    END IF;

    -- Check patients.assignedDeviceId consistency
    SELECT COUNT(*) INTO inconsistent_count
    FROM patients p
    LEFT JOIN deviceassignments da ON p.id = da."patientId" AND da.status = 'active'
    WHERE p."assignedDeviceId" IS DISTINCT FROM da."deviceId";

    IF inconsistent_count > 0 THEN
        RAISE WARNING 'Found % patients with inconsistent assignedDeviceId', inconsistent_count;
    ELSE
        RAISE NOTICE '✓ All patients.assignedDeviceId values are consistent with deviceassignments';
    END IF;
END $$;

-- ============================================================================
-- STEP 2: Drop Redundant Column from devices Table
-- ============================================================================
-- Remove devices.assignedPatientId - this information is now ONLY in deviceassignments

-- Check if column exists before dropping
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'assignedPatientId'
    ) THEN
        ALTER TABLE devices DROP COLUMN "assignedPatientId";
        RAISE NOTICE '✓ Dropped column devices.assignedPatientId';
    ELSE
        RAISE NOTICE '⊘ Column devices.assignedPatientId does not exist (already dropped)';
    END IF;
END $$;

-- ============================================================================
-- STEP 3: Drop Redundant Column from patients Table
-- ============================================================================
-- Remove patients.assignedDeviceId - this information is now ONLY in deviceassignments

-- Check if column exists before dropping
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'patients' AND column_name = 'assignedDeviceId'
    ) THEN
        ALTER TABLE patients DROP COLUMN "assignedDeviceId";
        RAISE NOTICE '✓ Dropped column patients.assignedDeviceId';
    ELSE
        RAISE NOTICE '⊘ Column patients.assignedDeviceId does not exist (already dropped)';
    END IF;
END $$;

-- ============================================================================
-- STEP 4: Verify Single Source of Truth
-- ============================================================================
-- Confirm deviceassignments is now the only place tracking assignments

DO $$
DECLARE
    active_assignments_count INTEGER;
    devices_has_col BOOLEAN;
    patients_has_col BOOLEAN;
BEGIN
    -- Count active assignments in deviceassignments
    SELECT COUNT(*) INTO active_assignments_count
    FROM deviceassignments
    WHERE status = 'active';

    -- Verify columns no longer exist
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'assignedPatientId'
    ) INTO devices_has_col;

    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'patients' AND column_name = 'assignedDeviceId'
    ) INTO patients_has_col;

    -- Report results
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration 008 Verification Results:';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Active device assignments: %', active_assignments_count;
    RAISE NOTICE 'devices.assignedPatientId exists: %', devices_has_col;
    RAISE NOTICE 'patients.assignedDeviceId exists: %', patients_has_col;

    IF NOT devices_has_col AND NOT patients_has_col THEN
        RAISE NOTICE '✓ SUCCESS: Redundant columns removed, deviceassignments is single source of truth';
    ELSE
        RAISE WARNING '⚠ INCOMPLETE: Some redundant columns still exist';
    END IF;
    RAISE NOTICE '========================================';
END $$;

-- ============================================================================
-- STEP 5: Add Performance Indices (Optional but Recommended)
-- ============================================================================
-- These indices optimize JOIN queries from code that now uses deviceassignments

-- Index for finding device by patient (common in vitals submission, discharge)
CREATE INDEX IF NOT EXISTS idx_deviceassignments_patient_active
    ON deviceassignments("patientId")
    WHERE status = 'active';

-- Index for finding patient by device (common in door scanner, ESP32 heartbeat)
CREATE INDEX IF NOT EXISTS idx_deviceassignments_device_active
    ON deviceassignments("deviceId")
    WHERE status = 'active';

RAISE NOTICE '✓ Created performance indices on deviceassignments';

COMMIT;

-- ============================================================================
-- Migration Complete
-- ============================================================================
-- Summary:
--   - Dropped devices.assignedPatientId (redundant)
--   - Dropped patients.assignedDeviceId (redundant)
--   - deviceassignments table is now single source of truth
--   - Added indices for JOIN performance
--   - Database is now in 3NF (Third Normal Form)
--
-- Next steps:
--   1. Update database.py schema definition (Phase 4)
--   2. Run comprehensive tests (Phase 5)
--
-- Rollback: See 008_rollback.sql if needed
-- ============================================================================
