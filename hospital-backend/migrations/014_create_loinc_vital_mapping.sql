-- Migration 014: Create LOINC Vital Mapping for NRCES FHIR R4 Compliance
-- Purpose: Map internal vital types to LOINC codes for ABDM/ABHA integration
--
-- NRCES Spec: https://nrces.in/ndhm/fhir/r4/StructureDefinition/ObservationVitalSigns
-- LOINC Database: https://loinc.org/

-- ========================================
-- LOINC VITAL MAPPING TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS loinc_vital_mapping (
    id SERIAL PRIMARY KEY,
    "vitalType" TEXT UNIQUE NOT NULL,  -- Internal vital name (camelCase)
    "loincCode" TEXT NOT NULL,         -- LOINC code (e.g., 8867-4)
    "loincDisplay" TEXT NOT NULL,      -- LOINC display name
    "ucumUnit" TEXT NOT NULL,          -- UCUM unit symbol
    "ucumCode" TEXT NOT NULL,          -- UCUM code for FHIR
    "snomedCode" TEXT,                 -- Optional SNOMED CT code
    "referenceRangeLow" NUMERIC,       -- Normal range lower bound
    "referenceRangeHigh" NUMERIC,      -- Normal range upper bound
    "createdAt" TIMESTAMPTZ DEFAULT NOW(),
    "updatedAt" TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_loinc_vital_type ON loinc_vital_mapping("vitalType");

-- ========================================
-- SEED LOINC CODES (NRCES APPROVED)
-- ========================================

-- 1. Heart Rate
INSERT INTO loinc_vital_mapping
("vitalType", "loincCode", "loincDisplay", "ucumUnit", "ucumCode", "snomedCode", "referenceRangeLow", "referenceRangeHigh")
VALUES
('heartRate', '8867-4', 'Heart rate', '/min', '/min', '364075005', 60, 100);

-- 2. Oxygen Saturation (SpO2)
INSERT INTO loinc_vital_mapping
("vitalType", "loincCode", "loincDisplay", "ucumUnit", "ucumCode", "snomedCode", "referenceRangeLow", "referenceRangeHigh")
VALUES
('oxygenSaturation', '59408-5', 'Oxygen saturation in Arterial blood by Pulse oximetry', '%', '%', '431314004', 95, 100);

-- 3. Body Temperature (Skin Temperature)
INSERT INTO loinc_vital_mapping
("vitalType", "loincCode", "loincDisplay", "ucumUnit", "ucumCode", "snomedCode", "referenceRangeLow", "referenceRangeHigh")
VALUES
('skinTemperature', '8310-5', 'Body temperature', 'Cel', 'Cel', '386725007', 36.1, 37.2);

-- 4. Systolic Blood Pressure
INSERT INTO loinc_vital_mapping
("vitalType", "loincCode", "loincDisplay", "ucumUnit", "ucumCode", "snomedCode", "referenceRangeLow", "referenceRangeHigh")
VALUES
('systolicPressure', '8480-6', 'Systolic blood pressure', 'mm[Hg]', 'mm[Hg]', '271649006', 90, 120);

-- 5. Diastolic Blood Pressure
INSERT INTO loinc_vital_mapping
("vitalType", "loincCode", "loincDisplay", "ucumUnit", "ucumCode", "snomedCode", "referenceRangeLow", "referenceRangeHigh")
VALUES
('diastolicPressure', '8462-4', 'Diastolic blood pressure', 'mm[Hg]', 'mm[Hg]', '271650006', 60, 80);

-- 6. Respiratory Rate
INSERT INTO loinc_vital_mapping
("vitalType", "loincCode", "loincDisplay", "ucumUnit", "ucumCode", "snomedCode", "referenceRangeLow", "referenceRangeHigh")
VALUES
('respiratoryRate', '9279-1', 'Respiratory rate', '/min', '/min', '86290005', 12, 20);

-- ========================================
-- ESP32 V5.2.13 NEW VITALS (Optional)
-- ========================================

-- 7. Perfusion Index
INSERT INTO loinc_vital_mapping
("vitalType", "loincCode", "loincDisplay", "ucumUnit", "ucumCode", "snomedCode", "referenceRangeLow", "referenceRangeHigh")
VALUES
('perfusionIndex', '61006-3', 'Perfusion index Tissue by Pulse oximetry', '%', '%', NULL, 0.5, 20.0);

-- 8. Step Count (Physical Activity)
INSERT INTO loinc_vital_mapping
("vitalType", "loincCode", "loincDisplay", "ucumUnit", "ucumCode", "snomedCode", "referenceRangeLow", "referenceRangeHigh")
VALUES
('stepCount', '41950-7', 'Number of steps in 24 hour Measured', '{steps}', '{steps}', NULL, 0, 20000);

-- ========================================
-- VERIFICATION QUERY
-- ========================================
SELECT
    "vitalType",
    "loincCode",
    "loincDisplay",
    "ucumUnit",
    "referenceRangeLow" || ' - ' || "referenceRangeHigh" AS "normalRange"
FROM loinc_vital_mapping
ORDER BY id;

-- Expected output:
--     vitalType      | loincCode |              loincDisplay               | ucumUnit | normalRange
-- -------------------+-----------+-----------------------------------------+----------+-------------
--  heartRate         | 8867-4    | Heart rate                              | /min     | 60 - 100
--  oxygenSaturation  | 59408-5   | Oxygen saturation...                    | %        | 95 - 100
--  skinTemperature   | 8310-5    | Body temperature                        | Cel      | 36.1 - 37.2
--  systolicPressure  | 8480-6    | Systolic blood pressure                 | mm[Hg]   | 90 - 120
--  diastolicPressure | 8462-4    | Diastolic blood pressure                | mm[Hg]   | 60 - 80
--  respiratoryRate   | 9279-1    | Respiratory rate                        | /min     | 12 - 20
--  perfusionIndex    | 61006-3   | Perfusion index Tissue by Pulse oximetry| %        | 0.5 - 20
--  stepCount         | 41950-7   | Number of steps in 24 hour Measured     | {steps}  | 0 - 20000
