-- Migration 016: Pure FHIR R5 Storage
-- Date: 2025-11-19
-- Purpose: Ground-up FHIR R5 implementation - single unified resource table
-- Architecture: Store all FHIR resources (Patient, Observation, Device, etc.) in one table

BEGIN;

-- ============================================================================
-- FHIR R5 RESOURCE STORAGE (Unified Table)
-- ============================================================================

-- Single table for ALL FHIR resources
-- This follows FHIR R5 specification for resource storage
CREATE TABLE IF NOT EXISTS fhir_resources (
    -- Primary identifiers
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resourceType TEXT NOT NULL,  -- Patient, Observation, Device, Medication, etc.
    resourceId TEXT NOT NULL,    -- Logical ID (PAT0001, fit-00001, MED-123, etc.)

    -- FHIR resource (complete JSON)
    resource JSONB NOT NULL,     -- Complete FHIR R5 resource as JSON

    -- Versioning (FHIR requires version tracking)
    version INTEGER NOT NULL DEFAULT 1,
    lastUpdated TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Fast search indexes (extracted from resource JSONB for performance)
    identifiers JSONB,  -- Array of {system, value} for identifier searches
    resourceReferences JSONB,   -- Array of {type, id} for reference searches (patient, device, etc.)

    -- Status tracking
    status TEXT,  -- active, inactive, entered-in-error, etc. (extracted for fast filtering)

    -- Soft delete (FHIR requires maintaining history)
    deleted BOOLEAN DEFAULT false,
    deletedAt TIMESTAMPTZ,
    deletedBy TEXT,

    -- Audit
    createdAt TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    createdBy TEXT,

    -- Unique constraint: one resource per type+id combination
    UNIQUE(resourceType, resourceId)
);

COMMENT ON TABLE fhir_resources IS 'Unified FHIR R5 resource storage - all resource types in one table';
COMMENT ON COLUMN fhir_resources.resource IS 'Complete FHIR R5 resource as JSON (Patient, Observation, Device, etc.)';
COMMENT ON COLUMN fhir_resources.identifiers IS 'Extracted identifiers for fast search: [{system, value, type}]';
COMMENT ON COLUMN fhir_resources.resourceReferences IS 'Extracted references for fast search: [{resourceType, resourceId}]';

-- ============================================================================
-- INDEXES FOR FAST FHIR QUERIES
-- ============================================================================

-- Primary search indexes
CREATE INDEX IF NOT EXISTS idx_fhir_resource_type ON fhir_resources(resourceType) WHERE deleted = false;
CREATE INDEX IF NOT EXISTS idx_fhir_resource_type_id ON fhir_resources(resourceType, resourceId) WHERE deleted = false;
CREATE INDEX IF NOT EXISTS idx_fhir_resource_status ON fhir_resources(resourceType, status) WHERE deleted = false;
CREATE INDEX IF NOT EXISTS idx_fhir_lastUpdated ON fhir_resources(resourceType, lastUpdated DESC) WHERE deleted = false;

-- JSONB indexes for identifier and reference searches
CREATE INDEX IF NOT EXISTS idx_fhir_identifiers ON fhir_resources USING GIN(identifiers);
CREATE INDEX IF NOT EXISTS idx_fhir_references ON fhir_resources USING GIN(resourceReferences);

-- Full-text search on resource content
CREATE INDEX IF NOT EXISTS idx_fhir_resource_content ON fhir_resources USING GIN(resource);

-- Soft delete index
CREATE INDEX IF NOT EXISTS idx_fhir_deleted ON fhir_resources(deleted, deletedAt);

-- ============================================================================
-- HELPER FUNCTIONS FOR FHIR OPERATIONS
-- ============================================================================

-- Function to extract identifiers from FHIR resource
CREATE OR REPLACE FUNCTION extract_fhir_identifiers(fhir_resource JSONB)
RETURNS JSONB AS $$
DECLARE
    identifiers JSONB;
BEGIN
    -- Extract identifier array from resource
    -- Format: [{"system": "https://...", "value": "123", "type": {...}}]
    SELECT jsonb_agg(
        jsonb_build_object(
            'system', (identifier->>'system'),
            'value', (identifier->>'value'),
            'type', (identifier->'type'->>'text')
        )
    )
    INTO identifiers
    FROM jsonb_array_elements(fhir_resource->'identifier') AS identifier
    WHERE identifier->>'value' IS NOT NULL;

    RETURN COALESCE(identifiers, '[]'::jsonb);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to extract references from FHIR resource
CREATE OR REPLACE FUNCTION extract_fhir_references(fhir_resource JSONB)
RETURNS JSONB AS $$
DECLARE
    ref_list JSONB;
BEGIN
    -- Extract common references: subject, patient, device, performer, etc.
    WITH extracted AS (
        SELECT jsonb_build_object(
            'reference', kv.value->>'reference',
            'display', kv.value->>'display'
        ) AS ref
        FROM jsonb_each(fhir_resource) AS kv
        WHERE kv.key IN ('subject', 'patient', 'device', 'performer', 'encounter', 'location', 'medication')
          AND jsonb_typeof(kv.value) = 'object'
          AND kv.value->>'reference' IS NOT NULL

        UNION ALL

        -- Handle arrays of references (performer, device arrays)
        SELECT jsonb_build_object(
            'reference', elem->>'reference',
            'display', elem->>'display'
        ) AS ref
        FROM jsonb_each(fhir_resource) AS kv,
             jsonb_array_elements(kv.value) AS elem
        WHERE kv.key IN ('performer', 'device', 'participant')
          AND jsonb_typeof(kv.value) = 'array'
          AND elem->>'reference' IS NOT NULL
    )
    SELECT jsonb_agg(ref) INTO ref_list FROM extracted;

    RETURN COALESCE(ref_list, '[]'::jsonb);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to extract status from FHIR resource
