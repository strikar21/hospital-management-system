-- Migration 007: Remove medicationadministrations.createdBy (redundant field)
-- Date: 2025-10-11
-- Reason: createdBy is redundant with performedBy in this table
-- Impact: Column removal, no data loss (field was redundant)

BEGIN;

-- Step 1: Safety check - verify createdBy = performedBy in all rows
DO $$
DECLARE
    different_count INTEGER;
    total_count INTEGER;
BEGIN
    -- Count rows where performedBy != createdBy
    SELECT COUNT(*) INTO different_count
    FROM medicationadministrations
    WHERE "performedBy" != "createdBy"
      AND "createdBy" IS NOT NULL
      AND "performedBy" IS NOT NULL;

    -- Count total rows with both fields populated
    SELECT COUNT(*) INTO total_count
    FROM medicationadministrations
    WHERE "createdBy" IS NOT NULL AND "performedBy" IS NOT NULL;

    RAISE NOTICE 'Safety check: Total rows with both fields: %, Different values: %', total_count, different_count;

    IF different_count > 0 THEN
        RAISE EXCEPTION 'ABORT: Found % records where performedBy != createdBy. Manual review required.', different_count;
    END IF;

    RAISE NOTICE 'Safety check PASSED: All createdBy values match performedBy';
END $$;

-- Step 2: Drop the redundant column
ALTER TABLE medicationadministrations DROP COLUMN IF EXISTS "createdBy";

-- Step 3: Verify column removed
DO $$
DECLARE
    column_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'medicationadministrations'
          AND column_name = 'createdBy'
    ) INTO column_exists;

    IF column_exists THEN
        RAISE EXCEPTION 'ERROR: Column createdBy still exists after DROP';
    ELSE
        RAISE NOTICE 'SUCCESS: Column createdBy removed from medicationadministrations';
    END IF;
END $$;

COMMIT;
