-- Add CHECK Constraints for Data Validation
-- Day 3: Add validation rules to prevent invalid data
-- Run AFTER Days 1-2 FK constraints are in place

-- ============================================
-- MEDICATIONS Table CHECK Constraints
-- ============================================

-- Status validation
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'medications_status_check'
    ) THEN
        ALTER TABLE medications
        ADD CONSTRAINT medications_status_check
        CHECK (status IN ('active', 'held', 'discontinued', 'completed'));

        RAISE NOTICE 'Added constraint: medications_status_check';
    ELSE
        RAISE NOTICE 'Constraint already exists: medications_status_check';
    END IF;
END $$;

-- Route validation (allow common medical routes)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'medications_route_check'
    ) THEN
        ALTER TABLE medications
        ADD CONSTRAINT medications_route_check
        CHECK (route IN (
            'PO', 'Oral', 'IV', 'IM', 'SC', 'SQ', 'Sublingual',
            'Topical', 'Rectal', 'Inhalation', 'Nebulizer',
            'Nasal', 'Ophthalmic', 'Otic', 'Transdermal', 'Per NGT'
        ));

        RAISE NOTICE 'Added constraint: medications_route_check';
    ELSE
        RAISE NOTICE 'Constraint already exists: medications_route_check';
    END IF;
END $$;

-- Date range validation (endDate must be >= startDate when both exist)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'medications_date_range_check'
    ) THEN
        ALTER TABLE medications
        ADD CONSTRAINT medications_date_range_check
        CHECK (
            "endDate" IS NULL OR
            "startDate" IS NULL OR
            "endDate" >= "startDate"
        );

        RAISE NOTICE 'Added constraint: medications_date_range_check';
    ELSE
        RAISE NOTICE 'Constraint already exists: medications_date_range_check';
    END IF;
END $$;

-- ============================================
-- INVESTIGATIONS Table CHECK Constraints
-- ============================================

-- Status validation
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'investigations_status_check'
    ) THEN
        ALTER TABLE investigations
        ADD CONSTRAINT investigations_status_check
        CHECK (status IN ('pending', 'scheduled', 'in_progress', 'completed', 'cancelled'));

        RAISE NOTICE 'Added constraint: investigations_status_check';
    ELSE
        RAISE NOTICE 'Constraint already exists: investigations_status_check';
    END IF;
END $$;

-- Priority validation (case-insensitive)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'investigations_priority_check'
    ) THEN
        ALTER TABLE investigations
        ADD CONSTRAINT investigations_priority_check
        CHECK (LOWER(priority) IN ('routine', 'urgent', 'stat', 'emergency'));

        RAISE NOTICE 'Added constraint: investigations_priority_check';
    ELSE
        RAISE NOTICE 'Constraint already exists: investigations_priority_check';
    END IF;
END $$;

-- Urgency validation (case-insensitive)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'investigations_urgency_check'
    ) THEN
        ALTER TABLE investigations
        ADD CONSTRAINT investigations_urgency_check
        CHECK (LOWER(urgency) IN ('routine', 'urgent', 'stat', 'emergency'));

        RAISE NOTICE 'Added constraint: investigations_urgency_check';
    ELSE
        RAISE NOTICE 'Constraint already exists: investigations_urgency_check';
    END IF;
END $$;

-- ============================================
-- THERAPY Table CHECK Constraints
-- ============================================

-- Status validation
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'therapy_status_check'
    ) THEN
        ALTER TABLE therapy
        ADD CONSTRAINT therapy_status_check
        CHECK (status IN ('active', 'inactive', 'completed', 'discontinued'));

        RAISE NOTICE 'Added constraint: therapy_status_check';
    ELSE
        RAISE NOTICE 'Constraint already exists: therapy_status_check';
    END IF;
END $$;

-- Date range validation
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'therapy_date_range_check'
    ) THEN
        ALTER TABLE therapy
        ADD CONSTRAINT therapy_date_range_check
        CHECK (
            "endDate" IS NULL OR
            "startDate" IS NULL OR
            "endDate" >= "startDate"
        );

        RAISE NOTICE 'Added constraint: therapy_date_range_check';
    ELSE
        RAISE NOTICE 'Constraint already exists: therapy_date_range_check';
    END IF;
END $$;

-- ============================================
-- PATIENTS Table CHECK Constraints
-- ============================================

-- Status validation
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'patients_status_check'
    ) THEN
        ALTER TABLE patients
        ADD CONSTRAINT patients_status_check
        CHECK (status IN ('active', 'discharged', 'deceased', 'transferred'));

        RAISE NOTICE 'Added constraint: patients_status_check';
    ELSE
        RAISE NOTICE 'Constraint already exists: patients_status_check';
    END IF;
END $$;

-- Gender validation (case-sensitive to match existing data)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'patients_gender_check'
    ) THEN
        ALTER TABLE patients
        ADD CONSTRAINT patients_gender_check
        CHECK (gender IN ('Male', 'Female', 'Other', 'Prefer not to say'));

        RAISE NOTICE 'Added constraint: patients_gender_check';
    ELSE
        RAISE NOTICE 'Constraint already exists: patients_gender_check';
    END IF;
END $$;

-- Date of birth validation (cannot be in the future)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'patients_dob_check'
    ) THEN
        ALTER TABLE patients
        ADD CONSTRAINT patients_dob_check
        CHECK ("dateOfBirth" <= CURRENT_DATE);

        RAISE NOTICE 'Added constraint: patients_dob_check';
    ELSE
        RAISE NOTICE 'Constraint already exists: patients_dob_check';
    END IF;
END $$;

-- ============================================
-- STAFF Table CHECK Constraints
-- ============================================

-- Role validation (case-sensitive to match existing data)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'staff_role_check'
    ) THEN
        ALTER TABLE staff
        ADD CONSTRAINT staff_role_check
        CHECK (role IN (
            'Doctor', 'Nurse', 'Administrator', 'Lab Technician',
            'Radiologist', 'Technician', 'Pharmacist', 'Therapist',
            'Receptionist', 'system'
        ));

        RAISE NOTICE 'Added constraint: staff_role_check';
    ELSE
        RAISE NOTICE 'Constraint already exists: staff_role_check';
    END IF;
END $$;

-- ============================================
-- Verification
-- ============================================
DO $$
DECLARE
    total_constraints INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_constraints
    FROM pg_constraint
    WHERE conname LIKE '%_check'
    AND conname IN (
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
    RAISE NOTICE 'CHECK Constraints Verification:';
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Total CHECK constraints: %', total_constraints;
    RAISE NOTICE '===========================================';

    IF total_constraints = 12 THEN
        RAISE NOTICE '[SUCCESS] All 12 CHECK constraints exist!';
    ELSE
        RAISE WARNING '[WARNING] Expected 12 CHECK constraints, found %', total_constraints;
    END IF;
END $$;
