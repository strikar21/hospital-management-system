-- Rollback for Day 2 FK Constraints
-- Removes all FK constraints added in 002_add_foreign_keys.sql

-- ============================================
-- Remove INVESTIGATIONS FK Constraints
-- ============================================

-- Drop fk_investigations_prescriber
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_investigations_prescriber'
        AND table_name = 'investigations'
    ) THEN
        ALTER TABLE investigations DROP CONSTRAINT fk_investigations_prescriber;
        RAISE NOTICE 'Dropped constraint: fk_investigations_prescriber';
    ELSE
        RAISE NOTICE 'Constraint does not exist: fk_investigations_prescriber';
    END IF;
END $$;

-- Drop fk_investigations_performer
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_investigations_performer'
        AND table_name = 'investigations'
    ) THEN
        ALTER TABLE investigations DROP CONSTRAINT fk_investigations_performer;
        RAISE NOTICE 'Dropped constraint: fk_investigations_performer';
    ELSE
        RAISE NOTICE 'Constraint does not exist: fk_investigations_performer';
    END IF;
END $$;

-- Note: fk_investigations_patient is NOT dropped (was created before Day 2)

-- ============================================
-- Remove THERAPY FK Constraints
-- ============================================

-- Drop fk_therapy_patient
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_therapy_patient'
        AND table_name = 'therapy'
    ) THEN
        ALTER TABLE therapy DROP CONSTRAINT fk_therapy_patient;
        RAISE NOTICE 'Dropped constraint: fk_therapy_patient';
    ELSE
        RAISE NOTICE 'Constraint does not exist: fk_therapy_patient';
    END IF;
END $$;

-- Drop fk_therapy_prescriber
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_therapy_prescriber'
        AND table_name = 'therapy'
    ) THEN
        ALTER TABLE therapy DROP CONSTRAINT fk_therapy_prescriber;
        RAISE NOTICE 'Dropped constraint: fk_therapy_prescriber';
    ELSE
        RAISE NOTICE 'Constraint does not exist: fk_therapy_prescriber';
    END IF;
END $$;

-- ============================================
-- Remove CASESHEETENTRIES FK Constraints
-- ============================================

-- Drop fk_casesheetentries_patient
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_casesheetentries_patient'
        AND table_name = 'casesheetentries'
    ) THEN
        ALTER TABLE casesheetentries DROP CONSTRAINT fk_casesheetentries_patient;
        RAISE NOTICE 'Dropped constraint: fk_casesheetentries_patient';
    ELSE
        RAISE NOTICE 'Constraint does not exist: fk_casesheetentries_patient';
    END IF;
END $$;

-- Drop fk_casesheetentries_creator
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_casesheetentries_creator'
        AND table_name = 'casesheetentries'
    ) THEN
        ALTER TABLE casesheetentries DROP CONSTRAINT fk_casesheetentries_creator;
        RAISE NOTICE 'Dropped constraint: fk_casesheetentries_creator';
    ELSE
        RAISE NOTICE 'Constraint does not exist: fk_casesheetentries_creator';
    END IF;
END $$;

-- Drop fk_casesheetentries_performer
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_casesheetentries_performer'
        AND table_name = 'casesheetentries'
    ) THEN
        ALTER TABLE casesheetentries DROP CONSTRAINT fk_casesheetentries_performer;
        RAISE NOTICE 'Dropped constraint: fk_casesheetentries_performer';
    ELSE
        RAISE NOTICE 'Constraint does not exist: fk_casesheetentries_performer';
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
    -- Count remaining FK constraints
    SELECT COUNT(*) INTO investigations_fk_count
    FROM information_schema.table_constraints
    WHERE table_name = 'investigations'
    AND constraint_type = 'FOREIGN KEY'
    AND constraint_name IN ('fk_investigations_prescriber', 'fk_investigations_performer');

    SELECT COUNT(*) INTO therapy_fk_count
    FROM information_schema.table_constraints
    WHERE table_name = 'therapy'
    AND constraint_type = 'FOREIGN KEY';

    SELECT COUNT(*) INTO casesheetentries_fk_count
    FROM information_schema.table_constraints
    WHERE table_name = 'casesheetentries'
    AND constraint_type = 'FOREIGN KEY';

    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Rollback Verification:';
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'investigations Day 2 FK constraints: %', investigations_fk_count;
    RAISE NOTICE 'therapy FK constraints: %', therapy_fk_count;
    RAISE NOTICE 'casesheetentries FK constraints: %', casesheetentries_fk_count;
    RAISE NOTICE '===========================================';

    IF investigations_fk_count = 0 AND therapy_fk_count = 0 AND casesheetentries_fk_count = 0 THEN
        RAISE NOTICE '[SUCCESS] All Day 2 FK constraints removed!';
    ELSE
        RAISE WARNING '[WARNING] Some FK constraints still exist';
    END IF;
END $$;
