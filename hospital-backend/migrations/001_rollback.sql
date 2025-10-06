-- Rollback: Remove Foreign Keys from medications table
-- Date: 2025-10-05
-- Description: Rollback migration 001 - removes all FK constraints from medications

BEGIN;

-- Drop all foreign key constraints added in migration 001
ALTER TABLE medications DROP CONSTRAINT IF EXISTS fk_medications_patient;
ALTER TABLE medications DROP CONSTRAINT IF EXISTS fk_medications_prescriber;
ALTER TABLE medications DROP CONSTRAINT IF EXISTS fk_medications_creator;

COMMIT;

-- Verification:
-- SELECT constraint_name FROM information_schema.table_constraints WHERE table_name = 'medications' AND constraint_type = 'FOREIGN KEY';
