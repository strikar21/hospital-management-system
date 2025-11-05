-- Migration 019: Fix duration column type to support float values
-- Purpose: Change duration from INTEGER to DECIMAL to support 0.1 second (100ms) waveform packets
-- Date: 2025-11-03
-- Reason: ESP32 v5.2.5 sends 100ms packets (duration=0.1), but database expects INTEGER

BEGIN;

-- ============================================================================
-- PART 1: ALTER waveform_snapshots TABLE
-- ============================================================================

ALTER TABLE waveform_snapshots
    ALTER COLUMN duration TYPE DECIMAL(5,2);

COMMENT ON COLUMN waveform_snapshots.duration IS 'Duration of waveform snapshot in seconds (e.g., 0.1 for 100ms packets)';

-- ============================================================================
-- PART 2: ALTER vitals_realtime TABLE (if duration column exists)
-- ============================================================================

-- Check if duration column exists in vitals_realtime
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vitals_realtime' AND column_name = 'duration'
    ) THEN
        ALTER TABLE vitals_realtime
            ALTER COLUMN duration TYPE DECIMAL(5,2);

        COMMENT ON COLUMN vitals_realtime.duration IS 'Duration of waveform snapshot in seconds (e.g., 0.1 for 100ms packets)';

        RAISE NOTICE 'Updated vitals_realtime.duration column to DECIMAL(5,2)';
    ELSE
        RAISE NOTICE 'Column vitals_realtime.duration does not exist, skipping';
    END IF;
END $$;

-- ============================================================================
-- PART 3: ALTER neural_events TABLE
-- ============================================================================

ALTER TABLE neural_events
    ALTER COLUMN duration TYPE DECIMAL(5,2);

COMMENT ON COLUMN neural_events.duration IS 'Duration of event waveform in seconds (e.g., 0.1 for 100ms packets)';

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify column types
SELECT
    table_name,
    column_name,
    data_type,
    numeric_precision,
    numeric_scale
FROM information_schema.columns
WHERE table_name IN ('waveform_snapshots', 'vitals_realtime', 'neural_events')
  AND column_name = 'duration'
ORDER BY table_name;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '>> Migration 019 completed: duration columns changed to DECIMAL(5,2)';
    RAISE NOTICE '   - waveform_snapshots.duration: INTEGER → DECIMAL(5,2)';
    RAISE NOTICE '   - neural_events.duration: INTEGER → DECIMAL(5,2)';
    RAISE NOTICE '   - Now supports 0.1 second (100ms) waveform packets from ESP32 v5.2.5';
END
$$;
