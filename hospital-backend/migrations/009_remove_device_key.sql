BEGIN;

-- Drop deviceKey constraint and column
ALTER TABLE devices DROP CONSTRAINT IF EXISTS devices_deviceKey_key;
ALTER TABLE devices DROP COLUMN IF EXISTS "deviceKey";

-- Add MAC index for performance
CREATE INDEX IF NOT EXISTS idx_devices_mac ON devices("macAddress");

-- Document change
COMMENT ON TABLE devices IS 'ESP32 devices use HMAC-SHA256 auth (deviceKey removed migration 009)';

COMMIT;
