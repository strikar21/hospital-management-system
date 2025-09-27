#!/usr/bin/env python3
"""
Add MRN (Medical Record Number) column to patients table
Migration script to add human-readable patient identifiers
"""

import asyncio
import asyncpg
from datetime import datetime
import os
from app.core.config import settings

async def add_mrn_column():
    """Add MRN column to patients table and generate MRNs for existing patients"""

    # Database connection
    conn = await asyncpg.connect(
        host=settings.databaseHost,
        port=settings.databasePort,
        database=settings.databaseName,
        user=settings.databaseUser,
        password=settings.databasePassword
    )

    try:
        print("Adding MRN column to patients table...")

        # Add MRN column if it doesn't exist
        await conn.execute("""
            ALTER TABLE patients
            ADD COLUMN IF NOT EXISTS mrn VARCHAR(50) UNIQUE;
        """)

        print("MRN column added successfully")

        # Check if we have existing patients without MRNs
        existing_patients = await conn.fetch("""
            SELECT id, "firstName", "lastName", "createdAt"
            FROM patients
            WHERE mrn IS NULL
            ORDER BY "createdAt"
        """)

        if existing_patients:
            print(f"Generating MRNs for {len(existing_patients)} existing patients...")

            # Generate MRNs for existing patients
            year = datetime.now().year
            for i, patient in enumerate(existing_patients, 1):
                # Format: MRN-2025-000001
                mrn = f"MRN-{year}-{i:06d}"

                await conn.execute("""
                    UPDATE patients
                    SET mrn = $1
                    WHERE id = $2
                """, mrn, patient['id'])

                print(f"  Generated MRN {mrn} for {patient['firstName']} {patient['lastName']}")

            print(f"Generated MRNs for all {len(existing_patients)} existing patients")
        else:
            print("No existing patients found or all patients already have MRNs")

        # Create index on MRN for fast lookups
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_patients_mrn ON patients(mrn);
        """)

        print("Created index on MRN column")
        print("MRN migration completed successfully!")

    except Exception as e:
        print(f"Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(add_mrn_column())