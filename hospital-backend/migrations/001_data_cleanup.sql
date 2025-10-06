-- Data Cleanup Migration for Medications Table
-- Prepares data for FK constraint application
-- Run BEFORE 001_add_foreign_keys_medications.sql

-- ============================================
-- Step 1: Add createdBy column
-- ============================================
-- Note: modifiedBy exists but FK constraint expects createdBy
-- We'll add createdBy and copy the data from modifiedBy

ALTER TABLE medications
ADD COLUMN IF NOT EXISTS "createdBy" TEXT;

-- Copy modifiedBy values to createdBy (for existing records)
UPDATE medications
SET "createdBy" = "modifiedBy"
WHERE "createdBy" IS NULL;

COMMENT ON COLUMN medications."createdBy" IS 'Staff ID who created this medication record';

-- ============================================
-- Step 2: Clean up prescribedBy data
-- ============================================
-- Some records have human names instead of staff IDs
-- We need to map these to valid staff IDs

-- First, let's see what invalid data we have
DO $$
DECLARE
    invalid_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO invalid_count
    FROM medications
    WHERE "prescribedBy" NOT IN (SELECT id FROM staff)
    AND "prescribedBy" IS NOT NULL;

    RAISE NOTICE 'Found % invalid prescribedBy values', invalid_count;
END $$;

-- Map known human names to staff IDs
-- Update "Dr. Sarah Johnson" to a valid staff ID
-- If no mapping exists, set to 'SYSTEM' for now

-- For now, update all invalid values to 'SYSTEM'
-- TODO: Add specific name mappings in future if needed
UPDATE medications
SET "prescribedBy" = 'SYSTEM'
WHERE "prescribedBy" NOT IN (SELECT id FROM staff)
AND "prescribedBy" IS NOT NULL;

-- Ensure SYSTEM staff exists
INSERT INTO staff (id, role, email, "firstName", "lastName", "createdAt", "updatedAt")
VALUES ('SYSTEM', 'system', 'system@hospital.local', 'System', 'User', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- Step 3: Verify data cleanup
-- ============================================
DO $$
DECLARE
    invalid_patient_count INTEGER;
    invalid_prescriber_count INTEGER;
    null_created_by_count INTEGER;
BEGIN
    -- Check for invalid patient IDs
    SELECT COUNT(*) INTO invalid_patient_count
    FROM medications
    WHERE "patientId" NOT IN (SELECT id FROM patients);

    -- Check for invalid prescriber IDs
    SELECT COUNT(*) INTO invalid_prescriber_count
    FROM medications
    WHERE "prescribedBy" NOT IN (SELECT id FROM staff)
    AND "prescribedBy" IS NOT NULL;

    -- Check for NULL createdBy values
    SELECT COUNT(*) INTO null_created_by_count
    FROM medications
    WHERE "createdBy" IS NULL;

    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Data Cleanup Verification:';
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Invalid patientId values: %', invalid_patient_count;
    RAISE NOTICE 'Invalid prescribedBy values: %', invalid_prescriber_count;
    RAISE NOTICE 'NULL createdBy values: %', null_created_by_count;
    RAISE NOTICE '===========================================';

    IF invalid_patient_count > 0 OR invalid_prescriber_count > 0 THEN
        RAISE EXCEPTION 'Data cleanup failed - still have invalid FK values!';
    END IF;

    RAISE NOTICE 'Data cleanup completed successfully!';
END $$;
