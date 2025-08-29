-- Migration to convert device_assignments table from snake_case to camelCase

BEGIN;

-- Rename device_id to deviceId
ALTER TABLE device_assignments RENAME COLUMN device_id TO "deviceId";

-- Rename patient_id to patientId
ALTER TABLE device_assignments RENAME COLUMN patient_id TO "patientId";

-- Rename assigned_by to assignedBy
ALTER TABLE device_assignments RENAME COLUMN assigned_by TO "assignedBy";

-- Rename assignment_reason to assignmentReason
ALTER TABLE device_assignments RENAME COLUMN assignment_reason TO "assignmentReason";

-- Rename assigned_at to assignedAt
ALTER TABLE device_assignments RENAME COLUMN assigned_at TO "assignedAt";

-- Rename unassigned_at to unassignedAt
ALTER TABLE device_assignments RENAME COLUMN unassigned_at TO "unassignedAt";

-- Rename unassigned_by to unassignedBy
ALTER TABLE device_assignments RENAME COLUMN unassigned_by TO "unassignedBy";

-- Rename unassignment_reason to unassignmentReason
ALTER TABLE device_assignments RENAME COLUMN unassignment_reason TO "unassignmentReason";

-- Rename new_device_id to newDeviceId
ALTER TABLE device_assignments RENAME COLUMN new_device_id TO "newDeviceId";

-- Rename created_at to createdAt
ALTER TABLE device_assignments RENAME COLUMN created_at TO "createdAt";

-- Rename is_active to isActive
ALTER TABLE device_assignments RENAME COLUMN is_active TO "isActive";

COMMIT;