CREATE OR REPLACE FUNCTION extract_fhir_status(fhir_resource JSONB)
RETURNS TEXT AS $$
BEGIN
    RETURN fhir_resource->>'status';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- TRIGGER TO AUTO-EXTRACT SEARCH FIELDS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_fhir_search_fields()
RETURNS TRIGGER AS $$
BEGIN
    -- Auto-extract identifiers, references, and status from resource JSON
    NEW.identifiers := extract_fhir_identifiers(NEW.resource);
    NEW.resourceReferences := extract_fhir_references(NEW.resource);
    NEW.status := extract_fhir_status(NEW.resource);
    NEW.lastUpdated := NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_fhir_search_fields
    BEFORE INSERT OR UPDATE ON fhir_resources
    FOR EACH ROW
    EXECUTE FUNCTION update_fhir_search_fields();

-- ============================================================================
-- FHIR RESOURCE HISTORY TABLE
-- ============================================================================

-- Track all versions of resources (FHIR requires version history)
CREATE TABLE IF NOT EXISTS fhir_resource_history (
    historyId UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resourceType TEXT NOT NULL,
    resourceId TEXT NOT NULL,
    version INTEGER NOT NULL,
    resource JSONB NOT NULL,
    operation TEXT NOT NULL,  -- 'create', 'update', 'delete'
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    performedBy TEXT,

    -- Link to current resource
    currentResourceId UUID REFERENCES fhir_resources(id)
);

CREATE INDEX IF NOT EXISTS idx_fhir_history_resource ON fhir_resource_history(resourceType, resourceId, version DESC);
CREATE INDEX IF NOT EXISTS idx_fhir_history_timestamp ON fhir_resource_history(timestamp DESC);

-- Trigger to auto-create history entries
CREATE OR REPLACE FUNCTION create_fhir_resource_history()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO fhir_resource_history (
            resourceType, resourceId, version, resource, operation, performedBy, currentResourceId
        ) VALUES (
            NEW.resourceType, NEW.resourceId, NEW.version, NEW.resource, 'create', NEW.createdBy, NEW.id
        );
    ELSIF TG_OP = 'UPDATE' AND OLD.resource::text != NEW.resource::text THEN
        INSERT INTO fhir_resource_history (
            resourceType, resourceId, version, resource, operation, performedBy, currentResourceId
        ) VALUES (
            NEW.resourceType, NEW.resourceId, NEW.version, NEW.resource, 'update', NEW.createdBy, NEW.id
        );
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO fhir_resource_history (
            resourceType, resourceId, version, resource, operation, performedBy, currentResourceId
        ) VALUES (
            OLD.resourceType, OLD.resourceId, OLD.version, OLD.resource, 'delete', OLD.deletedBy, OLD.id
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_fhir_resource_history
    AFTER INSERT OR UPDATE OR DELETE ON fhir_resources
    FOR EACH ROW
    EXECUTE FUNCTION create_fhir_resource_history();

-- ============================================================================
-- FHIR SEARCH HELPER VIEWS
-- ============================================================================

-- View for active resources only (most common query)
CREATE OR REPLACE VIEW fhir_resources_active AS
SELECT * FROM fhir_resources
WHERE deleted = false;

COMMENT ON VIEW fhir_resources_active IS 'All active (non-deleted) FHIR resources';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify table creation
SELECT 'FHIR R5 resource storage created successfully' as status;

-- Show table structure
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'fhir_resources'
ORDER BY ordinal_position;

COMMIT;

-- ============================================================================
-- USAGE EXAMPLES (for documentation)
-- ============================================================================

/*
-- Example 1: Create a FHIR Patient resource
INSERT INTO fhir_resources (resourceType, resourceId, resource, createdBy) VALUES (
    'Patient',
    'PAT0001',
    '{
        "resourceType": "Patient",
        "id": "PAT0001",
        "identifier": [
            {"system": "https://hospital.com/mrn", "value": "HMS2024000001"},
            {"system": "https://healthid.abdm.gov.in", "value": "91-1234-5678-9012-3456"}
        ],
        "name": [{"family": "Kumar", "given": ["Rajesh"]}],
        "gender": "male",
        "birthDate": "1985-03-15",
        "status": "active"
    }'::jsonb,
    'SYSTEM'
);

-- Example 2: Search by identifier (auto-indexed)
SELECT * FROM fhir_resources
WHERE resourceType = 'Patient'
  AND identifiers @> '[{"value": "HMS2024000001"}]'::jsonb;

-- Example 3: Get all observations for a patient (reference search)
SELECT * FROM fhir_resources
WHERE resourceType = 'Observation'
  AND resourceReferences @> '[{"reference": "Patient/PAT0001"}]'::jsonb;

-- Example 4: Get resource history
SELECT * FROM fhir_resource_history
WHERE resourceType = 'Patient' AND resourceId = 'PAT0001'
ORDER BY version DESC;
*/
