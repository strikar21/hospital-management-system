-- Migration 018: CSDS Alignment
-- Date: 2025-11-21
-- Purpose: Add missing CSDS fields to align with CSDS specification
-- Reference: STREAMLINED_EXECUTION_PLAN.md - Step 2

BEGIN;

-- ============================================================================
-- DEVICE DOMAIN - Add missing CSDS fields
-- ============================================================================

ALTER TABLE devices ADD COLUMN IF NOT EXISTS "hardwareSerial" TEXT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS "batterySOHPercent" FLOAT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS "signalStrengthDbm" INTEGER;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS "messageCounter" BIGINT DEFAULT 0;

-- Comments
COMMENT ON COLUMN devices."hardwareSerial" IS 'CSDS: Manufacturer serial number';
COMMENT ON COLUMN devices."batterySOHPercent" IS 'CSDS: Battery state of health 0-100%';
COMMENT ON COLUMN devices."signalStrengthDbm" IS 'CSDS: WiFi/BLE signal strength in dBm';
COMMENT ON COLUMN devices."messageCounter" IS 'CSDS: Monotonic counter for replay protection';

-- ============================================================================
-- ALERT DOMAIN - Add CSDS severity and escalation fields
-- ============================================================================

ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "alertSeverityLevel" TEXT;
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "escalationTargetRole" TEXT;
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "escalationChannel" TEXT;
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "riskReason" TEXT;

-- Standardize severity to L1/L2/L3
UPDATE patient_alerts SET "alertSeverityLevel" =
  CASE severity
    WHEN 'critical' THEN 'L3'
    WHEN 'high' THEN 'L2'
    WHEN 'medium' THEN 'L1'
    WHEN 'low' THEN 'L1'
    ELSE 'L1'
  END
WHERE "alertSeverityLevel" IS NULL;

-- Add constraints
ALTER TABLE patient_alerts ADD CONSTRAINT check_severity_level
  CHECK ("alertSeverityLevel" IN ('L1', 'L2', 'L3'));

ALTER TABLE patient_alerts ADD CONSTRAINT check_escalation_role
  CHECK ("escalationTargetRole" IN ('nurse', 'resident', 'consultant', 'biomed') OR "escalationTargetRole" IS NULL);

ALTER TABLE patient_alerts ADD CONSTRAINT check_escalation_channel
  CHECK ("escalationChannel" IN ('ui', 'telegram', 'sms', 'voice_call') OR "escalationChannel" IS NULL);

-- Comments
COMMENT ON COLUMN patient_alerts."alertSeverityLevel" IS 'CSDS: Alert severity L1/L2/L3';
COMMENT ON COLUMN patient_alerts."escalationTargetRole" IS 'CSDS: Primary escalation recipient';
COMMENT ON COLUMN patient_alerts."escalationChannel" IS 'CSDS: Delivery channel';
COMMENT ON COLUMN patient_alerts."riskReason" IS 'CSDS: Why alert was triggered';

-- ============================================================================
-- LOINC MAPPING - For FHIR R5 integration
-- ============================================================================

CREATE TABLE IF NOT EXISTS loinc_vital_mapping (
    "vitalType" TEXT PRIMARY KEY,
    "loincCode" TEXT NOT NULL,
    "loincDisplay" TEXT NOT NULL,
    "ucumUnit" TEXT NOT NULL,
    "ucumCode" TEXT NOT NULL,
    "snomedCode" TEXT,
    "referenceRangeLow" FLOAT,
    "referenceRangeHigh" FLOAT
);

-- Insert CSDS vitals mappings
INSERT INTO loinc_vital_mapping ("vitalType", "loincCode", "loincDisplay", "ucumUnit", "ucumCode", "referenceRangeLow", "referenceRangeHigh")
VALUES
    ('hr_bpm', '8867-4', 'Heart rate', 'beats/minute', '/min', 60, 100),
    ('spo2_percent', '59408-5', 'Oxygen saturation', '%', '%', 95, 100),
    ('respiration_rate_bpm', '9279-1', 'Respiratory rate', 'breaths/minute', '/min', 12, 20),
    ('skin_temp_c', '8310-5', 'Body temperature', 'Cel', 'Cel', 36.5, 37.5),
    ('ambient_temp_c', '8302-2', 'Ambient temperature', 'Cel', 'Cel', 20, 25),
    ('systolic_bp_mmhg', '8480-6', 'Systolic blood pressure', 'mmHg', 'mm[Hg]', 90, 120),
    ('diastolic_bp_mmhg', '8462-4', 'Diastolic blood pressure', 'mmHg', 'mm[Hg]', 60, 80)
ON CONFLICT ("vitalType") DO UPDATE SET
    "loincCode" = EXCLUDED."loincCode",
    "loincDisplay" = EXCLUDED."loincDisplay",
    "ucumUnit" = EXCLUDED."ucumUnit",
    "ucumCode" = EXCLUDED."ucumCode",
    "referenceRangeLow" = EXCLUDED."referenceRangeLow",
    "referenceRangeHigh" = EXCLUDED."referenceRangeHigh";

COMMENT ON TABLE loinc_vital_mapping IS 'CSDS: LOINC code mapping for FHIR R5 Observation resources';

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Show new device columns
SELECT column_name, data_type, col_description('devices'::regclass, ordinal_position)
FROM information_schema.columns
WHERE table_name = 'devices'
  AND column_name IN ('hardwareSerial', 'batterySOHPercent', 'signalStrengthDbm', 'messageCounter')
ORDER BY ordinal_position;

-- Show new alert columns
SELECT column_name, data_type, col_description('patient_alerts'::regclass, ordinal_position)
FROM information_schema.columns
WHERE table_name = 'patient_alerts'
  AND column_name IN ('alertSeverityLevel', 'escalationTargetRole', 'escalationChannel', 'riskReason')
ORDER BY ordinal_position;

-- Show LOINC mapping count
SELECT COUNT(*) as loinc_mappings FROM loinc_vital_mapping;
