-- Migration 004: Add remaining audit trail fields (createdBy, editedBy)
-- Date: 2025-10-06
-- Purpose: Complete staff field naming standardization
-- Adds createdBy to 5 medical tables and editedBy to patientnotes

-- ============================================================
-- STEP 1: Add createdBy to medicationadministrations
-- ============================================================
ALTER TABLE medicationadministrations
ADD COLUMN IF NOT EXISTS "createdBy" TEXT;

COMMENT ON COLUMN medicationadministrations."createdBy" IS 'Staff who created the administration record (audit trail)';

-- ============================================================
-- STEP 2: Add createdBy to investigations
-- ============================================================
ALTER TABLE investigations
ADD COLUMN IF NOT EXISTS "createdBy" TEXT;

COMMENT ON COLUMN investigations."createdBy" IS 'Staff who created the investigation order (audit trail)';

-- ============================================================
-- STEP 3: Add createdBy to therapy
-- ============================================================
ALTER TABLE therapy
ADD COLUMN IF NOT EXISTS "createdBy" TEXT;

COMMENT ON COLUMN therapy."createdBy" IS 'Staff who created the therapy order (audit trail)';

-- ============================================================
-- STEP 4: Add createdBy to therapysessions
-- ============================================================
ALTER TABLE therapysessions
ADD COLUMN IF NOT EXISTS "createdBy" TEXT;

COMMENT ON COLUMN therapysessions."createdBy" IS 'Staff who created the session record (audit trail)';

-- ============================================================
-- STEP 5: Add createdBy to patient_alerts
-- ============================================================
ALTER TABLE patient_alerts
ADD COLUMN IF NOT EXISTS "createdBy" TEXT;

COMMENT ON COLUMN patient_alerts."createdBy" IS 'System/Watch that generated the alert (audit trail)';

-- ============================================================
-- STEP 6: Add editedBy to patientnotes
-- ============================================================
ALTER TABLE patientnotes
ADD COLUMN IF NOT EXISTS "editedBy" TEXT;

COMMENT ON COLUMN patientnotes."editedBy" IS 'Staff who last edited the note';

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================

-- Verify all columns were added
DO $$
DECLARE
    missing_columns TEXT[] := ARRAY[]::TEXT[];
BEGIN
    -- Check medicationadministrations.createdBy
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'medicationadministrations' AND column_name = 'createdBy'
    ) THEN
        missing_columns := array_append(missing_columns, 'medicationadministrations.createdBy');
    END IF;

    -- Check investigations.createdBy
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'investigations' AND column_name = 'createdBy'
    ) THEN
        missing_columns := array_append(missing_columns, 'investigations.createdBy');
    END IF;

    -- Check therapy.createdBy
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'therapy' AND column_name = 'createdBy'
    ) THEN
        missing_columns := array_append(missing_columns, 'therapy.createdBy');
    END IF;

    -- Check therapysessions.createdBy
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'therapysessions' AND column_name = 'createdBy'
    ) THEN
        missing_columns := array_append(missing_columns, 'therapysessions.createdBy');
    END IF;

    -- Check patient_alerts.createdBy
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'patient_alerts' AND column_name = 'createdBy'
    ) THEN
        missing_columns := array_append(missing_columns, 'patient_alerts.createdBy');
    END IF;

    -- Check patientnotes.editedBy
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'patientnotes' AND column_name = 'editedBy'
    ) THEN
        missing_columns := array_append(missing_columns, 'patientnotes.editedBy');
    END IF;

    -- Report results
    IF array_length(missing_columns, 1) > 0 THEN
        RAISE EXCEPTION 'Migration failed! Missing columns: %', array_to_string(missing_columns, ', ');
    ELSE
        RAISE NOTICE '✅ Migration 004 completed successfully! All 6 columns added.';
    END IF;
END $$;
