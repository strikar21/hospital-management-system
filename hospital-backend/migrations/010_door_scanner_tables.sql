-- Migration 010: Door Scanner Tables
-- Date: 2025-11-14
-- Purpose: Add door scanner location tracking tables
-- Architecture: Modular design matching watch provisioning flow

BEGIN;

-- ============================================================================
-- TABLE 1: Door Scanners (Extended Device Info)
-- ============================================================================
-- Stores door scanner specific metadata (room assignment, location)
-- References devices table (id is door-00001, door-00002, etc.)

CREATE TABLE IF NOT EXISTS "doorScanners" (
    id TEXT PRIMARY KEY,
    "roomId" TEXT NOT NULL,
    "locationDescription" TEXT,
    ward TEXT,
    "isActive" BOOLEAN DEFAULT true,
    "lastScanTimestamp" TIMESTAMP,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    "updatedAt" TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_door_scanner_device FOREIGN KEY (id)
        REFERENCES devices(id) ON DELETE CASCADE
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_door_scanners_room
    ON "doorScanners"("roomId");
CREATE INDEX IF NOT EXISTS idx_door_scanners_ward
    ON "doorScanners"(ward);
CREATE INDEX IF NOT EXISTS idx_door_scanners_active
    ON "doorScanners"("isActive") WHERE "isActive" = true;

COMMENT ON TABLE "doorScanners" IS 'Door scanner specific metadata and room assignments';
COMMENT ON COLUMN "doorScanners".id IS 'Device ID (e.g., door-00001) - references devices table';
COMMENT ON COLUMN "doorScanners"."roomId" IS 'Room where scanner is installed (e.g., ICU-101)';
COMMENT ON COLUMN "doorScanners"."locationDescription" IS 'Human-readable location (e.g., ICU-101 Entrance)';


-- ============================================================================
-- TABLE 2: Scanner Readings (BLE Detection History)
-- ============================================================================
-- Historical record of all BLE device detections by door scanners
-- Used for analytics, audit trail, and debugging

CREATE TABLE IF NOT EXISTS "scannerReadings" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "scannerId" TEXT NOT NULL,
    "roomId" TEXT NOT NULL,
    "deviceId" TEXT NOT NULL,
    "deviceAddress" TEXT,
    "deviceName" TEXT,
    "deviceType" TEXT,
    rssi INTEGER,
    "scanTimestamp" TIMESTAMP NOT NULL,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_scanner_readings_scanner FOREIGN KEY ("scannerId")
        REFERENCES "doorScanners"(id) ON DELETE CASCADE
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_scanner_readings_scanner
    ON "scannerReadings"("scannerId", "scanTimestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_scanner_readings_device
    ON "scannerReadings"("deviceId", "scanTimestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_scanner_readings_room
    ON "scannerReadings"("roomId", "scanTimestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_scanner_readings_timestamp
    ON "scannerReadings"("scanTimestamp" DESC);

COMMENT ON TABLE "scannerReadings" IS 'Historical BLE device detection records from door scanners';
COMMENT ON COLUMN "scannerReadings"."scannerId" IS 'Door scanner that detected the device';
COMMENT ON COLUMN "scannerReadings".rssi IS 'Received Signal Strength Indicator (dBm)';


-- ============================================================================
-- TABLE 3: Device Locations (Real-time Tracking)
-- ============================================================================
-- Current real-time location of each device (watches, tablets, etc.)
-- One row per device, updated as device moves between rooms

CREATE TABLE IF NOT EXISTS "deviceLocations" (
    "deviceId" TEXT PRIMARY KEY,
    "currentRoom" TEXT,
    "currentScanner" TEXT,
    "lastSeen" TIMESTAMP NOT NULL,
    rssi INTEGER,
    "previousRoom" TEXT,
    "roomChangedAt" TIMESTAMP,
    "updatedAt" TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_device_locations_scanner FOREIGN KEY ("currentScanner")
        REFERENCES "doorScanners"(id) ON DELETE SET NULL
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_device_locations_room
    ON "deviceLocations"("currentRoom");
CREATE INDEX IF NOT EXISTS idx_device_locations_lastseen
    ON "deviceLocations"("lastSeen" DESC);
CREATE INDEX IF NOT EXISTS idx_device_locations_scanner
    ON "deviceLocations"("currentScanner");

COMMENT ON TABLE "deviceLocations" IS 'Real-time location tracking for all devices';
COMMENT ON COLUMN "deviceLocations"."currentRoom" IS 'Room where device is currently located';
COMMENT ON COLUMN "deviceLocations"."lastSeen" IS 'Timestamp of last BLE detection';
COMMENT ON COLUMN "deviceLocations"."previousRoom" IS 'Previous room (for movement tracking)';


-- ============================================================================
-- TABLE 4: Room Presence History (Analytics)
-- ============================================================================
-- Tracks device movement history (room entry/exit events)
-- Used for analytics, billing, compliance, and patient tracking

CREATE TABLE IF NOT EXISTS "roomPresenceHistory" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "deviceId" TEXT NOT NULL,
    "roomId" TEXT NOT NULL,
    "enteredAt" TIMESTAMP NOT NULL,
    "exitedAt" TIMESTAMP,
    duration INTERVAL GENERATED ALWAYS AS ("exitedAt" - "enteredAt") STORED,
    "enteredViaScanner" TEXT,
    "exitedViaScanner" TEXT,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_presence_device FOREIGN KEY ("deviceId")
        REFERENCES devices(id) ON DELETE CASCADE,
    CONSTRAINT fk_presence_entered_scanner FOREIGN KEY ("enteredViaScanner")
        REFERENCES "doorScanners"(id) ON DELETE SET NULL,
    CONSTRAINT fk_presence_exited_scanner FOREIGN KEY ("exitedViaScanner")
        REFERENCES "doorScanners"(id) ON DELETE SET NULL
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_presence_device
    ON "roomPresenceHistory"("deviceId", "enteredAt" DESC);
CREATE INDEX IF NOT EXISTS idx_presence_room
    ON "roomPresenceHistory"("roomId", "enteredAt" DESC);
CREATE INDEX IF NOT EXISTS idx_presence_active
    ON "roomPresenceHistory"("deviceId")
    WHERE "exitedAt" IS NULL;
CREATE INDEX IF NOT EXISTS idx_presence_duration
    ON "roomPresenceHistory"("roomId", duration DESC);

COMMENT ON TABLE "roomPresenceHistory" IS 'Historical record of device room presence (entry/exit events)';
COMMENT ON COLUMN "roomPresenceHistory".duration IS 'Auto-calculated duration in room (exitedAt - enteredAt)';
COMMENT ON COLUMN "roomPresenceHistory"."exitedAt" IS 'NULL if device still in room';


-- ============================================================================
-- VERIFICATION QUERY
-- ============================================================================
-- Verify all tables were created successfully

DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('doorScanners', 'scannerReadings', 'deviceLocations', 'roomPresenceHistory');

    IF table_count = 4 THEN
        RAISE NOTICE '✅ All 4 door scanner tables created successfully';
    ELSE
        RAISE EXCEPTION '❌ Expected 4 tables, found %', table_count;
    END IF;
END $$;

COMMIT;

-- Display table info
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
AND table_name IN ('doorScanners', 'scannerReadings', 'deviceLocations', 'roomPresenceHistory')
ORDER BY table_name;
