-- DATABASE CONSOLIDATION MIGRATION SCRIPT
-- Consolidates duplicate tables: therapy -> therapies, casesheetentries -> caseEntries
-- Execute this script to eliminate table duplication and achieve single source of truth

-- ========================================
-- STEP 1: PRE-MIGRATION DATA VERIFICATION
-- ========================================

-- Count existing records in all tables
SELECT 'therapy' as table_name, COUNT(*) as record_count FROM therapy
UNION ALL
SELECT 'therapies' as table_name, COUNT(*) as record_count FROM therapies
UNION ALL
SELECT 'casesheetentries' as table_name, COUNT(*) as record_count FROM casesheetentries
UNION ALL
SELECT 'caseEntries' as table_name, COUNT(*) as record_count FROM "caseEntries"
ORDER BY table_name;

-- ========================================
-- STEP 2: BACKUP EXISTING DATA (SAFETY)
-- ========================================

-- Create backup tables before migration
CREATE TABLE therapy_backup AS SELECT * FROM therapy;
CREATE TABLE casesheetentries_backup AS SELECT * FROM casesheetentries;

-- ========================================
-- STEP 3: MIGRATE THERAPY DATA
-- ========================================

-- Migrate data from therapy -> therapies
-- Map old schema to new schema with proper field alignment
INSERT INTO therapies (
    id,
    "patientId",
    "therapyType",
    "therapyName",
    description,
    "startDate",
    "endDate",
    frequency,
    "sessionDuration",
    status,
    "createdAt",
    "updatedAt",
    "createdBy"
)
SELECT
    gen_random_uuid()::text,           -- Generate new UUID for id
    "patientId",                       -- Direct mapping
    type,                             -- Map type -> therapyType
    COALESCE(type, 'General Therapy'), -- Map type -> therapyName (fallback)
    description,                       -- Direct mapping
    "startDate",                       -- Direct mapping
    "endDate",                         -- Direct mapping
    frequency,                         -- Direct mapping
    NULL,                             -- sessionDuration (not in old table)
    COALESCE(status, 'active'),       -- Map status with fallback
    COALESCE("createdAt", NOW()),      -- Map createdAt with fallback
    COALESCE("updatedAt", NOW()),      -- Map updatedAt with fallback
    "performedBy"                     -- Map performedBy -> createdBy
FROM therapy
WHERE NOT EXISTS (
    -- Avoid duplicates: check if similar record already exists in therapies
    SELECT 1 FROM therapies t2
    WHERE t2."patientId" = therapy."patientId"
    AND t2.description = therapy.description
    AND t2."createdAt" = therapy."createdAt"
);

-- ========================================
-- STEP 4: MIGRATE CASE SHEET DATA
-- ========================================

-- Migrate data from casesheetentries -> caseEntries
-- Map old schema to new schema with proper field alignment
INSERT INTO "caseEntries" (
    id,
    "patientId",
    "entryType",
    description,
    findings,
    recommendations,
    "followUpDate",
    severity,
    category,
    "createdBy",
    timestamp,
    "createdAt",
    "updatedAt",
    "deletedAt"
)
SELECT
    gen_random_uuid(),                        -- Generate new UUID for id
    "patientId",                             -- Direct mapping
    "entryType",                             -- Direct mapping
    description,                             -- Direct mapping
    NULL,                                    -- findings (not in old table)
    NULL,                                    -- recommendations (not in old table)
    NULL,                                    -- followUpDate (not in old table)
    NULL,                                    -- severity (not in old table)
    "entryType",                             -- Map entryType -> category
    "performedBy",                           -- Map performedBy -> createdBy
    timestamp,                               -- Direct mapping
    COALESCE("createdAt", NOW()),            -- Map createdAt with fallback
    COALESCE("updatedAt", NOW()),            -- Map updatedAt with fallback
    NULL                                     -- deletedAt (not deleted)
FROM casesheetentries
WHERE NOT EXISTS (
    -- Avoid duplicates: check if similar record already exists in caseEntries
    SELECT 1 FROM "caseEntries" ce
    WHERE ce."patientId" = casesheetentries."patientId"
    AND ce.description = casesheetentries.description
    AND ce.timestamp = casesheetentries.timestamp
);

-- ========================================
-- STEP 5: POST-MIGRATION VERIFICATION
-- ========================================

-- Verify migration results
SELECT 'POST-MIGRATION COUNTS' as status;

SELECT 'therapy' as table_name, COUNT(*) as record_count FROM therapy
UNION ALL
SELECT 'therapies' as table_name, COUNT(*) as record_count FROM therapies
UNION ALL
SELECT 'casesheetentries' as table_name, COUNT(*) as record_count FROM casesheetentries
UNION ALL
SELECT 'caseEntries' as table_name, COUNT(*) as record_count FROM "caseEntries"
ORDER BY table_name;

-- Check for any data integrity issues
SELECT 'THERAPY DATA INTEGRITY CHECK' as check_type;
SELECT
    COUNT(*) as total_therapies,
    COUNT(DISTINCT "patientId") as unique_patients,
    COUNT(CASE WHEN "therapyType" IS NULL THEN 1 END) as missing_therapy_type,
    COUNT(CASE WHEN description IS NULL THEN 1 END) as missing_description
FROM therapies;

SELECT 'CASE ENTRIES DATA INTEGRITY CHECK' as check_type;
SELECT
    COUNT(*) as total_entries,
    COUNT(DISTINCT "patientId") as unique_patients,
    COUNT(CASE WHEN "entryType" IS NULL THEN 1 END) as missing_entry_type,
    COUNT(CASE WHEN description IS NULL THEN 1 END) as missing_description
FROM "caseEntries";

-- ========================================
-- STEP 6: CLEANUP LEGACY TABLES (MANUAL EXECUTION AFTER VERIFICATION)
-- ========================================

-- IMPORTANT: Only execute these commands AFTER verifying migration success
-- and confirming that all applications work with the consolidated tables

-- DROP TABLE IF EXISTS therapy;
-- DROP TABLE IF EXISTS casesheetentries;
-- DROP TABLE IF EXISTS therapy_backup;
-- DROP TABLE IF EXISTS casesheetentries_backup;

-- ========================================
-- MIGRATION NOTES
-- ========================================

/*
MIGRATION SUMMARY:
1. therapy -> therapies: Consolidates therapy records into UUID-based table
2. casesheetentries -> caseEntries: Consolidates case sheet entries into UUID-based table

FIELD MAPPINGS:
therapy.type -> therapies.therapyType
therapy.performedBy -> therapies.createdBy

casesheetentries.performedBy -> caseEntries.createdBy
casesheetentries.entryType -> caseEntries.category (as well as entryType)

DATA SAFETY:
- Backup tables created before migration
- Duplicate detection prevents data corruption
- NULL value handling with sensible defaults
- Post-migration verification queries

NEXT STEPS AFTER MIGRATION:
1. Update all backend repository files to use consolidated tables
2. Update any hardcoded table references in code
3. Test all API endpoints
4. Verify frontend functionality
5. Drop legacy tables only after full verification

ROLLBACK PLAN:
If issues occur, data can be restored from backup tables:
- therapy_backup contains original therapy data
- casesheetentries_backup contains original casesheetentries data
*/