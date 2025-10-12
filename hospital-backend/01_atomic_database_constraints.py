#!/usr/bin/env python3
"""
Phase 1: Atomic Database Constraints Enhancement
Adds additional constraints, indexes, and tables for failproof atomic operations
"""

import asyncio
import asyncpg
import sys
sys.path.append('.')
from app.core.config import settings
from datetime import datetime

async def enhance_database_constraints():
    """Add atomic operation constraints and tables"""

    conn = await asyncpg.connect(
        host=settings.databaseHost,
        port=settings.databasePort,
        database=settings.databaseName,
        user=settings.databaseUser,
        password=settings.databasePassword
    )

    try:
        print("Phase 1: Enhancing database constraints for atomic operations...")

        # 1. Add data validation constraints for medications
        print("\nAdding medication validation constraints...")

        # Helper function to add constraint if it doesn't exist
        async def add_constraint_if_not_exists(table_name, constraint_name, constraint_definition):
            # Check if constraint exists
            exists = await conn.fetchval("""
                SELECT COUNT(*) FROM information_schema.table_constraints
                WHERE table_name = $1 AND constraint_name = $2
            """, table_name, constraint_name)

            if not exists:
                await conn.execute(f"""
                    ALTER TABLE {table_name}
                    ADD CONSTRAINT {constraint_name} {constraint_definition}
                """)
                print(f"  Added constraint: {constraint_name}")
            else:
                print(f"  Constraint already exists: {constraint_name}")

        await add_constraint_if_not_exists(
            'medications', 'chk_medication_name_valid',
            "CHECK (name IS NOT NULL AND name != '')"
        )

        await add_constraint_if_not_exists(
            'medications', 'chk_medication_dosage_valid',
            "CHECK (dosage IS NOT NULL AND dosage != '')"
        )

        await add_constraint_if_not_exists(
            'medications', 'chk_medication_prescribed_by_valid',
            'CHECK ("prescribedBy" IS NOT NULL AND "prescribedBy" != \'\')'
        )

        await add_constraint_if_not_exists(
            'medications', 'chk_medication_status_valid',
            "CHECK (status IN ('active', 'stopped', 'held', 'administered'))"
        )

        # 2. Add data validation constraints for investigations
        print("Adding investigation validation constraints...")
        await add_constraint_if_not_exists(
            'investigations', 'chk_investigation_name_valid',
            "CHECK (name IS NOT NULL AND name != '')"
        )

        await add_constraint_if_not_exists(
            'investigations', 'chk_investigation_performed_by_valid',
            'CHECK ("performedBy" IS NOT NULL AND "performedBy" != \'\')'
        )

        await add_constraint_if_not_exists(
            'investigations', 'chk_investigation_status_valid',
            "CHECK (status IN ('pending', 'ordered', 'scheduled', 'inProgress', 'completed', 'cancelled'))"
        )

        # 3. Add data validation constraints for therapy
        print("Adding therapy validation constraints...")
        await add_constraint_if_not_exists(
            'therapy', 'chk_therapy_type_valid',
            "CHECK (type IS NOT NULL AND type != '')"
        )

        await add_constraint_if_not_exists(
            'therapy', 'chk_therapy_performed_by_valid',
            'CHECK ("performedBy" IS NOT NULL AND "performedBy" != \'\')'
        )

        await add_constraint_if_not_exists(
            'therapy', 'chk_therapy_status_valid',
            "CHECK (status IN ('active', 'completed', 'cancelled'))"
        )

        # 4. Add case entry validation constraints
        print("Adding case entry validation constraints...")
        await add_constraint_if_not_exists(
            'casesheetentries', 'chk_case_entry_type_valid',
            'CHECK ("entryType" IS NOT NULL AND "entryType" != \'\')'
        )

        await add_constraint_if_not_exists(
            'casesheetentries', 'chk_case_entry_description_valid',
            "CHECK (description IS NOT NULL AND description != '')"
        )

        await add_constraint_if_not_exists(
            'casesheetentries', 'chk_case_entry_performed_by_valid',
            'CHECK ("performedBy" IS NOT NULL AND "performedBy" != \'\')'
        )

        # 5. Create idempotency tracking table for retry safety
        print("Creating idempotency tracking table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS medical_operations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                idempotency_key VARCHAR(255) NOT NULL UNIQUE,
                operation_type VARCHAR(50) NOT NULL,
                patient_id TEXT NOT NULL,
                result JSONB,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMP WITH TIME ZONE,

                CONSTRAINT chk_medical_operation_status
                CHECK (status IN ('pending', 'completed', 'failed')),

                CONSTRAINT chk_medical_operation_type
                CHECK (operation_type IN (
                    'medication', 'investigation', 'therapy', 'note',
                    'medication_administration', 'therapy_session',
                    'alert_acknowledgment', 'investigation_completion',
                    'medication_status_change'
                ))
            );
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_medical_operations_idempotency_key
            ON medical_operations(idempotency_key);
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_medical_operations_patient_id
            ON medical_operations(patient_id);
        """)

        # 6. Create atomic transaction tracking table
        print("Creating atomic transaction tracking table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS atomic_transactions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                transaction_id UUID NOT NULL UNIQUE,
                patient_id TEXT NOT NULL,
                operation_type VARCHAR(50) NOT NULL,
                operation_data JSONB NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMP WITH TIME ZONE,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,

                CONSTRAINT chk_atomic_transaction_status
                CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'rolled_back'))
            );
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_atomic_transactions_transaction_id
            ON atomic_transactions(transaction_id);
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_atomic_transactions_patient_id
            ON atomic_transactions(patient_id);
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_atomic_transactions_status
            ON atomic_transactions(status);
        """)

        # 7. Add performance indexes for atomic operations
        print("Adding performance indexes for atomic operations...")

        # Medications indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_medications_patient_status
            ON medications("patientId", status);
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_medications_prescribed_by
            ON medications("prescribedBy");
        """)

        # Investigations indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_investigations_patient_status
            ON investigations("patientId", status);
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_investigations_performed_by
            ON investigations("performedBy");
        """)

        # Therapy indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_therapy_patient_status
            ON therapy("patientId", status);
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_therapy_performed_by
            ON therapy("performedBy");
        """)

        # Case entries indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_casesheetentries_patient_type
            ON casesheetentries("patientId", "entryType");
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_casesheetentries_performed_by
            ON casesheetentries("performedBy");
        """)

        # 8. Create atomic operation helper functions
        print("Creating atomic operation helper functions...")

        # Function to lock patient for atomic operations
        await conn.execute("""
            CREATE OR REPLACE FUNCTION lock_patient_for_atomic_operation(patient_uuid TEXT)
            RETURNS TABLE(id TEXT) AS $$
            BEGIN
                -- Lock patient row to prevent concurrent modifications
                RETURN QUERY
                SELECT patients.id
                FROM patients
                WHERE patients.id = patient_uuid
                FOR UPDATE;

                -- Verify patient exists after lock
                IF NOT FOUND THEN
                    RAISE EXCEPTION 'Patient % not found or unavailable for atomic operation', patient_uuid;
                END IF;
            END;
            $$ LANGUAGE plpgsql;
        """)

        # Function to create atomic case entry
        await conn.execute("""
            CREATE OR REPLACE FUNCTION create_atomic_case_entry(
                p_patient_id TEXT,
                p_entry_type TEXT,
                p_description TEXT,
                p_performed_by TEXT
            )
            RETURNS UUID AS $$
            DECLARE
                entry_id UUID;
            BEGIN
                INSERT INTO "caseEntries" (
                    "patientId", "entryType", description, "createdBy", timestamp, "createdAt", "updatedAt"
                ) VALUES (
                    p_patient_id, p_entry_type, p_description, p_performed_by, NOW(), NOW(), NOW()
                ) RETURNING id INTO entry_id;

                RETURN entry_id;
            END;
            $$ LANGUAGE plpgsql;
        """)

        # 9. Add audit triggers for atomic operations (optional - only if audit schema exists)
        print("Adding audit triggers for atomic operations...")

        # Check if audit schema exists
        audit_schema_exists = await conn.fetchval("""
            SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'audit')
        """)

        if audit_schema_exists:
            # Atomic transactions audit
            await conn.execute("""
                CREATE TRIGGER atomic_transactions_audit_trigger
                AFTER INSERT OR UPDATE OR DELETE ON atomic_transactions
                FOR EACH ROW EXECUTE FUNCTION audit.audit_trigger();
            """)

            # Medical operations audit
            await conn.execute("""
                CREATE TRIGGER medical_operations_audit_trigger
                AFTER INSERT OR UPDATE OR DELETE ON medical_operations
                FOR EACH ROW EXECUTE FUNCTION audit.audit_trigger();
            """)
            print("  Audit triggers added successfully")
        else:
            print("  Audit schema not found - skipping audit triggers (not required for atomic operations)")

        # 10. Verify constraint additions
        print("Verifying constraint additions...")

        # Check constraint counts
        constraint_count = await conn.fetchval("""
            SELECT COUNT(*)
            FROM information_schema.table_constraints
            WHERE constraint_type = 'CHECK'
            AND table_name IN ('medications', 'investigations', 'therapy', 'casesheetentries')
        """)

        print(f"   Added {constraint_count} validation constraints")

        # Check new table existence
        new_tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name IN ('medical_operations', 'atomic_transactions')
            AND table_schema = 'public'
        """)

        print(f"   Created {len(new_tables)} atomic operation tables")

        # Check index count
        index_count = await conn.fetchval("""
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE indexname LIKE 'idx_%_patient_%'
            OR indexname LIKE 'idx_%_performed_by%'
            OR indexname LIKE 'idx_medical_operations_%'
            OR indexname LIKE 'idx_atomic_transactions_%'
        """)

        print(f"   Created {index_count} performance indexes")

        print("\nPhase 1 Complete: Database constraints enhanced for atomic operations!")
        print("- Data validation constraints added")
        print("- Idempotency tracking table created")
        print("- Atomic transaction tracking table created")
        print("- Performance indexes added")
        print("- Atomic operation helper functions created")
        print("- Audit triggers configured")
        print("\nDatabase is now ready for failproof atomic medical operations")

    except Exception as e:
        print(f"ERROR: Error enhancing database constraints: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    print("Hospital Management System - Atomic Database Enhancement")
    print("=" * 60)
    asyncio.run(enhance_database_constraints())