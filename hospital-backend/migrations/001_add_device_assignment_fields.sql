-- Migration: Add missing fields to deviceassignments table
-- Date: 2025-10-13
-- Issue: Code tries to update unassignedBy and unassignmentReason fields that don't exist
-- Phase: 0 - Fix Critical Schema Bug

BEGIN;

-- Add unassignedBy field to track who unassigned the device
ALTER TABLE deviceassignments ADD COLUMN IF NOT EXISTS "unassignedBy" TEXT;

-- Add unassignmentReason field to track why device was unassigned
ALTER TABLE deviceassignments ADD COLUMN IF NOT EXISTS "unassignmentReason" TEXT;

-- Verify columns were added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'deviceassignments'
  AND column_name IN ('unassignedBy', 'unassignmentReason')
ORDER BY column_name;

COMMIT;

-- Expected output:
-- column_name        | data_type | is_nullable
-- -------------------+-----------+------------
-- unassignedBy       | text      | YES
-- unassignmentReason | text      | YES
