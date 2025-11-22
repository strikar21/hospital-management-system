-- ============================================
-- Migration 019: CSDS v2.0 Field Name Alignment
-- ============================================
-- Purpose: Align TimescaleDB vitals_realtime schema with CSDS v2.0 naming convention
-- from ESP32 watch firmware v5.2.14+
--
-- ESP32 Watch (CSDS v2.0):
--   hrBpm, spo2Percent, skinTempC, respirationRateBpm, batteryPercent,
--   systolicBpMmhg, diastolicBpMmhg
--
-- Legacy Backend (OLD):
--   heartRate, oxygenSaturation, skinTemperature, respiratoryRate, batteryLevel,
--   systolicPressure, diastolicPressure
--
-- This migration renames database columns to match CSDS v2.0 for seamless
-- watch-to-backend data flow.
-- ============================================

-- Rename basic vitals columns to CSDS v2.0
ALTER TABLE vitals_realtime
  RENAME COLUMN "heartRate" TO "hrBpm";

ALTER TABLE vitals_realtime
  RENAME COLUMN "oxygenSaturation" TO "spo2Percent";

ALTER TABLE vitals_realtime
  RENAME COLUMN "skinTemperature" TO "skinTempC";

ALTER TABLE vitals_realtime
  RENAME COLUMN "respiratoryRate" TO "respirationRateBpm";

ALTER TABLE vitals_realtime
  RENAME COLUMN "batteryLevel" TO "batteryPercent";

-- Rename blood pressure columns to CSDS v2.0
ALTER TABLE vitals_realtime
  RENAME COLUMN "systolicPressure" TO "systolicBpMmhg";

ALTER TABLE vitals_realtime
  RENAME COLUMN "diastolicPressure" TO "diastolicBpMmhg";

-- Add comments documenting CSDS v2.0 compliance
COMMENT ON COLUMN vitals_realtime."hrBpm"
  IS 'Heart rate in beats per minute (CSDS v2.0)';

COMMENT ON COLUMN vitals_realtime."spo2Percent"
  IS 'Oxygen saturation percentage (CSDS v2.0)';

COMMENT ON COLUMN vitals_realtime."skinTempC"
  IS 'Skin temperature in Celsius (CSDS v2.0)';

COMMENT ON COLUMN vitals_realtime."respirationRateBpm"
  IS 'Respiration rate in breaths per minute (CSDS v2.0)';

COMMENT ON COLUMN vitals_realtime."batteryPercent"
  IS 'Device battery level percentage (CSDS v2.0)';

COMMENT ON COLUMN vitals_realtime."systolicBpMmhg"
  IS 'Systolic blood pressure in mmHg (CSDS v2.0)';

COMMENT ON COLUMN vitals_realtime."diastolicBpMmhg"
  IS 'Diastolic blood pressure in mmHg (CSDS v2.0)';

-- Verify columns renamed successfully
DO $$
DECLARE
    column_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO column_count
    FROM information_schema.columns
    WHERE table_name = 'vitals_realtime'
      AND column_name IN ('hrBpm', 'spo2Percent', 'skinTempC', 'respirationRateBpm',
                          'batteryPercent', 'systolicBpMmhg', 'diastolicBpMmhg');

    IF column_count = 7 THEN
        RAISE NOTICE '✅ All 7 CSDS v2.0 columns renamed successfully';
    ELSE
        RAISE EXCEPTION '❌ Column rename verification failed: Expected 7, found %', column_count;
    END IF;
END $$;

-- Update vitals_timeseries table (if it exists and has same columns)
DO $$
BEGIN
    -- Check if vitals_timeseries exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vitals_timeseries') THEN
        -- Rename columns in vitals_timeseries
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'vitals_timeseries' AND column_name = 'heartRate') THEN
            ALTER TABLE vitals_timeseries RENAME COLUMN "heartRate" TO "hrBpm";
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'vitals_timeseries' AND column_name = 'oxygenSaturation') THEN
            ALTER TABLE vitals_timeseries RENAME COLUMN "oxygenSaturation" TO "spo2Percent";
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'vitals_timeseries' AND column_name = 'skinTemperature') THEN
            ALTER TABLE vitals_timeseries RENAME COLUMN "skinTemperature" TO "skinTempC";
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'vitals_timeseries' AND column_name = 'respiratoryRate') THEN
            ALTER TABLE vitals_timeseries RENAME COLUMN "respiratoryRate" TO "respirationRateBpm";
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'vitals_timeseries' AND column_name = 'batteryLevel') THEN
            ALTER TABLE vitals_timeseries RENAME COLUMN "batteryLevel" TO "batteryPercent";
        END IF;

        RAISE NOTICE '✅ vitals_timeseries columns updated to CSDS v2.0';
    ELSE
        RAISE NOTICE 'ℹ️  vitals_timeseries table does not exist, skipping';
    END IF;
END $$;

-- Final verification
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name IN ('vitals_realtime', 'vitals_timeseries')
  AND column_name IN ('hrBpm', 'spo2Percent', 'skinTempC', 'respirationRateBpm',
                      'batteryPercent', 'systolicBpMmhg', 'diastolicBpMmhg')
ORDER BY table_name, column_name;
