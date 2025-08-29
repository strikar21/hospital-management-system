-- Database Schema Conversion to camelCase
-- This script converts all snake_case column names to camelCase

-- ===================================
-- PATIENT_MEDICATIONS TABLE
-- ===================================
ALTER TABLE patient_medications 
RENAME COLUMN prescribed_by TO prescribedBy;

ALTER TABLE patient_medications 
RENAME COLUMN prescribed_at TO prescribedAt;

ALTER TABLE patient_medications 
RENAME COLUMN start_date TO startDate;

ALTER TABLE patient_medications 
RENAME COLUMN end_date TO endDate;

ALTER TABLE patient_medications 
RENAME COLUMN modified_by TO modifiedBy;

ALTER TABLE patient_medications 
RENAME COLUMN modified_at TO modifiedAt;

ALTER TABLE patient_medications 
RENAME COLUMN can_edit TO canEdit;

ALTER TABLE patient_medications 
RENAME COLUMN created_at TO createdAt;

ALTER TABLE patient_medications 
RENAME COLUMN updated_at TO updatedAt;

-- ===================================
-- PATIENT_INVESTIGATIONS TABLE  
-- ===================================
ALTER TABLE patient_investigations 
RENAME COLUMN ordered_by TO orderedBy;

ALTER TABLE patient_investigations 
RENAME COLUMN ordered_date TO orderedDate;

ALTER TABLE patient_investigations 
RENAME COLUMN scheduled_date TO scheduledDate;

ALTER TABLE patient_investigations 
RENAME COLUMN completed_date TO completedDate;

ALTER TABLE patient_investigations 
RENAME COLUMN created_at TO createdAt;

ALTER TABLE patient_investigations 
RENAME COLUMN updated_at TO updatedAt;

-- ===================================
-- PATIENT_THERAPIES TABLE
-- ===================================
ALTER TABLE patient_therapies 
RENAME COLUMN prescribed_by TO prescribedBy;

ALTER TABLE patient_therapies 
RENAME COLUMN start_date TO startDate;

ALTER TABLE patient_therapies 
RENAME COLUMN created_at TO createdAt;

ALTER TABLE patient_therapies 
RENAME COLUMN updated_at TO updatedAt;

-- ===================================
-- PATIENT_CASE_ENTRIES TABLE
-- ===================================
ALTER TABLE patient_case_entries 
RENAME COLUMN entry_type TO entryType;

ALTER TABLE patient_case_entries 
RENAME COLUMN performed_by TO performedBy;

ALTER TABLE patient_case_entries 
RENAME COLUMN can_edit TO canEdit;

-- ===================================
-- PATIENT_NOTES TABLE
-- ===================================
ALTER TABLE patient_notes 
RENAME COLUMN author_id TO authorId;

ALTER TABLE patient_notes 
RENAME COLUMN author_name TO authorName;

ALTER TABLE patient_notes 
RENAME COLUMN author_role TO authorRole;

ALTER TABLE patient_notes 
RENAME COLUMN edited_at TO editedAt;

ALTER TABLE patient_notes 
RENAME COLUMN can_edit TO canEdit;

ALTER TABLE patient_notes 
RENAME COLUMN is_edited TO isEdited;

-- ===================================
-- PATIENTS TABLE
-- ===================================
ALTER TABLE patients 
RENAME COLUMN bed_number TO bedNumber;

ALTER TABLE patients 
RENAME COLUMN assigned_doctor TO assignedDoctor;

ALTER TABLE patients 
RENAME COLUMN admission_date TO admissionDate;

ALTER TABLE patients 
RENAME COLUMN code_status TO codeStatus;

ALTER TABLE patients 
RENAME COLUMN created_at TO createdAt;

ALTER TABLE patients 
RENAME COLUMN updated_at TO updatedAt;

-- ===================================
-- STAFF TABLE
-- ===================================
ALTER TABLE staff 
RENAME COLUMN staff_id TO staffId;

ALTER TABLE staff 
RENAME COLUMN phone_number TO phoneNumber;

ALTER TABLE staff 
RENAME COLUMN is_active TO isActive;

ALTER TABLE staff 
RENAME COLUMN created_at TO createdAt;

ALTER TABLE staff 
RENAME COLUMN updated_at TO updatedAt;

-- ===================================
-- MEDICATION_HISTORY TABLE  
-- ===================================
ALTER TABLE medication_history 
RENAME COLUMN medication_id TO medicationId;

ALTER TABLE medication_history 
RENAME COLUMN performed_by TO performedBy;

COMMIT;

-- Verify the changes
SELECT column_name 
FROM information_schema.columns 
WHERE table_name IN ('patient_medications', 'patient_investigations', 'patient_therapies', 'patient_case_entries')
ORDER BY table_name, ordinal_position;