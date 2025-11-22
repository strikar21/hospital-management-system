-- Migration 020: Create patients VIEW from FHIR and drop HMS patients table
-- Date: 2025-11-21
-- Purpose: Complete migration to FHIR-first architecture
--
-- What this does:
-- 1. Creates a PostgreSQL VIEW that extracts patient data from FHIR resources
-- 2. VIEW provides same columns as old HMS patients table (backward compatibility)
-- 3. Drops the HMS patients table (data already migrated to fhir_resources)
--
-- Result: Single source of truth (FHIR), no data duplication

BEGIN;

-- ============================================================================
-- CREATE PATIENTS VIEW (Backward Compatibility Layer)
-- ============================================================================

CREATE OR REPLACE VIEW patients AS
SELECT
    -- Extract from FHIR resource JSONB
    resourceid AS id,
    (resource->'name'->0->>'family') AS "lastName",
    (resource->'name'->0->'given'->>0) AS "firstName",
    (resource->>'birthDate')::DATE AS "dateOfBirth",
    INITCAP(resource->>'gender') AS gender,

    -- Extract phone number (first telecom entry)
    (resource->'telecom'->0->>'value') AS "phoneNumber",

    -- Extract emergency contact from contact array
    (resource->'contact'->0->'name'->>'text') AS "emergencyContactName",
    (resource->'contact'->0->'telecom'->0->>'value') AS "emergencyContactPhone",

    -- Extract extensions (HMS-specific fields stored as FHIR extensions)
    (
        SELECT ext->>'valueString'
        FROM jsonb_array_elements(resource->'extension') AS ext
        WHERE ext->>'url' = 'https://hospital.local/fhir/StructureDefinition/blood-type'
    ) AS "bloodType",

    (
        SELECT ext->>'valueString'
        FROM jsonb_array_elements(resource->'extension') AS ext
        WHERE ext->>'url' = 'https://hospital.local/fhir/StructureDefinition/allergies'
    ) AS allergies,

    (
        SELECT ext->>'valueString'
        FROM jsonb_array_elements(resource->'extension') AS ext
        WHERE ext->>'url' = 'https://hospital.local/fhir/StructureDefinition/medical-history'
    ) AS "medicalHistory",

    (
        SELECT ext->>'valueString'
        FROM jsonb_array_elements(resource->'extension') AS ext
        WHERE ext->>'url' = 'https://hospital.local/fhir/StructureDefinition/current-medications'
    ) AS "currentMedications",

    -- Extract room/bed from location extension
    (
        SELECT loc_ext->>'valueString'
        FROM jsonb_array_elements(resource->'extension') AS ext,
        jsonb_array_elements(ext->'extension') AS loc_ext
        WHERE ext->>'url' = 'https://hospital.local/fhir/StructureDefinition/patient-location'
        AND loc_ext->>'url' = 'roomNumber'
    ) AS "roomNumber",

    (
        SELECT loc_ext->>'valueString'
        FROM jsonb_array_elements(resource->'extension') AS ext,
        jsonb_array_elements(ext->'extension') AS loc_ext
        WHERE ext->>'url' = 'https://hospital.local/fhir/StructureDefinition/patient-location'
        AND loc_ext->>'url' = 'bedNumber'
    ) AS "bedNumber",

    -- Extract admission date from extension
    (
        SELECT (ext->>'valueDateTime')::TIMESTAMPTZ
        FROM jsonb_array_elements(resource->'extension') AS ext
        WHERE ext->>'url' = 'https://hospital.local/fhir/StructureDefinition/admission-date'
    ) AS "admissionDate",

    -- Extract attending physician
    (
        SELECT REPLACE(ext->'valueReference'->>'reference', 'Practitioner/', '')
        FROM jsonb_array_elements(resource->'extension') AS ext
        WHERE ext->>'url' = 'https://hospital.local/fhir/StructureDefinition/attending-physician'
    ) AS "attendingPhysician",

    -- Extract nurse in charge
    (
        SELECT REPLACE(ext->'valueReference'->>'reference', 'Practitioner/', '')
        FROM jsonb_array_elements(resource->'extension') AS ext
        WHERE ext->>'url' = 'https://hospital.local/fhir/StructureDefinition/nurse-in-charge'
    ) AS "nurseInCharge",

    -- Status
    CASE WHEN (resource->>'active')::BOOLEAN THEN 'active' ELSE 'inactive' END AS status,

    -- Discharge status (derived from active status for now)
    CASE WHEN (resource->>'active')::BOOLEAN THEN 'active' ELSE 'discharged' END AS "dischargeStatus",

    NULL::TIMESTAMPTZ AS "dischargeDate",  -- TODO: Add discharge extension

    -- MRN from identifier
    (
        SELECT ident->>'value'
        FROM jsonb_array_elements(resource->'identifier') AS ident
        WHERE ident->'type'->'coding'->0->>'code' = 'MR'
    ) AS mrn,

    -- Weight
    (
        SELECT (ext->'valueQuantity'->>'value')::NUMERIC(5,2)
        FROM jsonb_array_elements(resource->'extension') AS ext
        WHERE ext->>'url' = 'https://hospital.local/fhir/StructureDefinition/weight'
    ) AS weight,

    -- Diagnosis
    (
        SELECT ext->>'valueString'
        FROM jsonb_array_elements(resource->'extension') AS ext
        WHERE ext->>'url' = 'https://hospital.local/fhir/StructureDefinition/diagnosis'
    ) AS diagnosis,

    -- Metadata
    "createdAt",
    "lastUpdated" AS "updatedAt",

    NULL AS "recommendedFrom"  -- TODO: Add if needed

