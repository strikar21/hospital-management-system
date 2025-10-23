-- Migration 014: Device MAC Mapping Table
-- Purpose: Map MAC addresses to assigned device IDs for sequential naming
-- Date: 2025-10-20
-- Related: Proper fix for device ID naming (fit-00001, door-00001)

-- =====================================================
-- Create device_mac_mapping table
-- =====================================================

CREATE TABLE IF NOT EXISTS device_mac_mapping (
    mac_address TEXT PRIMARY KEY,
    device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE device_mac_mapping IS 'Maps device MAC addresses to assigned sequential device IDs';
COMMENT ON COLUMN device_mac_mapping.mac_address IS 'Device MAC address (format: A0:A3:B3:AA:13:B0)';
COMMENT ON COLUMN device_mac_mapping.device_id IS 'Assigned device ID (format: fit-00001, door-00001)';

-- =====================================================
-- Indexes
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_device_mac_mapping_device_id
ON device_mac_mapping(device_id);

-- =====================================================
-- Migrate existing data
-- =====================================================

-- Find devices with ESP32-WATCH-* pattern and create mappings
-- Extract MAC from device ID and create mapping
DO $$
DECLARE
    device_record RECORD;
    mac_part TEXT;
BEGIN
    FOR device_record IN
        SELECT id FROM devices WHERE id LIKE 'ESP32-WATCH-%'
    LOOP
        -- Extract MAC from "ESP32-WATCH-A0A3B3AA13B0" → "A0:A3:B3:AA:13:B0"
        mac_part := SUBSTRING(device_record.id FROM 12);

        -- Add colons back: "A0A3B3AA13B0" → "A0:A3:B3:AA:13:B0"
        IF LENGTH(mac_part) = 12 THEN
            mac_part := SUBSTRING(mac_part FROM 1 FOR 2) || ':' ||
                       SUBSTRING(mac_part FROM 3 FOR 2) || ':' ||
                       SUBSTRING(mac_part FROM 5 FOR 2) || ':' ||
                       SUBSTRING(mac_part FROM 7 FOR 2) || ':' ||
                       SUBSTRING(mac_part FROM 9 FOR 2) || ':' ||
                       SUBSTRING(mac_part FROM 11 FOR 2);

            -- Insert mapping
            INSERT INTO device_mac_mapping (mac_address, device_id)
            VALUES (mac_part, device_record.id)
            ON CONFLICT (mac_address) DO NOTHING;

            RAISE NOTICE 'Created mapping: % → %', mac_part, device_record.id;
        END IF;
    END LOOP;
END $$;

-- =====================================================
-- Verification
-- =====================================================

SELECT COUNT(*) as total_mappings FROM device_mac_mapping;
