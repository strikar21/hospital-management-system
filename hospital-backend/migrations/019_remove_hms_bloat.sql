-- Migration 019: Remove HMS bloat - Focus on vitals monitoring system
-- Date: 2025-11-21
-- Purpose: Remove full HMS features not needed for real-time vitals monitoring
--
-- System Identity: Real-Time Patient Vital Monitoring System
-- NOT: Full Hospital Management System / Electronic Medical Record
--
-- What we're removing:
-- - Medication management (13 tables dropped)
-- - Lab test ordering
-- - Physiotherapy scheduling
-- - Clinical notes
-- - Medical operations tracking
-- - Bed inventory management
-- - Admission queue
-- - Complex state machines
--
-- What we're keeping:
-- - Patient vitals monitoring (core purpose)
-- - Device management (ESP32 watches)
-- - Alert detection and display
-- - Compliance (audit logs)
-- - FHIR interoperability (ABDM)
-- - Hardware expansion tables (impedancereadings, neural_events for future use)

BEGIN;

-- =============================================================================
-- BACKUP CHECK: Ensure backup exists before proceeding
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '⚠️  IMPORTANT: Ensure you have a database backup before running this migration!';
    RAISE NOTICE '    Run: cd hospital-backend && python backup_database.py';
    RAISE NOTICE '';
    RAISE NOTICE '🗑️  This migration will DROP 13 tables permanently:';
    RAISE NOTICE '    - medicationadministrations, medications';
    RAISE NOTICE '    - investigations';
    RAISE NOTICE '    - therapysessions, therapy, therapies_legacy';
    RAISE NOTICE '    - patientnotes';
    RAISE NOTICE '    - caseEntries, medical_operations, atomic_transactions';
    RAISE NOTICE '    - beds, admissionrecommendations, patientstates';
    RAISE NOTICE '';
    RAISE NOTICE '✅ Keeping: patients, devices, vitals, alerts, compliance tables';
    RAISE NOTICE '✅ Keeping: impedancereadings, neural_events (future hardware)';
END $$;

-- =============================================================================
-- DROP MEDICATION MANAGEMENT TABLES
-- =============================================================================

-- Medication administration tracking (nurses administering medications)
DROP TABLE IF EXISTS medicationadministrations CASCADE;
COMMENT ON SCHEMA public IS 'Dropped medicationadministrations - not managing medication doses';

-- Medication prescriptions
DROP TABLE IF EXISTS medications CASCADE;
COMMENT ON SCHEMA public IS 'Dropped medications - not managing prescriptions';

-- =============================================================================
-- DROP LAB TEST MANAGEMENT TABLES
-- =============================================================================

-- Lab test orders (CBC, X-ray, etc.)
DROP TABLE IF EXISTS investigations CASCADE;
COMMENT ON SCHEMA public IS 'Dropped investigations - not ordering lab tests';

-- =============================================================================
-- DROP PHYSIOTHERAPY MANAGEMENT TABLES
-- =============================================================================

-- Therapy sessions
DROP TABLE IF EXISTS therapysessions CASCADE;
COMMENT ON SCHEMA public IS 'Dropped therapysessions - not managing physiotherapy';

-- Therapy plans
DROP TABLE IF EXISTS therapy CASCADE;
COMMENT ON SCHEMA public IS 'Dropped therapy - not managing therapy sessions';

-- Legacy therapy data
DROP TABLE IF EXISTS therapies_legacy CASCADE;
COMMENT ON SCHEMA public IS 'Dropped therapies_legacy - old unused data';

-- =============================================================================
-- DROP CLINICAL NOTES TABLES
-- =============================================================================

-- Doctor/nurse clinical notes
DROP TABLE IF EXISTS patientnotes CASCADE;
COMMENT ON SCHEMA public IS 'Dropped patientnotes - not building full EMR with clinical notes';

-- =============================================================================
-- DROP MEDICAL OPERATIONS TRACKING TABLES
-- =============================================================================

-- Medical operation audit trail (tracks all medication/investigation/therapy changes)
DROP TABLE IF EXISTS caseEntries CASCADE;
COMMENT ON SCHEMA public IS 'Dropped caseEntries - not tracking medical operation history';

