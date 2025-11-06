-- Migration 021: Add sensor vitals (tremor, bioimpedance, fall risk, etc.)
-- Date: 2025-11-06
-- Purpose: Complete sensor integration - BMI323, MAX86178, STS40, ADS1298

-- Add new columns from sensor simulators
ALTER TABLE vitals_realtime
ADD COLUMN IF NOT EXISTS tremor NUMERIC(4,2),
ADD COLUMN IF NOT EXISTS bioimpedance NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS "imuFallRisk" NUMERIC(4,2),
ADD COLUMN IF NOT EXISTS "perfusionIndex" NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS "stepCount" INTEGER,
ADD COLUMN IF NOT EXISTS "watchWorn" BOOLEAN,
ADD COLUMN IF NOT EXISTS "lastMovementTime" INTEGER;

-- Add constraints
ALTER TABLE vitals_realtime
ADD CONSTRAINT vitals_tremor_range CHECK (tremor BETWEEN 0.0 AND 10.0),
ADD CONSTRAINT vitals_bioimpedance_range CHECK (bioimpedance BETWEEN 20.0 AND 50.0),
ADD CONSTRAINT vitals_imu_fall_risk_range CHECK ("imuFallRisk" BETWEEN 0.0 AND 10.0),
ADD CONSTRAINT vitals_perfusion_index_range CHECK ("perfusionIndex" BETWEEN 0.0 AND 20.0);

-- Add indexes for critical values
CREATE INDEX IF NOT EXISTS idx_vitals_tremor
ON vitals_realtime ("patientId", tremor)
WHERE tremor > 5.0;

CREATE INDEX IF NOT EXISTS idx_vitals_fall_risk
ON vitals_realtime ("patientId", "imuFallRisk")
WHERE "imuFallRisk" > 7.0;

CREATE INDEX IF NOT EXISTS idx_vitals_perfusion
ON vitals_realtime ("patientId", "perfusionIndex")
WHERE "perfusionIndex" < 0.5;

CREATE INDEX IF NOT EXISTS idx_vitals_watch_off
ON vitals_realtime ("patientId", "watchWorn", time)
WHERE "watchWorn" = false;

-- Add comment
COMMENT ON COLUMN vitals_realtime.tremor IS 'Tremor intensity 0-10 from BMI323 IMU sensor';
COMMENT ON COLUMN vitals_realtime.bioimpedance IS 'Thoracic bioimpedance 20-50 Ohms from MAX86178 PPG sensor';
COMMENT ON COLUMN vitals_realtime."imuFallRisk" IS 'Fall risk 0-10 from BMI323 IMU sensor (state machine)';
COMMENT ON COLUMN vitals_realtime."perfusionIndex" IS 'Perfusion index 0-20% from MAX86178 PPG sensor (<0.5% = sepsis)';
COMMENT ON COLUMN vitals_realtime."stepCount" IS 'Step counter from BMI323 IMU pedometer';
COMMENT ON COLUMN vitals_realtime."watchWorn" IS 'Watch worn status from MAX86178 proximity detection';
COMMENT ON COLUMN vitals_realtime."lastMovementTime" IS 'Milliseconds since last movement from BMI323 (bedsore prevention)';
