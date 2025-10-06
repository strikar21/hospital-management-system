-- Data Cleanup Migration for Day 2 Tables
-- Prepares data for FK constraint application on investigations, therapy, casesheetentries
-- Run BEFORE 002_add_foreign_keys.sql

-- ============================================
-- Step 1: Create missing staff records
-- ============================================
-- investigations table references LAB001 and RAD001 which don't exist
-- Create these staff records to maintain data integrity

-- Create LAB001 (Lab Technician)
INSERT INTO staff (id, role, email, "firstName", "lastName", "createdAt", "updatedAt")
VALUES ('LAB001', 'Lab Technician', 'lab@hospital.local', 'Laboratory', 'Services', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Create RAD001 (Radiologist)
INSERT INTO staff (id, role, email, "firstName", "lastName", "createdAt", "updatedAt")
VALUES ('RAD001', 'Radiologist', 'radiology@hospital.local', 'Radiology', 'Department', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

DO $$
BEGIN
    RAISE NOTICE 'Created missing staff records: LAB001, RAD001';
END $$;

-- ============================================
-- Step 2: Verify investigations table data
-- ============================================
DO $$
DECLARE
    invalid_patient_count INTEGER;
    invalid_prescriber_count INTEGER;
    invalid_performer_count INTEGER;
BEGIN
    -- Check for invalid patient IDs
    SELECT COUNT(*) INTO invalid_patient_count
    FROM investigations
    WHERE "patientId" NOT IN (SELECT id FROM patients);

    -- Check for invalid prescriber IDs
    SELECT COUNT(*) INTO invalid_prescriber_count
    FROM investigations
    WHERE "prescribedBy" IS NOT NULL
    AND "prescribedBy" NOT IN (SELECT id FROM staff);

    -- Check for invalid performer IDs
    SELECT COUNT(*) INTO invalid_performer_count
    FROM investigations
    WHERE "performedBy" IS NOT NULL
    AND "performedBy" NOT IN (SELECT id FROM staff);

    RAISE NOTICE '===========================================';
    RAISE NOTICE 'INVESTIGATIONS Table Data Validation:';
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Invalid patientId values: %', invalid_patient_count;
    RAISE NOTICE 'Invalid prescribedBy values: %', invalid_prescriber_count;
    RAISE NOTICE 'Invalid performedBy values: %', invalid_performer_count;

    IF invalid_patient_count > 0 OR invalid_prescriber_count > 0 OR invalid_performer_count > 0 THEN
        RAISE EXCEPTION 'INVESTIGATIONS: Data validation failed - still have invalid FK values!';
    END IF;

    RAISE NOTICE 'INVESTIGATIONS: Data validation passed!';
END $$;

-- ============================================
-- Step 3: Verify therapy table data
-- ============================================
DO $$
DECLARE
    invalid_patient_count INTEGER;
    invalid_prescriber_count INTEGER;
BEGIN
    -- Check for invalid patient IDs
    SELECT COUNT(*) INTO invalid_patient_count
    FROM therapy
    WHERE "patientId" NOT IN (SELECT id FROM patients);

    -- Check for invalid prescriber IDs
    SELECT COUNT(*) INTO invalid_prescriber_count
    FROM therapy
    WHERE "prescribedBy" IS NOT NULL
    AND "prescribedBy" NOT IN (SELECT id FROM staff);

    RAISE NOTICE '===========================================';
    RAISE NOTICE 'THERAPY Table Data Validation:';
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Invalid patientId values: %', invalid_patient_count;
    RAISE NOTICE 'Invalid prescribedBy values: %', invalid_prescriber_count;

    IF invalid_patient_count > 0 OR invalid_prescriber_count > 0 THEN
        RAISE EXCEPTION 'THERAPY: Data validation failed - still have invalid FK values!';
    END IF;

    RAISE NOTICE 'THERAPY: Data validation passed!';
END $$;

-- ============================================
-- Step 4: Verify casesheetentries table data
-- ============================================
DO $$
DECLARE
    row_count INTEGER;
    invalid_patient_count INTEGER;
    invalid_creator_count INTEGER;
    invalid_performer_count INTEGER;
BEGIN
    -- Check if table has data
    SELECT COUNT(*) INTO row_count FROM casesheetentries;

    IF row_count = 0 THEN
        RAISE NOTICE '===========================================';
        RAISE NOTICE 'CASESHEETENTRIES Table Data Validation:';
        RAISE NOTICE '===========================================';
        RAISE NOTICE 'Table is empty - no validation needed';
        RETURN;
    END IF;

    -- Check for invalid patient IDs
    SELECT COUNT(*) INTO invalid_patient_count
    FROM casesheetentries
    WHERE "patientId" NOT IN (SELECT id FROM patients);

    -- Check for invalid creator IDs
    SELECT COUNT(*) INTO invalid_creator_count
    FROM casesheetentries
    WHERE "createdBy" IS NOT NULL
    AND "createdBy" NOT IN (SELECT id FROM staff);

    -- Check for invalid performer IDs
    SELECT COUNT(*) INTO invalid_performer_count
    FROM casesheetentries
    WHERE "performedBy" NOT IN (SELECT id FROM staff);

    RAISE NOTICE '===========================================';
    RAISE NOTICE 'CASESHEETENTRIES Table Data Validation:';
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Invalid patientId values: %', invalid_patient_count;
    RAISE NOTICE 'Invalid createdBy values: %', invalid_creator_count;
    RAISE NOTICE 'Invalid performedBy values: %', invalid_performer_count;

    IF invalid_patient_count > 0 OR invalid_creator_count > 0 OR invalid_performer_count > 0 THEN
        RAISE EXCEPTION 'CASESHEETENTRIES: Data validation failed - still have invalid FK values!';
    END IF;

    RAISE NOTICE 'CASESHEETENTRIES: Data validation passed!';
END $$;

-- ============================================
-- Step 5: Final Summary
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Day 2 Data Cleanup Complete!';
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'All tables ready for FK constraint application';
END $$;
