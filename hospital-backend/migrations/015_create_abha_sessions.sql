-- Migration 015: Create ABHA Sessions Table
-- Purpose: Store ABHA auth tokens for pushing vitals to PHR app
-- Date: 2025-11-18

-- ============================================
-- ABHA Sessions Table
-- ============================================

CREATE TABLE IF NOT EXISTS abha_sessions (
    id SERIAL PRIMARY KEY,

    -- Patient linkage
    "patientId" TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,

    -- ABHA identifiers
    "abhaNumber" TEXT NOT NULL,  -- 14-digit ABHA number (stored without hyphens)
    "abhaAddress" TEXT,          -- username@abdm (e.g., rajesh.kumar@abdm)

    -- ABDM auth tokens
    "authToken" TEXT,            -- JWT token for ABDM API calls
    "refreshToken" TEXT,         -- Refresh token
    "tokenExpiresAt" TIMESTAMPTZ,  -- Token expiry time

    -- Session tracking
    "linkedAt" TIMESTAMPTZ DEFAULT NOW(),
    "lastPushAt" TIMESTAMPTZ,    -- Last time vitals were pushed to PHR
    "lastVerifiedAt" TIMESTAMPTZ,  -- Last OTP verification

    -- Session status
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expired', 'revoked', 'pending')),

    -- OTP verification tracking (for mock OTP)
    "otpTxnId" TEXT,             -- Transaction ID from ABDM (or mock)
    "otpSentAt" TIMESTAMPTZ,     -- When OTP was sent
    "otpVerifiedAt" TIMESTAMPTZ, -- When OTP was verified

    -- Metadata
    "createdAt" TIMESTAMPTZ DEFAULT NOW(),
    "updatedAt" TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_abha_sessions_patient ON abha_sessions("patientId");
CREATE INDEX IF NOT EXISTS idx_abha_sessions_abha_number ON abha_sessions("abhaNumber");
CREATE INDEX IF NOT EXISTS idx_abha_sessions_status ON abha_sessions(status);

-- Unique constraint: One active ABHA session per patient
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_abha_session
ON abha_sessions("patientId")
WHERE status = 'active';

-- ============================================
-- Comments
-- ============================================

COMMENT ON TABLE abha_sessions IS 'Stores ABHA authentication sessions for PHR data push';
COMMENT ON COLUMN abha_sessions."patientId" IS 'Reference to patients.id (MRN-based)';
COMMENT ON COLUMN abha_sessions."abhaNumber" IS '14-digit ABHA number without hyphens';
COMMENT ON COLUMN abha_sessions."abhaAddress" IS 'ABHA address (username@abdm)';
COMMENT ON COLUMN abha_sessions."authToken" IS 'JWT token from ABDM for API authentication';
COMMENT ON COLUMN abha_sessions."lastPushAt" IS 'Last successful vitals push to PHR app';
COMMENT ON COLUMN abha_sessions.status IS 'active=linked and valid, expired=token expired, revoked=manually unlinked, pending=OTP not verified';

-- ============================================
-- Sample Data for Testing (Mock ABHA)
-- ============================================

-- Add mock ABHA sessions for PAT0001 and PAT0002
INSERT INTO abha_sessions ("patientId", "abhaNumber", "abhaAddress", status, "linkedAt")
VALUES
    ('PAT0001', '12345678901234', 'rajesh.kumar@abdm', 'pending', NOW()),
    ('PAT0002', '12345678901235', 'priya.sharma@abdm', 'pending', NOW())
ON CONFLICT DO NOTHING;

COMMENT ON TABLE abha_sessions IS 'ABHA sessions for linking patients to ABDM PHR app';
