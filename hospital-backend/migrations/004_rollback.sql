-- Rollback Migration 004: Remove audit trail fields
-- Date: 2025-10-06
-- WARNING: This will delete audit trail data

-- Remove createdBy from medicationadministrations
ALTER TABLE medicationadministrations
DROP COLUMN IF EXISTS "createdBy";

-- Remove createdBy from investigations
ALTER TABLE investigations
DROP COLUMN IF EXISTS "createdBy";

-- Remove createdBy from therapy
ALTER TABLE therapy
DROP COLUMN IF EXISTS "createdBy";

-- Remove createdBy from therapysessions
ALTER TABLE therapysessions
DROP COLUMN IF EXISTS "createdBy";

-- Remove createdBy from patient_alerts
ALTER TABLE patient_alerts
DROP COLUMN IF EXISTS "createdBy";

-- Remove editedBy from patientnotes
ALTER TABLE patientnotes
DROP COLUMN IF EXISTS "editedBy";

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 004 rolled back successfully';
END $$;
