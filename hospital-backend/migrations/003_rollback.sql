-- Rollback for Day 3 CHECK Constraints
-- Removes all CHECK constraints added in 003_add_check_constraints.sql

-- ============================================
-- Remove MEDICATIONS CHECK Constraints
-- ============================================

-- Drop medications_status_check
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'medications_status_check'
    ) THEN
        ALTER TABLE medications DROP CONSTRAINT medications_status_check;
        RAISE NOTICE 'Dropped constraint: medications_status_check';
    ELSE
        RAISE NOTICE 'Constraint does not exist: medications_status_check';
    END IF;
END $$;

-- Drop medications_route_check
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'medications_route_check'
    ) THEN
        ALTER TABLE medications DROP CONSTRAINT medications_route_check;
        RAISE NOTICE 'Dropped constraint: medications_route_check';
    ELSE
        RAISE NOTICE 'Constraint does not exist: medications_route_check';
    END IF;
END $$;

-- Drop medications_date_range_check
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'medications_date_range_check'
    ) THEN
        ALTER TABLE medications DROP CONSTRAINT medications_date_range_check;
        RAISE NOTICE 'Dropped constraint: medications_date_range_check';
    ELSE
        RAISE NOTICE 'Constraint does not exist: medications_date_range_check';
    END IF;
END $$;

-- ============================================
-- Remove INVESTIGATIONS CHECK Constraints
-- ============================================

-- Drop investigations_status_check
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'investigations_status_check'
    ) THEN
        ALTER TABLE investigations DROP CONSTRAINT investigations_status_check;
        RAISE NOTICE 'Dropped constraint: investigations_status_check';
    ELSE
        RAISE NOTICE 'Constraint does not exist: investigations_status_check';
    END IF;
END $$;

-- Drop investigations_priority_check
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'investigations_priority_check'
    ) THEN
        ALTER TABLE investigations DROP CONSTRAINT investigations_priority_check;
        RAISE NOTICE 'Dropped constraint: investigations_priority_check';
    ELSE
        RAISE NOTICE 'Constraint does not exist: investigations_priority_check';
    END IF;
END $$;

-- Drop investigations_urgency_check
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'investigations_urgency_check'
    ) THEN
        ALTER TABLE investigations DROP CONSTRAINT investigations_urgency_check;
        RAISE NOTICE 'Dropped constraint: investigations_urgency_check';
    ELSE
        RAISE NOTICE 'Constraint does not exist: investigations_urgency_check';
    END IF;
END $$;

-- ============================================
-- Remove THERAPY CHECK Constraints
-- ============================================

-- Drop therapy_status_check
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'therapy_status_check'
    ) THEN
        ALTER TABLE therapy DROP CONSTRAINT therapy_status_check;
        RAISE NOTICE 'Dropped constraint: therapy_status_check';
    ELSE
        RAISE NOTICE 'Constraint does not exist: therapy_status_check';
    END IF;
END $$;

-- Drop therapy_date_range_check
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'therapy_date_range_check'
    ) THEN
        ALTER TABLE therapy DROP CONSTRAINT therapy_date_range_check;
        RAISE NOTICE 'Dropped constraint: therapy_date_range_check';
    ELSE
        RAISE NOTICE 'Constraint does not exist: therapy_date_range_check';
    END IF;
END $$;

-- ============================================
-- Remove PATIENTS CHECK Constraints
-- ============================================

-- Drop patients_status_check
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'patients_status_check'
    ) THEN
        ALTER TABLE patients DROP CONSTRAINT patients_status_check;
        RAISE NOTICE 'Dropped constraint: patients_status_check';
    ELSE
        RAISE NOTICE 'Constraint does not exist: patients_status_check';
    END IF;
END $$;

-- Drop patients_gender_check
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'patients_gender_check'
    ) THEN
        ALTER TABLE patients DROP CONSTRAINT patients_gender_check;
        RAISE NOTICE 'Dropped constraint: patients_gender_check';
    ELSE
        RAISE NOTICE 'Constraint does not exist: patients_gender_check';
    END IF;
END $$;

-- Drop patients_dob_check
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'patients_dob_check'
    ) THEN
        ALTER TABLE patients DROP CONSTRAINT patients_dob_check;
        RAISE NOTICE 'Dropped constraint: patients_dob_check';
    ELSE
        RAISE NOTICE 'Constraint does not exist: patients_dob_check';
    END IF;
END $$;

-- ============================================
-- Remove STAFF CHECK Constraints
-- ============================================

-- Drop staff_role_check
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'staff_role_check'
    ) THEN
        ALTER TABLE staff DROP CONSTRAINT staff_role_check;
        RAISE NOTICE 'Dropped constraint: staff_role_check';
    ELSE
        RAISE NOTICE 'Constraint does not exist: staff_role_check';
    END IF;
END $$;

-- ============================================
-- Verification
-- ============================================
DO $$
DECLARE
    remaining_constraints INTEGER;
BEGIN
    SELECT COUNT(*) INTO remaining_constraints
    FROM pg_constraint
    WHERE conname IN (
        'medications_status_check',
        'medications_route_check',
        'medications_date_range_check',
        'investigations_status_check',
        'investigations_priority_check',
        'investigations_urgency_check',
        'therapy_status_check',
        'therapy_date_range_check',
        'patients_status_check',
        'patients_gender_check',
        'patients_dob_check',
        'staff_role_check'
    );

    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Rollback Verification:';
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Remaining Day 3 CHECK constraints: %', remaining_constraints;
    RAISE NOTICE '===========================================';

    IF remaining_constraints = 0 THEN
        RAISE NOTICE '[SUCCESS] All Day 3 CHECK constraints removed!';
    ELSE
        RAISE WARNING '[WARNING] Some CHECK constraints still exist';
    END IF;
END $$;
