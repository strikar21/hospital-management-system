-- Migration to convert devices table from snake_case to camelCase
-- This will rename all snake_case columns to camelCase while preserving data

BEGIN;

-- Rename device_id to deviceId
ALTER TABLE devices RENAME COLUMN device_id TO "deviceId";

-- Rename device_type to deviceType  
ALTER TABLE devices RENAME COLUMN device_type TO "deviceType";

-- Rename mac_address to macAddress
ALTER TABLE devices RENAME COLUMN mac_address TO "macAddress";

-- Rename ip_address to ipAddress
ALTER TABLE devices RENAME COLUMN ip_address TO "ipAddress";

-- Rename firmware_version to firmwareVersion
ALTER TABLE devices RENAME COLUMN firmware_version TO "firmwareVersion";

-- Rename device_token to deviceToken
ALTER TABLE devices RENAME COLUMN device_token TO "deviceToken";

-- Rename api_key to apiKey
ALTER TABLE devices RENAME COLUMN api_key TO "apiKey";

-- Rename last_seen to lastSeen
ALTER TABLE devices RENAME COLUMN last_seen TO "lastSeen";

-- Rename last_heartbeat to lastHeartbeat
ALTER TABLE devices RENAME COLUMN last_heartbeat TO "lastHeartbeat";

-- Rename battery_level to batteryLevel
ALTER TABLE devices RENAME COLUMN battery_level TO "batteryLevel";

-- Rename signal_strength to signalStrength
ALTER TABLE devices RENAME COLUMN signal_strength TO "signalStrength";

-- Rename created_at to createdAt
ALTER TABLE devices RENAME COLUMN created_at TO "createdAt";

-- Rename updated_at to updatedAt
ALTER TABLE devices RENAME COLUMN updated_at TO "updatedAt";

-- Rename is_active to isActive
ALTER TABLE devices RENAME COLUMN is_active TO "isActive";

-- Rename assignment_status to assignmentStatus
ALTER TABLE devices RENAME COLUMN assignment_status TO "assignmentStatus";

-- Rename assigned_to to assignedTo
ALTER TABLE devices RENAME COLUMN assigned_to TO "assignedTo";

-- Rename assigned_at to assignedAt
ALTER TABLE devices RENAME COLUMN assigned_at TO "assignedAt";

COMMIT;