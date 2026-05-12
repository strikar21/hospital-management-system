-- Migration: Add Bootstrap Provisioning Tables
-- Description: Add support for automatic device provisioning with bootstrap authentication
-- Author: Claude
-- Date: 2025-05-12

-- ============================================================================
-- Table: device_serials
-- Purpose: Track auto-increment serial numbers for each device type
-- ============================================================================
CREATE TABLE IF NOT EXISTS device_serials (
    id SERIAL PRIMARY KEY,
    device_type VARCHAR(20) NOT NULL UNIQUE,
    last_sequence INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Initialize device serial counters
INSERT INTO device_serials (device_type, last_sequence) VALUES
    ('watch', 0),
    ('scanner', 0)
ON CONFLICT (device_type) DO NOTHING;

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_device_serials_type ON device_serials(device_type);

-- ============================================================================
-- Table: bootstrap_codes
-- Purpose: Store one-time provisioning codes for device bootstrap
-- ============================================================================
CREATE TABLE IF NOT EXISTS bootstrap_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(6) NOT NULL UNIQUE,
    device_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    used_by_device VARCHAR(50),  -- Serial number of device that used this code
    created_by_staff INTEGER REFERENCES staff(id) ON DELETE SET NULL,
    CONSTRAINT check_status CHECK (status IN ('active', 'used', 'expired'))
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_bootstrap_codes_code_status ON bootstrap_codes(code, status);
CREATE INDEX IF NOT EXISTS idx_bootstrap_codes_expires ON bootstrap_codes(expires_at);
CREATE INDEX IF NOT EXISTS idx_bootstrap_codes_device_type ON bootstrap_codes(device_type);
CREATE INDEX IF NOT EXISTS idx_bootstrap_codes_created_by ON bootstrap_codes(created_by_staff);

-- ============================================================================
-- Table: device_certificates
-- Purpose: Track X.509 certificates issued to devices for mTLS
-- ============================================================================
CREATE TABLE IF NOT EXISTS device_certificates (
    id SERIAL PRIMARY KEY,
    serial_number VARCHAR(20) NOT NULL,
    certificate_pem TEXT NOT NULL,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revocation_reason VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for certificate lifecycle queries
CREATE INDEX IF NOT EXISTS idx_device_certs_serial ON device_certificates(serial_number);
CREATE INDEX IF NOT EXISTS idx_device_certs_serial_active ON device_certificates(serial_number, revoked_at);
CREATE INDEX IF NOT EXISTS idx_device_certs_expires ON device_certificates(expires_at);

-- ============================================================================
-- Alter devices table: Add bootstrap provisioning fields
-- ============================================================================

-- Add UUID column (permanent device identifier)
ALTER TABLE devices ADD COLUMN IF NOT EXISTS uuid VARCHAR(50) UNIQUE;
CREATE INDEX IF NOT EXISTS idx_devices_uuid ON devices(uuid);

-- Add serial_number column (human-readable W00001, S00001)
ALTER TABLE devices ADD COLUMN IF NOT EXISTS serial_number VARCHAR(20) UNIQUE;
CREATE INDEX IF NOT EXISTS idx_devices_serial ON devices(serial_number);

-- Add bootstrap API key (factory credential per device type)
ALTER TABLE devices ADD COLUMN IF NOT EXISTS bootstrap_api_key VARCHAR(100);

-- Add provisioning timestamp
ALTER TABLE devices ADD COLUMN IF NOT EXISTS provisioned_at TIMESTAMP WITH TIME ZONE;

-- Add provisioning code used
ALTER TABLE devices ADD COLUMN IF NOT EXISTS provisioning_code VARCHAR(6);

-- Add MQTT authentication fields (defense in depth with mTLS)
ALTER TABLE devices ADD COLUMN IF NOT EXISTS mqtt_username VARCHAR(50);
ALTER TABLE devices ADD COLUMN IF NOT EXISTS mqtt_password_hash VARCHAR(100);

-- Add foreign key to current active certificate
ALTER TABLE devices ADD COLUMN IF NOT EXISTS certificate_serial INTEGER REFERENCES device_certificates(id) ON DELETE SET NULL;

-- ============================================================================
-- Add foreign key constraint for device_certificates
-- ============================================================================
ALTER TABLE device_certificates
    ADD CONSTRAINT fk_device_cert_serial
    FOREIGN KEY (serial_number)
    REFERENCES devices(serial_number)
    ON DELETE CASCADE
    ON UPDATE CASCADE;

-- ============================================================================
-- Create function to automatically expire old codes
-- ============================================================================
CREATE OR REPLACE FUNCTION expire_old_bootstrap_codes()
RETURNS void AS $$
BEGIN
    UPDATE bootstrap_codes
    SET status = 'expired'
    WHERE status = 'active'
      AND expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Create function to get next serial number (atomic operation)
-- ============================================================================
CREATE OR REPLACE FUNCTION get_next_serial_number(p_device_type VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    v_next_seq INTEGER;
    v_prefix VARCHAR(1);
    v_serial VARCHAR(20);
BEGIN
    -- Lock row for update
    SELECT last_sequence + 1 INTO v_next_seq
    FROM device_serials
    WHERE device_type = p_device_type
    FOR UPDATE;

    -- Update sequence
    UPDATE device_serials
    SET last_sequence = v_next_seq,
        updated_at = CURRENT_TIMESTAMP
    WHERE device_type = p_device_type;

    -- Determine prefix
    IF p_device_type = 'watch' THEN
        v_prefix := 'W';
    ELSIF p_device_type = 'scanner' THEN
        v_prefix := 'S';
    ELSE
        v_prefix := 'D';  -- Default for unknown types
    END IF;

    -- Format serial: W00001, S00001
    v_serial := v_prefix || LPAD(v_next_seq::TEXT, 5, '0');

    RETURN v_serial;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Audit trail: Create trigger for updated_at timestamps
-- ============================================================================

-- Function to update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for device_serials
DROP TRIGGER IF EXISTS update_device_serials_updated_at ON device_serials;
CREATE TRIGGER update_device_serials_updated_at
    BEFORE UPDATE ON device_serials
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for device_certificates
DROP TRIGGER IF EXISTS update_device_certificates_updated_at ON device_certificates;
CREATE TRIGGER update_device_certificates_updated_at
    BEFORE UPDATE ON device_certificates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Grant permissions (adjust as needed for your setup)
-- ============================================================================

-- Grant access to application user (replace 'hospital_app' with your app user)
-- GRANT SELECT, INSERT, UPDATE ON device_serials TO hospital_app;
-- GRANT SELECT, INSERT, UPDATE ON bootstrap_codes TO hospital_app;
-- GRANT SELECT, INSERT, UPDATE ON device_certificates TO hospital_app;
-- GRANT USAGE, SELECT ON SEQUENCE device_serials_id_seq TO hospital_app;
-- GRANT USAGE, SELECT ON SEQUENCE bootstrap_codes_id_seq TO hospital_app;
-- GRANT USAGE, SELECT ON SEQUENCE device_certificates_id_seq TO hospital_app;

-- ============================================================================
-- Insert sample provisioning codes for testing (REMOVE IN PRODUCTION)
-- ============================================================================

-- Generate 5 sample codes for watches (expires in 48 hours)
INSERT INTO bootstrap_codes (code, device_type, status, expires_at) VALUES
    ('123456', 'watch', 'active', CURRENT_TIMESTAMP + INTERVAL '48 hours'),
    ('234567', 'watch', 'active', CURRENT_TIMESTAMP + INTERVAL '48 hours'),
    ('345678', 'watch', 'active', CURRENT_TIMESTAMP + INTERVAL '48 hours'),
    ('456789', 'watch', 'active', CURRENT_TIMESTAMP + INTERVAL '48 hours'),
    ('567890', 'watch', 'active', CURRENT_TIMESTAMP + INTERVAL '48 hours');

-- Generate 2 sample codes for scanners
INSERT INTO bootstrap_codes (code, device_type, status, expires_at) VALUES
    ('111111', 'scanner', 'active', CURRENT_TIMESTAMP + INTERVAL '48 hours'),
    ('222222', 'scanner', 'active', CURRENT_TIMESTAMP + INTERVAL '48 hours');

-- ============================================================================
-- Verification queries
-- ============================================================================

-- Check device_serials table
-- SELECT * FROM device_serials ORDER BY device_type;

-- Check bootstrap_codes table
-- SELECT code, device_type, status, expires_at FROM bootstrap_codes WHERE status = 'active';

-- Check device_certificates table
-- SELECT serial_number, expires_at, revoked_at FROM device_certificates ORDER BY issued_at DESC LIMIT 10;

-- Check devices with new fields
-- SELECT serial_number, uuid, deviceType, provisioned_at, mqtt_username FROM devices WHERE serial_number IS NOT NULL;

-- ============================================================================
-- Rollback script (for development only)
-- ============================================================================

/*
-- WARNING: This will delete all provisioning data!

DROP TRIGGER IF EXISTS update_device_serials_updated_at ON device_serials;
DROP TRIGGER IF EXISTS update_device_certificates_updated_at ON device_certificates;
DROP FUNCTION IF EXISTS update_updated_at_column();
DROP FUNCTION IF EXISTS get_next_serial_number(VARCHAR);
DROP FUNCTION IF EXISTS expire_old_bootstrap_codes();

ALTER TABLE device_certificates DROP CONSTRAINT IF EXISTS fk_device_cert_serial;
ALTER TABLE devices DROP CONSTRAINT IF EXISTS devices_certificate_serial_fkey;

DROP TABLE IF EXISTS device_certificates CASCADE;
DROP TABLE IF EXISTS bootstrap_codes CASCADE;
DROP TABLE IF EXISTS device_serials CASCADE;

ALTER TABLE devices DROP COLUMN IF EXISTS certificate_serial;
ALTER TABLE devices DROP COLUMN IF EXISTS mqtt_password_hash;
ALTER TABLE devices DROP COLUMN IF EXISTS mqtt_username;
ALTER TABLE devices DROP COLUMN IF EXISTS provisioning_code;
ALTER TABLE devices DROP COLUMN IF EXISTS provisioned_at;
ALTER TABLE devices DROP COLUMN IF EXISTS bootstrap_api_key;
ALTER TABLE devices DROP COLUMN IF EXISTS serial_number;
ALTER TABLE devices DROP COLUMN IF EXISTS uuid;
*/
