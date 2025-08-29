-- Migration to convert TimescaleDB tables from snake_case to camelCase

BEGIN;

-- Fix vital_readings table
ALTER TABLE vital_readings RENAME COLUMN device_id TO "deviceId";
ALTER TABLE vital_readings RENAME COLUMN patient_id TO "patientId";
ALTER TABLE vital_readings RENAME COLUMN vital_type TO "vitalType";
ALTER TABLE vital_readings RENAME COLUMN quality_indicator TO "qualityIndicator";

-- Fix device_alerts_ts table
ALTER TABLE device_alerts_ts RENAME COLUMN device_id TO "deviceId";
ALTER TABLE device_alerts_ts RENAME COLUMN patient_id TO "patientId";
ALTER TABLE device_alerts_ts RENAME COLUMN alert_type TO "alertType";
ALTER TABLE device_alerts_ts RENAME COLUMN resolved_at TO "resolvedAt";

COMMIT;