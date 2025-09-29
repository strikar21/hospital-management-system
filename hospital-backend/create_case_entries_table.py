#!/usr/bin/env python3
"""
Create caseEntries table with proper camelCase structure
Migration script for case sheet functionality
"""

import asyncio
import asyncpg
from datetime import datetime
import os
from app.core.config import settings

async def create_case_entries_table():
    """Create caseEntries table with camelCase columns"""

    # Database connection
    conn = await asyncpg.connect(
        host=settings.databaseHost,
        port=settings.databasePort,
        database=settings.databaseName,
        user=settings.databaseUser,
        password=settings.databasePassword
    )

    try:
        print("Creating caseEntries table with camelCase structure...")

        # Create the table with camelCase name and columns
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS "caseEntries" (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                "patientId" TEXT NOT NULL,
                "entryType" TEXT NOT NULL,
                description TEXT NOT NULL,
                findings TEXT,
                recommendations TEXT,
                "followUpDate" DATE,
                severity TEXT,
                category TEXT,
                "createdBy" TEXT NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                "deletedAt" TIMESTAMP WITH TIME ZONE,

                -- Foreign key constraint
                CONSTRAINT fk_case_entries_patient
                FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE
            );
        """)

        print("SUCCESS: caseEntries table created successfully")

        # Create indexes for performance
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS "idx_caseEntries_patientId"
            ON "caseEntries"("patientId");
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS "idx_caseEntries_timestamp"
            ON "caseEntries"(timestamp);
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS "idx_caseEntries_entryType"
            ON "caseEntries"("entryType");
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS "idx_caseEntries_createdAt"
            ON "caseEntries"("createdAt");
        """)

        print("SUCCESS: Indexes created successfully")

        # Add audit trigger for HIPAA compliance
        await conn.execute("""
            CREATE TRIGGER "caseEntries_audit_trigger"
            AFTER INSERT OR UPDATE OR DELETE ON "caseEntries"
            FOR EACH ROW EXECUTE FUNCTION audit.audit_trigger();
        """)

        print("SUCCESS: Audit trigger added successfully")

        # Check if we have existing patients to create sample case entries
        existing_patients = await conn.fetch("""
            SELECT id, "firstName", "lastName"
            FROM patients
            WHERE status = 'active'
            LIMIT 5
        """)

        if existing_patients:
            print(f"Found {len(existing_patients)} active patients")

            # Create sample case entries for existing patients
            for patient in existing_patients:
                patient_id = patient['id']
                patient_name = f"{patient['firstName']} {patient['lastName']}"

                # Admission case entry
                await conn.execute("""
                    INSERT INTO "caseEntries" (
                        "patientId", "entryType", description, "createdBy", timestamp
                    ) VALUES ($1, $2, $3, $4, $5)
                """,
                patient_id,
                'admission',
                f"Patient {patient_name} admitted to hospital",
                'SYSTEM',
                datetime.now()
                )

                print(f"  Created admission case entry for {patient_name}")

        print(f"SUCCESS: caseEntries table setup completed successfully!")
        print("Table structure:")
        print("   - id (UUID, Primary Key)")
        print("   - patientId (Foreign Key to patients)")
        print("   - entryType (medication, investigation, therapy, note, etc.)")
        print("   - description (Required)")
        print("   - findings (Optional)")
        print("   - recommendations (Optional)")
        print("   - followUpDate (Optional)")
        print("   - severity (Optional)")
        print("   - category (Optional)")
        print("   - createdBy (Required)")
        print("   - timestamp (Required)")
        print("   - createdAt, updatedAt, deletedAt (Audit fields)")
        print("All columns follow strict camelCase naming convention")

    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_case_entries_table())