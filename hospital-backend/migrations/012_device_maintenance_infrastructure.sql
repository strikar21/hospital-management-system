-- Migration 012: Device Maintenance Infrastructure
-- Component 5: Device Maintenance Alerts
-- Purpose: Add tables and columns for device calibration, maintenance, health tracking

-- ============================================
-- TABLE 1: Device Calibration Tracking
-- ============================================
CREATE TABLE IF NOT EXISTS "deviceCalibration" (
    "calibrationId" SERIAL PRIMARY KEY,
    "deviceId" TEXT NOT NULL,
    "calibratedAt" TIMESTAMP NOT NULL DEFAULT NOW(),
    "calibratedBy" TEXT,  -- Staff ID who performed calibration
    "calibrationType" TEXT DEFAULT 'full',  -- 'full', 'sensor_specific', 'quick'
    "sensorType" TEXT,  -- 'heartRate', 'spo2', 'temperature', 'bloodPressure', 'all'
    notes TEXT,
    "expiresAt" TIMESTAMP,  -- calibratedAt + 30 days
    "createdAt" TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY ("deviceId") REFERENCES devices(id) ON DELETE CASCADE,
    FOREIGN KEY ("calibratedBy") REFERENCES staff(id) ON DELETE SET NULL
);

-- ============================================
-- TABLE 2: Device Maintenance History
-- ============================================
CREATE TABLE IF NOT EXISTS "deviceMaintenanceHistory" (
    "maintenanceId" SERIAL PRIMARY KEY,
    "deviceId" TEXT NOT NULL,
    "maintenanceType" TEXT NOT NULL,  -- 'calibration', 'repair', 'battery_replacement', 'firmware_update', 'cleaning', 'inspection'
    "performedAt" TIMESTAMP NOT NULL DEFAULT NOW(),
    "performedBy" TEXT,  -- Staff ID
    notes TEXT,
    "nextMaintenanceDue" TIMESTAMP,
    cost DECIMAL(10, 2),  -- Cost of maintenance (optional)
    "createdAt" TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY ("deviceId") REFERENCES devices(id) ON DELETE CASCADE,
    FOREIGN KEY ("performedBy") REFERENCES staff(id) ON DELETE SET NULL
);

-- ============================================
-- TABLE 3: Device Performance Baselines
-- ============================================
CREATE TABLE IF NOT EXISTS "deviceBaselines" (
    "baselineId" SERIAL PRIMARY KEY,
    "deviceId" TEXT NOT NULL UNIQUE,

    -- Battery baseline
    "batteryDrainRatePerHour" FLOAT,  -- % per hour at normal usage
    "batteryHealthPercentage" INT DEFAULT 100,  -- 0-100, degrades over time

    -- Sensor variance baselines (for drift detection)
    "heartRateMean" FLOAT,
    "heartRateStdDev" FLOAT,
    "spo2Mean" FLOAT,
    "spo2StdDev" FLOAT,
    "temperatureMean" FLOAT,
    "temperatureStdDev" FLOAT,
    "systolicBpMean" FLOAT,
    "systolicBpStdDev" FLOAT,
    "diastolicBpMean" FLOAT,
    "diastolicBpStdDev" FLOAT,

    -- Baseline metadata
    "baselineCalculatedAt" TIMESTAMP DEFAULT NOW(),
    "baselineUpdatedAt" TIMESTAMP DEFAULT NOW(),
    "sampleCount" INT DEFAULT 0,  -- Number of readings used for baseline
    "calculationPeriodDays" INT DEFAULT 7,  -- Days of data used

    FOREIGN KEY ("deviceId") REFERENCES devices(id) ON DELETE CASCADE
);

-- ============================================
-- EXTEND devices TABLE
-- ============================================

-- Add firmware version tracking
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'firmwareVersion'
    ) THEN
        ALTER TABLE devices ADD COLUMN "firmwareVersion" TEXT;
        RAISE NOTICE 'Added column firmwareVersion to devices table';
    ELSE
        RAISE NOTICE 'Column firmwareVersion already exists in devices table';
    END IF;
END $$;

-- Add calibration tracking
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'lastCalibrationDate'
    ) THEN
        ALTER TABLE devices ADD COLUMN "lastCalibrationDate" TIMESTAMP;
        RAISE NOTICE 'Added column lastCalibrationDate to devices table';
    ELSE
        RAISE NOTICE 'Column lastCalibrationDate already exists in devices table';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'calibrationDueDate'
    ) THEN
        ALTER TABLE devices ADD COLUMN "calibrationDueDate" TIMESTAMP;
        RAISE NOTICE 'Added column calibrationDueDate to devices table';
    ELSE
        RAISE NOTICE 'Column calibrationDueDate already exists in devices table';
    END IF;
END $$;

-- Add battery health tracking
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'batteryHealthPercentage'
    ) THEN
        ALTER TABLE devices ADD COLUMN "batteryHealthPercentage" INT DEFAULT 100;
        RAISE NOTICE 'Added column batteryHealthPercentage to devices table';
    ELSE
        RAISE NOTICE 'Column batteryHealthPercentage already exists in devices table';
    END IF;
END $$;