-- Surgical procedures
DROP TABLE IF EXISTS medical_operations CASCADE;
COMMENT ON SCHEMA public IS 'Dropped medical_operations - not managing surgeries';

-- Complex atomic transactions for medical operations
DROP TABLE IF EXISTS atomic_transactions CASCADE;
COMMENT ON SCHEMA public IS 'Dropped atomic_transactions - unnecessary complexity for vitals monitoring';

-- =============================================================================
-- DROP UNNECESSARY INFRASTRUCTURE TABLES
-- =============================================================================

-- Bed inventory management
DROP TABLE IF EXISTS beds CASCADE;
COMMENT ON SCHEMA public IS 'Dropped beds - room/bed numbers are manual text entries in patients table';

-- Admission queue/recommendations
DROP TABLE IF EXISTS admissionrecommendations CASCADE;
COMMENT ON SCHEMA public IS 'Dropped admissionrecommendations - patients admitted directly without queue';

-- Complex patient state machine
DROP TABLE IF EXISTS patientstates CASCADE;
COMMENT ON SCHEMA public IS 'Dropped patientstates - using simple patients.status field instead';

-- =============================================================================
-- VERIFY REMAINING TABLES
-- =============================================================================

DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM pg_tables
    WHERE schemaname = 'public'
    AND tablename NOT LIKE 'pg_%'
    AND tablename NOT LIKE 'sql_%';

    RAISE NOTICE '';
    RAISE NOTICE '✅ Migration complete!';
    RAISE NOTICE '   Remaining tables: %', table_count;
    RAISE NOTICE '';
    RAISE NOTICE '📋 Core tables kept:';
    RAISE NOTICE '   - patients, staff (core entities)';
    RAISE NOTICE '   - devices, deviceassignments (ESP32 watches)';
    RAISE NOTICE '   - device_certificates, device_mac_mapping, provisioning_codes (device security)';
    RAISE NOTICE '   - deviceBaselines, deviceCalibration, deviceMaintenanceHistory (device quality)';
    RAISE NOTICE '   - patient_alerts (critical alerts)';
    RAISE NOTICE '   - auditlog, token_blacklist (compliance & security)';
    RAISE NOTICE '   - fhir_resources, fhir_resource_history, loinc_vital_mapping (FHIR/ABDM)';
    RAISE NOTICE '   - discharge_requests, watchremovalevents (discharge workflow)';
    RAISE NOTICE '   - impedancereadings, neural_events (future hardware expansion)';
    RAISE NOTICE '';
    RAISE NOTICE '📡 TimescaleDB tables (separate database):';
    RAISE NOTICE '   - vitals_realtime, vitals_timeseries (time-series vitals)';
    RAISE NOTICE '   - waveform_snapshots (ECG/EEG waveforms)';
    RAISE NOTICE '   - neural_events (EEG events)';
    RAISE NOTICE '';
    RAISE NOTICE '🗑️  Dropped 13 HMS bloat tables (medications, investigations, therapy, notes, etc.)';
END $$;

COMMIT;

-- =============================================================================
-- POST-MIGRATION CHECKLIST
-- =============================================================================

-- [ ] Update backend code:
--     1. Remove API routers: medications, investigations, therapy, patient notes
--     2. Remove Pydantic models for dropped tables
--     3. Update main.py router registrations
--     4. Remove unused service files
--
-- [ ] Update frontend code:
--     1. Remove medication management UI
--     2. Remove investigation ordering UI
--     3. Remove therapy scheduling UI
--     4. Remove clinical notes UI
--
-- [ ] Test core workflows:
--     1. Patient admission ✓
--     2. Device assignment ✓
--     3. Vitals monitoring (ESP32 → MQTT → Backend → TimescaleDB) ✓
--     4. Alert detection ✓
--     5. Patient discharge ✓
--
-- [ ] Update documentation:
--     1. README.md - Remove HMS features from endpoints list
--     2. Update system description - emphasize "vitals monitoring" not "HMS"
--     3. Update API documentation

-- =============================================================================
-- ROLLBACK (if needed)
-- =============================================================================

-- If you need to rollback this migration, restore from backup:
-- psql -h localhost -p 5432 -U hospital -d hospitaldb < backup_YYYYMMDD_HHMMSS.sql
