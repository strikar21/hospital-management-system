-- Migration 013: Certificate Provisioning Infrastructure
-- Description: Add tables for device certificate management and provisioning codes
-- Author: Hospital IT Team
-- Date: 2025-10-17

-- Table 1: Provisioning Codes
-- Stores one-time codes for secure device provisioning
CREATE TABLE IF NOT EXISTS provisioning_codes (
    code VARCHAR(20) PRIMARY KEY,
    technician_id VARCHAR(50) NOT NULL REFERENCES staff(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT false,
    used_at TIMESTAMPTZ,
    device_id VARCHAR(50) REFERENCES devices(id)
);

-- Index for finding active (unused, unexpired) codes
CREATE INDEX IF NOT EXISTS idx_provisioning_codes_active
ON provisioning_codes (used, expires_at)
WHERE used = false;

-- Index for technician lookup (audit trail)
CREATE INDEX IF NOT EXISTS idx_provisioning_codes_technician
ON provisioning_codes (technician_id);

-- Table 2: Device Certificates
-- Stores X.509 certificate metadata for each device
CREATE TABLE IF NOT EXISTS device_certificates (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL REFERENCES devices(id) UNIQUE,
    certificate_pem TEXT NOT NULL,
    issued_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN DEFAULT false,
    revoked_at TIMESTAMPTZ,
    revoked_by VARCHAR(50) REFERENCES staff(id),
    revocation_reason TEXT,
    mac_address VARCHAR(17) NOT NULL,
    serial_number VARCHAR(50)
);

-- Index for finding certificates expiring soon
CREATE INDEX IF NOT EXISTS idx_device_certificates_expiry
ON device_certificates (expires_at)
WHERE revoked = false;

-- Index for revoked certificates (security audit)
CREATE INDEX IF NOT EXISTS idx_device_certificates_revoked
ON device_certificates (revoked, revoked_at)
WHERE revoked = true;

-- Index for device lookup (most common query)
CREATE INDEX IF NOT EXISTS idx_device_certificates_device
ON device_certificates (device_id);

-- Index for MAC address lookup (provisioning validation)
CREATE INDEX IF NOT EXISTS idx_device_certificates_mac
ON device_certificates (mac_address);

-- Comments for documentation
COMMENT ON TABLE provisioning_codes IS 'Stores one-time codes (10 min validity) for secure device provisioning';
COMMENT ON COLUMN provisioning_codes.code IS 'Random 16-character alphanumeric code';
COMMENT ON COLUMN provisioning_codes.expires_at IS 'Code expires 10 minutes after creation';
COMMENT ON COLUMN provisioning_codes.used IS 'True if code has been used for provisioning';

COMMENT ON TABLE device_certificates IS 'Stores X.509 certificate metadata for mTLS authentication';
COMMENT ON COLUMN device_certificates.certificate_pem IS 'PEM-encoded X.509 certificate (public key)';
COMMENT ON COLUMN device_certificates.expires_at IS 'Certificate expiration (default: 1 year)';
COMMENT ON COLUMN device_certificates.revoked IS 'True if certificate has been revoked (stolen/compromised device)';