-- Add disconnect tracking
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'totalDisconnects'
    ) THEN
        ALTER TABLE devices ADD COLUMN "totalDisconnects" INT DEFAULT 0;
        RAISE NOTICE 'Added column totalDisconnects to devices table';
    ELSE
        RAISE NOTICE 'Column totalDisconnects already exists in devices table';
    END IF;
END $$;

-- Add command responsiveness tracking
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'lastCommandSentAt'
    ) THEN
        ALTER TABLE devices ADD COLUMN "lastCommandSentAt" TIMESTAMP;
        RAISE NOTICE 'Added column lastCommandSentAt to devices table';
    ELSE
        RAISE NOTICE 'Column lastCommandSentAt already exists in devices table';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'lastCommandAckAt'
    ) THEN
        ALTER TABLE devices ADD COLUMN "lastCommandAckAt" TIMESTAMP;
        RAISE NOTICE 'Added column lastCommandAckAt to devices table';
    ELSE
        RAISE NOTICE 'Column lastCommandAckAt already exists in devices table';
    END IF;
END $$;

-- ============================================
-- INDEXES for Performance
-- ============================================

-- Device Calibration indexes
CREATE INDEX IF NOT EXISTS "idx_devicecalibration_deviceid"
    ON "deviceCalibration"("deviceId");

CREATE INDEX IF NOT EXISTS "idx_devicecalibration_expiresat"
    ON "deviceCalibration"("expiresAt");

CREATE INDEX IF NOT EXISTS "idx_devicecalibration_calibratedby"
    ON "deviceCalibration"("calibratedBy");

-- Device Maintenance indexes
CREATE INDEX IF NOT EXISTS "idx_devicemaintenance_deviceid"
    ON "deviceMaintenanceHistory"("deviceId");

CREATE INDEX IF NOT EXISTS "idx_devicemaintenance_performedat"
    ON "deviceMaintenanceHistory"("performedAt");

CREATE INDEX IF NOT EXISTS "idx_devicemaintenance_nextdue"
    ON "deviceMaintenanceHistory"("nextMaintenanceDue");

-- Device Baselines indexes
CREATE INDEX IF NOT EXISTS "idx_devicebaselines_deviceid"
    ON "deviceBaselines"("deviceId");

-- Devices table new column indexes
CREATE INDEX IF NOT EXISTS "idx_devices_calibration_due"
    ON devices("calibrationDueDate");

CREATE INDEX IF NOT EXISTS "idx_devices_firmware"
    ON devices("firmwareVersion");

CREATE INDEX IF NOT EXISTS "idx_devices_last_calibration"
    ON devices("lastCalibrationDate");

-- ============================================
-- TRIGGERS for Auto-Update
-- ============================================

-- Auto-update deviceBaselines updatedAt timestamp
CREATE OR REPLACE FUNCTION "update_devicebaselines_timestamp"()
RETURNS TRIGGER AS $$
BEGIN
    NEW."baselineUpdatedAt" = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER "trigger_update_devicebaselines_timestamp"
    BEFORE UPDATE ON "deviceBaselines"
    FOR EACH ROW
    EXECUTE FUNCTION "update_devicebaselines_timestamp"();

-- ============================================
-- DATA INITIALIZATION (Optional)
-- ============================================

-- Set default calibration due dates for existing devices (30 days from now)
UPDATE devices
SET "calibrationDueDate" = NOW() + INTERVAL '30 days'
WHERE "calibrationDueDate" IS NULL;

-- Set default battery health for existing devices
UPDATE devices
SET "batteryHealthPercentage" = 100
WHERE "batteryHealthPercentage" IS NULL;

-- Set default firmware version for existing devices
UPDATE devices
SET "firmwareVersion" = '1.0.0'
WHERE "firmwareVersion" IS NULL;

-- ============================================
-- VERIFICATION QUERY
-- ============================================

-- Verify migration success
DO $$
DECLARE
    table_count INT;
    column_count INT;
    index_count INT;
BEGIN
    -- Count new tables
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_name IN ('deviceCalibration', 'deviceMaintenanceHistory', 'deviceBaselines');

    -- Count new columns in devices table
    SELECT COUNT(*) INTO column_count
    FROM information_schema.columns
    WHERE table_name = 'devices'
      AND column_name IN ('firmwareVersion', 'lastCalibrationDate', 'calibrationDueDate',
                          'batteryHealthPercentage', 'totalDisconnects',
                          'lastCommandSentAt', 'lastCommandAckAt');

    -- Count new indexes
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE tablename IN ('deviceCalibration', 'deviceMaintenanceHistory', 'deviceBaselines', 'devices')
      AND indexname LIKE 'idx_device%';

    RAISE NOTICE '=== Migration 012 Verification ===';
    RAISE NOTICE 'New tables created: %', table_count;
    RAISE NOTICE 'New columns added to devices: %', column_count;
    RAISE NOTICE 'New indexes created: %', index_count;

    IF table_count = 3 AND column_count = 7 THEN
        RAISE NOTICE 'SUCCESS: Migration 012 completed successfully!';
    ELSE
        RAISE WARNING 'PARTIAL: Migration may be incomplete (expected 3 tables, 7 columns)';
    END IF;
END $$;
