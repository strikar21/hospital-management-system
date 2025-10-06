-- Add remaining FK constraints to medications table
-- Run AFTER 001_data_cleanup.sql
-- Note: fk_medications_patient already exists from previous run

-- ============================================
-- FK #2: medications.prescribedBy → staff.id
-- ============================================
-- Prevents deletion of staff who prescribed medications
-- Ensures prescribedBy always references valid staff member

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_medications_prescriber'
        AND table_name = 'medications'
    ) THEN
        ALTER TABLE medications
        ADD CONSTRAINT fk_medications_prescriber
        FOREIGN KEY ("prescribedBy") REFERENCES staff(id)
        ON DELETE RESTRICT;

        RAISE NOTICE 'Added constraint: fk_medications_prescriber';
    ELSE
        RAISE NOTICE 'Constraint already exists: fk_medications_prescriber';
    END IF;
END $$;

-- ============================================
-- FK #3: medications.createdBy → staff.id
-- ============================================
-- If creator deleted, set createdBy to NULL
-- Allows staff cleanup while preserving medication record

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_medications_creator'
        AND table_name = 'medications'
    ) THEN
        ALTER TABLE medications
        ADD CONSTRAINT fk_medications_creator
        FOREIGN KEY ("createdBy") REFERENCES staff(id)
        ON DELETE SET NULL;

        RAISE NOTICE 'Added constraint: fk_medications_creator';
    ELSE
        RAISE NOTICE 'Constraint already exists: fk_medications_creator';
    END IF;
END $$;

-- ============================================
-- Verification
-- ============================================
DO $$
DECLARE
    constraint_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO constraint_count
    FROM information_schema.table_constraints
    WHERE table_name = 'medications'
    AND constraint_type = 'FOREIGN KEY'
    AND constraint_name IN ('fk_medications_patient', 'fk_medications_prescriber', 'fk_medications_creator');

    RAISE NOTICE '===========================================';
    RAISE NOTICE 'FK Constraints Verification:';
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Total FK constraints on medications: %', constraint_count;
    RAISE NOTICE '===========================================';

    IF constraint_count = 3 THEN
        RAISE NOTICE '[SUCCESS] All 3 FK constraints exist!';
    ELSE
        RAISE WARNING '[WARNING] Expected 3 FK constraints, found %', constraint_count;
    END IF;
END $$;
