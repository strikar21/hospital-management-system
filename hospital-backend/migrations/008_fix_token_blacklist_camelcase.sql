-- Migration: Fix token_blacklist table to use camelCase column names
-- Date: 2025-11-14
-- Purpose: Standardize all column names to camelCase (snake_case → camelCase)

-- Rename snake_case columns to camelCase
ALTER TABLE token_blacklist
RENAME COLUMN blacklisted_at TO "blacklistedAt";

ALTER TABLE token_blacklist
RENAME COLUMN expires_at TO "expiresAt";

-- Verify the migration
SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'token_blacklist'
ORDER BY ordinal_position;
