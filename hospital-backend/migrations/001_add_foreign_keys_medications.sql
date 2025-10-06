-- Migration: Add Foreign Keys to medications table
-- Date: 2025-10-05
-- Description: Establish referential integrity for medication records

BEGIN;

-- 1. Add foreign key to patients table
-- CASCADE: If patient deleted, cascade delete their medications (maintains data consistency)
ALTER TABLE medications
ADD CONSTRAINT fk_medications_patient
FOREIGN KEY ("patientId") REFERENCES patients(id)
ON DELETE CASCADE;

-- 2. Add foreign key to staff table (prescriber)
-- RESTRICT: Cannot delete staff who prescribed medications (preserves audit trail)
ALTER TABLE medications
ADD CONSTRAINT fk_medications_prescriber
FOREIGN KEY ("prescribedBy") REFERENCES staff(id)
ON DELETE RESTRICT;

-- 3. Add foreign key to staff table (creator)
-- SET NULL: If creator deleted, set to NULL (allows staff cleanup while preserving record)
ALTER TABLE medications
ADD CONSTRAINT fk_medications_creator
FOREIGN KEY ("createdBy") REFERENCES staff(id)
ON DELETE SET NULL;

COMMIT;

-- Verification queries:
-- SELECT constraint_name, constraint_type FROM information_schema.table_constraints WHERE table_name = 'medications' AND constraint_type = 'FOREIGN KEY';
-- \d medications
