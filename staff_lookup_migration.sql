-- ========================================
-- STAFF LOOKUP REFACTOR MIGRATION
-- Single Source of Truth: Staff Table
-- ========================================
-- Date: 2025-10-04
-- Purpose: Eliminate redundant data storage and implement staff table lookups
--
-- Changes:
-- 1. Add prescribedBy to investigations and therapy tables
-- 2. Backfill data from performedBy fields
-- 3. Add indexes for JOIN performance
-- 4. (Later) Drop redundant authorName/authorRole from patientnotes
--
-- ========================================

-- PHASE 1: ADD COLUMNS
-- ========================================

-- Add prescribedBy to investigations table
ALTER TABLE investigations ADD COLUMN IF NOT EXISTS "prescribedBy" TEXT;

-- Add prescribedBy to therapy table
ALTER TABLE therapy ADD COLUMN IF NOT EXISTS "prescribedBy" TEXT;

-- ========================================
-- PHASE 2: BACKFILL DATA
-- ========================================

-- Backfill investigations.prescribedBy from performedBy
-- (performedBy was being used as prescribedBy before schema fix)
UPDATE investigations
SET "prescribedBy" = "performedBy"
WHERE "prescribedBy" IS NULL AND "performedBy" IS NOT NULL;

-- Backfill therapy.prescribedBy from performedBy
-- (performedBy was being used as prescribedBy before schema fix)
UPDATE therapy
SET "prescribedBy" = "performedBy"
WHERE "prescribedBy" IS NULL AND "performedBy" IS NOT NULL;

-- ========================================
-- PHASE 3: ADD INDEXES FOR PERFORMANCE
-- ========================================

-- Index on staff.id for fast lookups (if not exists)
CREATE INDEX IF NOT EXISTS idx_staff_id ON staff(id);

-- Index on investigations.prescribedBy for LEFT JOIN performance
CREATE INDEX IF NOT EXISTS idx_investigations_prescribed_by ON investigations("prescribedBy");

-- Index on therapy.prescribedBy for LEFT JOIN performance
CREATE INDEX IF NOT EXISTS idx_therapy_prescribed_by ON therapy("prescribedBy");

-- Index on patientnotes.authorId for LEFT JOIN performance
CREATE INDEX IF NOT EXISTS idx_patientnotes_author_id ON patientnotes("authorId");

-- Index on medications.prescribedBy (should already exist, but ensure)
CREATE INDEX IF NOT EXISTS idx_medications_prescribed_by ON medications("prescribedBy");

-- ========================================
-- PHASE 4: VERIFICATION QUERIES
-- ========================================

-- Verify investigations have prescribedBy populated
SELECT
    'investigations' as table_name,
    COUNT(*) as total_records,
    COUNT("prescribedBy") as with_prescribed_by,
    COUNT(*) - COUNT("prescribedBy") as missing_prescribed_by
FROM investigations;

-- Verify therapy has prescribedBy populated
SELECT
    'therapy' as table_name,
    COUNT(*) as total_records,
    COUNT("prescribedBy") as with_prescribed_by,
    COUNT(*) - COUNT("prescribedBy") as missing_prescribed_by
FROM therapy;

-- Verify staff table has all referenced IDs
SELECT
    'Missing staff in investigations' as issue,
    COUNT(DISTINCT i."prescribedBy") as count
FROM investigations i
LEFT JOIN staff s ON i."prescribedBy" = s.id
WHERE i."prescribedBy" IS NOT NULL AND s.id IS NULL;

SELECT
    'Missing staff in therapy' as issue,
    COUNT(DISTINCT t."prescribedBy") as count
FROM therapy t
LEFT JOIN staff s ON t."prescribedBy" = s.id
WHERE t."prescribedBy" IS NOT NULL AND s.id IS NULL;

SELECT
    'Missing staff in patientnotes' as issue,
    COUNT(DISTINCT pn."authorId") as count
FROM patientnotes pn
LEFT JOIN staff s ON pn."authorId" = s.id
WHERE pn."authorId" IS NOT NULL AND s.id IS NULL;

-- ========================================
-- PHASE 5: TEST LEFT JOIN QUERIES
-- ========================================

-- Test query: Investigations with staff lookup
SELECT
    i.id,
    i.name,
    i."prescribedBy",
    COALESCE(s."firstName" || ' ' || s."lastName", 'Unknown') as "prescribedByName",
    s.role as "prescribedByRole"
FROM investigations i
LEFT JOIN staff s ON i."prescribedBy" = s.id
LIMIT 5;

-- Test query: Therapy with staff lookup
SELECT
    t.id,
    t.description,
    t."prescribedBy",
    COALESCE(s."firstName" || ' ' || s."lastName", 'Unknown') as "prescribedByName",
    s.role as "prescribedByRole"
FROM therapy t
LEFT JOIN staff s ON t."prescribedBy" = s.id
LIMIT 5;

-- Test query: Patient notes with staff lookup
SELECT
    pn.id,
    pn.content,
    pn."authorId",
    COALESCE(s."firstName" || ' ' || s."lastName", pn."authorName") as "authorName",
    COALESCE(s.role, pn."authorRole") as "authorRole"
FROM patientnotes pn
LEFT JOIN staff s ON pn."authorId" = s.id
LIMIT 5;

-- ========================================
-- PHASE 6: DROP REDUNDANT COLUMNS (AFTER BACKEND DEPLOYED)
-- ========================================
--
-- IMPORTANT: Only run these after backend code is updated and deployed
-- to use LEFT JOIN staff lookups for authorName and authorRole
--
-- ALTER TABLE patientnotes DROP COLUMN IF EXISTS "authorName";
-- ALTER TABLE patientnotes DROP COLUMN IF EXISTS "authorRole";

-- ========================================
-- ROLLBACK SCRIPT (IF NEEDED)
-- ========================================
--
-- To rollback this migration:
--
-- DROP INDEX IF EXISTS idx_staff_id;
-- DROP INDEX IF EXISTS idx_investigations_prescribed_by;
-- DROP INDEX IF EXISTS idx_therapy_prescribed_by;
-- DROP INDEX IF EXISTS idx_patientnotes_author_id;
-- DROP INDEX IF EXISTS idx_medications_prescribed_by;
--
-- ALTER TABLE investigations DROP COLUMN IF EXISTS "prescribedBy";
-- ALTER TABLE therapy DROP COLUMN IF EXISTS "prescribedBy";
--
-- Note: Cannot rollback authorName/authorRole drops without data loss
-- (this is why Phase 6 should only run after backend is confirmed working)

-- ========================================
-- MIGRATION COMPLETE
-- ========================================
-- Next steps:
-- 1. Update backend code to use LEFT JOIN staff in all queries
-- 2. Update frontend to handle optional authorName/authorRole
-- 3. Test thoroughly
-- 4. Deploy backend
-- 5. Deploy frontend
-- 6. Run Phase 6 to drop redundant columns
