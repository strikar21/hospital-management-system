-- Migration 017: Fix device_certificates Table - snake_case to camelCase
-- Purpose: Rename all snake_case columns to camelCase for consistency
-- Date: 2025-10-23
-- Related: Migration 013 originally created table with snake_case

-- =====================================================
-- RENAME COLUMNS TO CAMELCASE
-- =====================================================

ALTER TABLE device_certificates
    RENAME COLUMN device_id TO "deviceId";

ALTER TABLE device_certificates
    RENAME COLUMN certificate_pem TO "certificatePem";

ALTER TABLE device_certificates
    RENAME COLUMN issued_at TO "issuedAt";

ALTER TABLE device_certificates
    RENAME COLUMN expires_at TO "expiresAt";

ALTER TABLE device_certificates
    RENAME COLUMN revoked_at TO "revokedAt";

ALTER TABLE device_certificates
    RENAME COLUMN revoked_by TO "revokedBy";

ALTER TABLE device_certificates
    RENAME COLUMN revocation_reason TO "revocationReason";

ALTER TABLE device_certificates
    RENAME COLUMN mac_address TO "macAddress";

ALTER TABLE device_certificates
    RENAME COLUMN serial_number TO "serialNumber";

-- =====================================================
-- RECREATE INDEXES WITH CAMELCASE COLUMN NAMES
-- =====================================================

-- Drop old indexes
DROP INDEX IF EXISTS idx_device_certificates_expiry;
DROP INDEX IF EXISTS idx_device_certificates_revoked;
DROP INDEX IF EXISTS idx_device_certificates_device;
DROP INDEX IF EXISTS idx_device_certificates_mac;

-- Recreate with camelCase column names
CREATE INDEX idx_device_certificates_expiry
ON device_certificates ("expiresAt")
WHERE revoked = false;

CREATE INDEX idx_device_certificates_revoked
ON device_certificates (revoked, "revokedAt")
WHERE revoked = true;

CREATE INDEX idx_device_certificates_device
ON device_certificates ("deviceId");

CREATE INDEX idx_device_certificates_mac
ON device_certificates ("macAddress");

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
    WHERE table_name = 'device_certificates'
    AND column_name IN ('deviceId', 'certificatePem', 'issuedAt', 'expiresAt', 'revokedAt',
                        'revokedBy', 'revocationReason', 'macAddress', 'serialNumber');

    IF column_count = 9 THEN
        RAISE NOTICE '✅ All 9 columns successfully renamed to camelCase';
    ELSE
        RAISE WARNING '⚠️ Expected 9 camelCase columns, found %', column_count;
    END IF;
END $$;

-- Show final schema
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'device_certificates'
ORDER BY ordinal_position;
