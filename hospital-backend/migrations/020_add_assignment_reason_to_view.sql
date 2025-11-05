-- Migration 020: Add assignmentReason to devices_enriched view
-- Purpose: Include assignment reason in enriched device view for complete data
-- Date: 2025-10-27

BEGIN;

-- Drop and recreate the devices_enriched view with assignmentReason field
DROP VIEW IF EXISTS devices_enriched CASCADE;

CREATE VIEW devices_enriched AS
SELECT
    -- All device fields
    d.id,
    d."deviceType",
    d.name,
    d."serialNumber",
    d."macAddress",
    d."firmwareVersion",
    d.status,
    d.location,
    d.description,
    d."batteryLevel",
    d."lastSeen",
    d."calibrationDate",
    d."nextMaintenanceDate",
    d."createdAt",
    d."updatedAt",
    d.model,
    d.manufacturer,

    -- Current assignment info (if assigned)
    da.id as "assignmentId",
    da."patientId" as "assignedPatientId",
    da."assignedBy",
    da."assignedAt",
    da."unassignedBy",
    da."unassignedAt",
    da."unassignmentReason",
    da.status as "assignmentStatus",
    da."assignmentReason",  -- ✅ ADDED: Assignment reason for frontend display

    -- Patient info (if assigned)
    p."firstName" as "patientFirstName",
    p."lastName" as "patientLastName",
    p."roomNumber",
    p."bedNumber",
    CONCAT(p."firstName", ' ', p."lastName") as "patientName",
    CONCAT('Room ', p."roomNumber", ', Bed ', p."bedNumber") as "patientLocation",

    -- Computed connection status (based on lastSeen timestamp)
    CASE
        WHEN d."lastSeen" IS NULL THEN 'offline'
        WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
        WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
        ELSE 'offline'
    END as "connectionStatus",

    -- Computed battery status
    CASE
        WHEN d."batteryLevel" IS NULL THEN 'unknown'
        WHEN d."batteryLevel" >= 80 THEN 'excellent'
        WHEN d."batteryLevel" >= 60 THEN 'good'
        WHEN d."batteryLevel" >= 40 THEN 'fair'
        WHEN d."batteryLevel" >= 20 THEN 'low'
        ELSE 'critical'
    END as "batteryStatus",

    -- Minutes since last seen (useful for alerting)
    CASE
        WHEN d."lastSeen" IS NULL THEN NULL
        ELSE EXTRACT(EPOCH FROM (NOW() - d."lastSeen")) / 60
    END as "minutesSinceLastSeen"

FROM devices d
LEFT JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
LEFT JOIN patients p ON da."patientId" = p.id;

-- Add comment to view
COMMENT ON VIEW devices_enriched IS 'Unified view of devices with current assignments and computed fields. Includes assignmentReason for complete assignment history. Single source of truth for device queries.';

COMMIT;

-- Verification queries
SELECT 'Migration 020 completed successfully' as status;

-- Verify assignmentReason field is included
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'devices_enriched' AND column_name = 'assignmentReason';

-- Show sample data with assignmentReason
SELECT id, name, "assignmentStatus", "assignmentReason", "patientName"
FROM devices_enriched
WHERE "assignmentStatus" = 'active'
LIMIT 5;