FROM fhir_resources
WHERE resourcetype = 'Patient'
AND deleted = false;

COMMENT ON VIEW patients IS 'Backward-compatible view extracting patient data from FHIR resources (fhir_resources table)';

-- ============================================================================
-- DROP HMS PATIENTS TABLE (Data already migrated to FHIR)
-- ============================================================================

-- Drop foreign key constraints first (if any)
ALTER TABLE deviceassignments DROP CONSTRAINT IF EXISTS fk_deviceassignments_patient;
ALTER TABLE patient_alerts DROP CONSTRAINT IF EXISTS fk_patient_alerts_patient;
ALTER TABLE discharge_requests DROP CONSTRAINT IF EXISTS fk_discharge_requests_patient;

-- Drop the HMS patients table
DROP TABLE IF EXISTS patients CASCADE;

COMMENT ON SCHEMA public IS 'Dropped HMS patients table - migrated to FHIR fhir_resources (use patients VIEW for queries)';

-- ============================================================================
-- VERIFY MIGRATION
-- ============================================================================

DO $$
DECLARE
    view_count INTEGER;
    fhir_count INTEGER;
BEGIN
    -- Count patients in VIEW
    SELECT COUNT(*) INTO view_count FROM patients;

    -- Count FHIR Patient resources
    SELECT COUNT(*) INTO fhir_count FROM fhir_resources WHERE resourcetype = 'Patient' AND deleted = false;

    RAISE NOTICE '';
    RAISE NOTICE 'Migration 020 Complete!';
    RAISE NOTICE '========================';
    RAISE NOTICE 'patients VIEW: % rows', view_count;
    RAISE NOTICE 'FHIR Patient resources: % rows', fhir_count;
    RAISE NOTICE '';

    IF view_count = fhir_count THEN
        RAISE NOTICE 'SUCCESS: VIEW matches FHIR resources';
    ELSE
        RAISE WARNING 'MISMATCH: VIEW count != FHIR count';
    END IF;

    RAISE NOTICE '';
    RAISE NOTICE 'HMS patients table: DROPPED';
    RAISE NOTICE 'New patients VIEW: CREATED (reads from fhir_resources)';
    RAISE NOTICE 'Single source of truth: FHIR';
END $$;

COMMIT;

-- ============================================================================
-- POST-MIGRATION NOTES
-- ============================================================================

-- Old code using "SELECT * FROM patients" will continue to work (VIEW)
-- New code should use FHIR API: GET /fhir/r5/Patient

-- To create new patients:
-- OLD: INSERT INTO patients (...) -- This will FAIL (no table)
-- NEW: Use FHIR service to create Patient resource in fhir_resources

-- To update patients:
-- OLD: UPDATE patients SET ... WHERE id = ... -- This will FAIL (VIEW not updatable)
-- NEW: Use FHIR service to update Patient resource

-- To delete patients:
-- OLD: DELETE FROM patients WHERE id = ... -- This will FAIL (VIEW not updatable)
-- NEW: Use FHIR service soft delete (set deleted = true in fhir_resources)
