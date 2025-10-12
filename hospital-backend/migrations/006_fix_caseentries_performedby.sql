-- Migration 006: Fix caseEntries performedBy Field
-- Date: 2025-10-11
-- Purpose: Add performedBy column to caseEntries table and fix database function
-- Addresses: Frontend expects performedBy but table only has createdBy, causing NULL staff attribution

-- ============================================================
-- CRITICAL ISSUE SUMMARY
-- ============================================================
-- Problem 1: caseEntries table missing performedBy column (frontend requires it)
-- Problem 2: create_atomic_case_entry() function inserts into createdBy instead of performedBy
-- Problem 3: All 112 existing case entries show NULL for performedBy in frontend
-- Problem 4: Staff names not displaying in case sheet (performedByName resolution fails)

-- ============================================================
-- STEP 1: Add performedBy column to caseEntries table
-- ============================================================
DO $$
BEGIN
    -- Check if column already exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'caseEntries' AND column_name = 'performedBy'
    ) THEN
        ALTER TABLE "caseEntries" ADD COLUMN "performedBy" TEXT;
        RAISE NOTICE '✅ Added performedBy column to caseEntries table';
    ELSE
        RAISE NOTICE 'ℹ️  performedBy column already exists';
    END IF;
END $$;

COMMENT ON COLUMN "caseEntries"."performedBy" IS 'Medical staff who performed the action (matches frontend expectations)';

-- ============================================================
-- STEP 2: Populate performedBy from existing createdBy data
-- ============================================================
DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    -- Copy createdBy to performedBy for all existing records
    UPDATE "caseEntries"
    SET "performedBy" = "createdBy"
    WHERE "performedBy" IS NULL;

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE '✅ Populated performedBy for % existing case entries', updated_count;
END $$;

-- ============================================================
-- STEP 3: Update create_atomic_case_entry() database function
-- ============================================================
CREATE OR REPLACE FUNCTION public.create_atomic_case_entry(
    p_patient_id text,
    p_entry_type text,
    p_description text,
    p_performed_by text
)
RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
    entry_id UUID;
BEGIN
    -- Insert case entry with BOTH performedBy AND createdBy
    -- performedBy: Medical staff who performed the action (for frontend display)
    -- createdBy: Who created the database record (audit trail, same in our system)
    INSERT INTO "caseEntries" (
        "patientId",
        "entryType",
        description,
        "performedBy",    -- FIXED: Now populates performedBy (frontend requirement)
        "createdBy",      -- KEEP: Audit trail (database record creator)
        timestamp,
        "createdAt",
        "updatedAt"
    ) VALUES (
        p_patient_id,
        p_entry_type,
        p_description,
        p_performed_by,   -- Medical staff ID (matches frontend type definition)
        p_performed_by,   -- Same value for audit trail
        NOW(),
        NOW(),
        NOW()
    ) RETURNING id INTO entry_id;

    RETURN entry_id;
END;
$$;

COMMENT ON FUNCTION public.create_atomic_case_entry IS 'Creates case entry with proper performedBy field (fixed in migration 006)';

-- ============================================================
-- STEP 4: Verification checks
-- ============================================================
DO $$
DECLARE
    null_performed_count INTEGER;
    null_created_count INTEGER;
    total_count INTEGER;
    function_exists BOOLEAN;
BEGIN
    -- Check for NULL performedBy
    SELECT COUNT(*) INTO null_performed_count
    FROM "caseEntries"
    WHERE "performedBy" IS NULL;

    -- Check for NULL createdBy
    SELECT COUNT(*) INTO null_created_count
    FROM "caseEntries"
    WHERE "createdBy" IS NULL;

    -- Total entries
    SELECT COUNT(*) INTO total_count FROM "caseEntries";

    -- Check function exists
    SELECT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'create_atomic_case_entry'
    ) INTO function_exists;

    -- Report results
    RAISE NOTICE '=== MIGRATION 006 VERIFICATION ===';
    RAISE NOTICE 'Total case entries: %', total_count;
    RAISE NOTICE 'Entries with NULL performedBy: %', null_performed_count;
    RAISE NOTICE 'Entries with NULL createdBy: %', null_created_count;
    RAISE NOTICE 'Function create_atomic_case_entry exists: %', function_exists;

    -- Fail if any critical issues
    IF null_performed_count > 0 THEN
        RAISE EXCEPTION '❌ MIGRATION FAILED: % case entries still have NULL performedBy', null_performed_count;
    END IF;

    IF NOT function_exists THEN
        RAISE EXCEPTION '❌ MIGRATION FAILED: create_atomic_case_entry function missing';
    END IF;

    RAISE NOTICE '✅ Migration 006 completed successfully';
    RAISE NOTICE '   - performedBy column added and populated';
    RAISE NOTICE '   - Database function updated to use performedBy';
    RAISE NOTICE '   - All % case entries have performedBy populated', total_count;
END $$;

-- ============================================================
-- STEP 5: Create index for performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_caseentries_performedby
ON "caseEntries"("performedBy");

COMMENT ON INDEX idx_caseentries_performedby IS 'Index for case entries lookup by staff member';

-- ============================================================
-- MIGRATION NOTES
-- ============================================================
-- After this migration:
-- 1. Frontend will receive performedBy field (was NULL before)
-- 2. Staff names will display correctly in case sheet
-- 3. Both performedBy and createdBy exist for clarity:
--    - performedBy: Medical staff who performed the action
--    - createdBy: Who created the database record (audit)
-- 4. In current system, both have same value (immediate recording)
-- 5. Future-proof for scheduled entries where they might differ
