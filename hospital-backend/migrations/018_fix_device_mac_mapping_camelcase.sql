-- Migration 018: Fix device_mac_mapping Table - snake_case to camelCase
-- Purpose: Rename all snake_case columns to camelCase for consistency
-- Date: 2025-10-23
-- Related: Migration 014 originally created table with snake_case

-- =====================================================
-- RENAME COLUMNS TO CAMELCASE
-- =====================================================

ALTER TABLE device_mac_mapping
    RENAME COLUMN mac_address TO "macAddress";

ALTER TABLE device_mac_mapping
    RENAME COLUMN device_id TO "deviceId";

ALTER TABLE device_mac_mapping
    RENAME COLUMN created_at TO "createdAt";

ALTER TABLE device_mac_mapping
    RENAME COLUMN updated_at TO "updatedAt";

-- =====================================================
-- RECREATE INDEXES WITH CAMELCASE COLUMN NAMES
-- =====================================================

-- Drop old index
DROP INDEX IF EXISTS idx_device_mac_mapping_device_id;

-- Recreate with camelCase column name
CREATE INDEX idx_device_mac_mapping_device_id
ON device_mac_mapping("deviceId");

-- =====================================================
-- UPDATE PRIMARY KEY CONSTRAINT (if needed)
-- =====================================================

-- The primary key is on macAddress column - PostgreSQL automatically updates this
-- No action needed as column rename automatically updates constraint

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
    WHERE table_name = 'device_mac_mapping'
    AND column_name IN ('macAddress', 'deviceId', 'createdAt', 'updatedAt');

    IF column_count = 4 THEN
        RAISE NOTICE '✅ All 4 columns successfully renamed to camelCase';
    ELSE
        RAISE WARNING '⚠️ Expected 4 camelCase columns, found %', column_count;
    END IF;
END $$;

-- Show final schema
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'device_mac_mapping'
ORDER BY ordinal_position;
