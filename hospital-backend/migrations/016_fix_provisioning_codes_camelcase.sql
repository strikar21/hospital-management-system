-- Migration 016: Fix provisioning_codes Table - snake_case to camelCase
-- Purpose: Rename all snake_case columns to camelCase for consistency
-- Date: 2025-10-23
-- Related: Migration 013 originally created table with snake_case

-- =====================================================
-- RENAME COLUMNS TO CAMELCASE
-- =====================================================

ALTER TABLE provisioning_codes
    RENAME COLUMN technician_id TO "technicianId";

ALTER TABLE provisioning_codes
    RENAME COLUMN created_at TO "createdAt";

ALTER TABLE provisioning_codes
    RENAME COLUMN expires_at TO "expiresAt";

ALTER TABLE provisioning_codes
    RENAME COLUMN used_at TO "usedAt";

ALTER TABLE provisioning_codes
    RENAME COLUMN device_id TO "deviceId";

-- =====================================================
-- RECREATE INDEXES WITH CAMELCASE COLUMN NAMES
-- =====================================================

-- Drop old indexes
DROP INDEX IF EXISTS idx_provisioning_codes_active;
DROP INDEX IF EXISTS idx_provisioning_codes_technician;

-- Recreate with camelCase column names
CREATE INDEX idx_provisioning_codes_active
ON provisioning_codes (used, "expiresAt")
WHERE used = false;

CREATE INDEX idx_provisioning_codes_technician
ON provisioning_codes ("technicianId");

-- =====================================================
-- VERIFICATION
-- =====================================================

-- Verify column names
DO $$
DECLARE
    column_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO column_count
    FROM information_schema.columns
    WHERE table_name = 'provisioning_codes'
    AND column_name IN ('technicianId', 'createdAt', 'expiresAt', 'usedAt', 'deviceId');

    IF column_count = 5 THEN
        RAISE NOTICE '✅ All 5 columns successfully renamed to camelCase';
    ELSE
        RAISE WARNING '⚠️ Expected 5 camelCase columns, found %', column_count;
    END IF;
END $$;

-- Show final schema
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'provisioning_codes'
ORDER BY ordinal_position;
