-- Add Foreign Key Constraints to Day 2 Tables
-- Tables: investigations, therapy, casesheetentries
-- Run AFTER 002_data_cleanup.sql

-- ============================================
-- INVESTIGATIONS TABLE
-- ============================================
-- Note: fk_investigations_patient already exists

-- FK: investigations.prescribedBy -> staff.id (RESTRICT)
-- Prevents deletion of staff who ordered investigations
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_investigations_prescriber'
        AND table_name = 'investigations'
    ) THEN
        ALTER TABLE investigations
        ADD CONSTRAINT fk_investigations_prescriber
        FOREIGN KEY ("prescribedBy") REFERENCES staff(id)
        ON DELETE RESTRICT;

        RAISE NOTICE 'Added constraint: fk_investigations_prescriber';
    ELSE
        RAISE NOTICE 'Constraint already exists: fk_investigations_prescriber';
    END IF;
END $$;

-- FK: investigations.performedBy -> staff.id (SET NULL)
-- If performer deleted, set performedBy to NULL
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_investigations_performer'
        AND table_name = 'investigations'
    ) THEN
        ALTER TABLE investigations
        ADD CONSTRAINT fk_investigations_performer
        FOREIGN KEY ("performedBy") REFERENCES staff(id)
        ON DELETE SET NULL;

        RAISE NOTICE 'Added constraint: fk_investigations_performer';
    ELSE
        RAISE NOTICE 'Constraint already exists: fk_investigations_performer';
    END IF;
END $$;

-- ============================================
-- THERAPY TABLE
-- ============================================

-- FK: therapy.patientId -> patients.id (CASCADE)
-- When patient deleted, delete all their therapy records
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_therapy_patient'
        AND table_name = 'therapy'
    ) THEN
        ALTER TABLE therapy
        ADD CONSTRAINT fk_therapy_patient
        FOREIGN KEY ("patientId") REFERENCES patients(id)
        ON DELETE CASCADE;

        RAISE NOTICE 'Added constraint: fk_therapy_patient';
    ELSE
        RAISE NOTICE 'Constraint already exists: fk_therapy_patient';
    END IF;
END $$;

-- FK: therapy.prescribedBy -> staff.id (RESTRICT)
-- Prevents deletion of staff who prescribed therapy
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_therapy_prescriber'
        AND table_name = 'therapy'
    ) THEN
        ALTER TABLE therapy
        ADD CONSTRAINT fk_therapy_prescriber
        FOREIGN KEY ("prescribedBy") REFERENCES staff(id)
        ON DELETE RESTRICT;

        RAISE NOTICE 'Added constraint: fk_therapy_prescriber';
    ELSE
        RAISE NOTICE 'Constraint already exists: fk_therapy_prescriber';
    END IF;
END $$;

-- ============================================
-- CASESHEETENTRIES TABLE
-- ============================================

-- FK: casesheetentries.patientId -> patients.id (CASCADE)
-- When patient deleted, delete all their case sheet entries
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_casesheetentries_patient'
        AND table_name = 'casesheetentries'
    ) THEN
        ALTER TABLE casesheetentries
        ADD CONSTRAINT fk_casesheetentries_patient
        FOREIGN KEY ("patientId") REFERENCES patients(id)
        ON DELETE CASCADE;

        RAISE NOTICE 'Added constraint: fk_casesheetentries_patient';
    ELSE
        RAISE NOTICE 'Constraint already exists: fk_casesheetentries_patient';
    END IF;
END $$;

-- FK: casesheetentries.createdBy -> staff.id (SET NULL)
-- If creator deleted, set createdBy to NULL
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_casesheetentries_creator'
        AND table_name = 'casesheetentries'
    ) THEN
        ALTER TABLE casesheetentries
        ADD CONSTRAINT fk_casesheetentries_creator
        FOREIGN KEY ("createdBy") REFERENCES staff(id)
        ON DELETE SET NULL;

        RAISE NOTICE 'Added constraint: fk_casesheetentries_creator';
    ELSE
        RAISE NOTICE 'Constraint already exists: fk_casesheetentries_creator';
    END IF;
END $$;

-- FK: casesheetentries.performedBy -> staff.id (RESTRICT)
-- Prevents deletion of staff who performed case sheet entries
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_casesheetentries_performer'
        AND table_name = 'casesheetentries'
    ) THEN
        ALTER TABLE casesheetentries
        ADD CONSTRAINT fk_casesheetentries_performer
        FOREIGN KEY ("performedBy") REFERENCES staff(id)
        ON DELETE RESTRICT;

        RAISE NOTICE 'Added constraint: fk_casesheetentries_performer';
    ELSE
        RAISE NOTICE 'Constraint already exists: fk_casesheetentries_performer';
    END IF;
END $$;

-- ============================================
-- Verification
-- ============================================
DO $$
DECLARE
    investigations_fk_count INTEGER;
    therapy_fk_count INTEGER;
    casesheetentries_fk_count INTEGER;
BEGIN
    -- Count FK constraints for each table
    SELECT COUNT(*) INTO investigations_fk_count
    FROM information_schema.table_constraints
    WHERE table_name = 'investigations'
    AND constraint_type = 'FOREIGN KEY'
    AND constraint_name IN ('fk_investigations_patient', 'fk_investigations_prescriber', 'fk_investigations_performer');

    SELECT COUNT(*) INTO therapy_fk_count
    FROM information_schema.table_constraints
    WHERE table_name = 'therapy'
    AND constraint_type = 'FOREIGN KEY'
    AND constraint_name IN ('fk_therapy_patient', 'fk_therapy_prescriber');

    SELECT COUNT(*) INTO casesheetentries_fk_count
    FROM information_schema.table_constraints
    WHERE table_name = 'casesheetentries'
    AND constraint_type = 'FOREIGN KEY'
    AND constraint_name IN ('fk_casesheetentries_patient', 'fk_casesheetentries_creator', 'fk_casesheetentries_performer');

    RAISE NOTICE '===========================================';
    RAISE NOTICE 'FK Constraints Verification:';
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'investigations: % of 3 FK constraints', investigations_fk_count;
    RAISE NOTICE 'therapy: % of 2 FK constraints', therapy_fk_count;
    RAISE NOTICE 'casesheetentries: % of 3 FK constraints', casesheetentries_fk_count;
    RAISE NOTICE '===========================================';

    IF investigations_fk_count = 3 AND therapy_fk_count = 2 AND casesheetentries_fk_count = 3 THEN
        RAISE NOTICE '[SUCCESS] All Day 2 FK constraints exist!';
    ELSE
        RAISE WARNING '[WARNING] Some FK constraints missing!';
    END IF;
END $$;
