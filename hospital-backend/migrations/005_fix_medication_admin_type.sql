-- Migration 005: Fix medicationadministrations.medicationId Type Mismatch
-- Date: 2025-10-10
-- Purpose: Change medicationId from TEXT to INTEGER for proper foreign key constraint
-- Addresses: Schema type mismatch between medications.id (INTEGER) and medicationadministrations.medicationId (TEXT)

-- STEP 1: Check current data and identify any issues
DO $$
DECLARE
    invalid_count INTEGER;
BEGIN
    -- Count records with non-numeric medicationId
    SELECT COUNT(*) INTO invalid_count
    FROM medicationadministrations
    WHERE "medicationId" !~ '^[0-9]+$';

    IF invalid_count > 0 THEN
        RAISE WARNING 'Found % records with non-numeric medicationId values', invalid_count;
        RAISE NOTICE 'These records will need manual review before migration';
    ELSE
        RAISE NOTICE 'All medicationId values are numeric - safe to convert';
    END IF;
END $$;

-- STEP 2: Backup the current column (safety measure)
ALTER TABLE medicationadministrations
ADD COLUMN IF NOT EXISTS "medicationId_backup" TEXT;

UPDATE medicationadministrations
SET "medicationId_backup" = "medicationId"
WHERE "medicationId_backup" IS NULL;

COMMENT ON COLUMN medicationadministrations."medicationId_backup" IS 'Backup of TEXT medicationId before type conversion (migration 005)';

-- STEP 3: Convert medicationId from TEXT to INTEGER
-- This will fail if any values are not valid integers
ALTER TABLE medicationadministrations
ALTER COLUMN "medicationId" TYPE INTEGER USING "medicationId"::integer;

COMMENT ON COLUMN medicationadministrations."medicationId" IS 'Foreign key to medications.id (INTEGER) - fixed in migration 005';

-- STEP 4: Add foreign key constraint
ALTER TABLE medicationadministrations
ADD CONSTRAINT fk_medicationadmin_medication
FOREIGN KEY ("medicationId")
REFERENCES medications(id)
ON DELETE CASCADE;

COMMENT ON CONSTRAINT fk_medicationadmin_medication ON medicationadministrations IS 'Ensures medicationId references valid medication record';

-- STEP 5: Create index for performance
CREATE INDEX IF NOT EXISTS idx_medicationadmin_medication
ON medicationadministrations("medicationId");

COMMENT ON INDEX idx_medicationadmin_medication IS 'Index for medication administration lookups by medication';

-- STEP 6: Verification
DO $$
DECLARE
    constraint_exists BOOLEAN;
    column_type TEXT;
BEGIN
    -- Check if foreign key constraint was created
    SELECT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'medicationadministrations'
        AND constraint_name = 'fk_medicationadmin_medication'
        AND constraint_type = 'FOREIGN KEY'
    ) INTO constraint_exists;

    -- Check column type
    SELECT data_type INTO column_type
    FROM information_schema.columns
    WHERE table_name = 'medicationadministrations'
    AND column_name = 'medicationId';

    IF constraint_exists AND column_type = 'integer' THEN
        RAISE NOTICE '✅ Migration 005 completed successfully';
        RAISE NOTICE '   - medicationId type: %', column_type;
        RAISE NOTICE '   - Foreign key constraint: created';
        RAISE NOTICE '   - Backup column: medicationId_backup (TEXT)';
    ELSE
        RAISE WARNING '⚠️ Migration 005 may have issues:';
        RAISE WARNING '   - medicationId type: %', column_type;
        RAISE WARNING '   - Foreign key constraint exists: %', constraint_exists;
    END IF;
END $$;

-- STEP 7: Optional - Remove backup column after verification (commented out for safety)
-- Run this manually after confirming everything works:
-- ALTER TABLE medicationadministrations DROP COLUMN IF EXISTS "medicationId_backup";
