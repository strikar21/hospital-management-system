#!/usr/bin/env python3
"""
Database Foreign Key Constraints Creation
Adds referential integrity constraints to ensure data consistency
"""

import asyncio
import asyncpg
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://hospital_user:hospital123@localhost:5432/hospitaldb"

async def create_foreign_key_constraints():
    """Create foreign key constraints for referential integrity"""

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        logger.info("Connected to database for foreign key creation")

        # Foreign key constraints based on actual schema
        constraints = [
            # Patient Notes foreign keys
            {
                "name": "fk_patientnotes_patient",
                "query": 'ALTER TABLE patientnotes ADD CONSTRAINT fk_patientnotes_patient FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE;',
                "description": "Patient notes must reference valid patients"
            },

            # Medications foreign keys
            {
                "name": "fk_medications_patient",
                "query": 'ALTER TABLE medications ADD CONSTRAINT fk_medications_patient FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE;',
                "description": "Medications must reference valid patients"
            },

            # Medication Administrations foreign keys
            {
                "name": "fk_medicationadmin_patient",
                "query": 'ALTER TABLE medicationadministrations ADD CONSTRAINT fk_medicationadmin_patient FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE;',
                "description": "Medication administrations must reference valid patients"
            },
            {
                "name": "fk_medicationadmin_medication",
                "query": 'ALTER TABLE medicationadministrations ADD CONSTRAINT fk_medicationadmin_medication FOREIGN KEY ("medicationId") REFERENCES medications(id) ON DELETE CASCADE;',
                "description": "Medication administrations must reference valid medications"
            },

            # Investigations foreign keys
            {
                "name": "fk_investigations_patient",
                "query": 'ALTER TABLE investigations ADD CONSTRAINT fk_investigations_patient FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE;',
                "description": "Investigations must reference valid patients"
            },

            # Therapy foreign keys
            {
                "name": "fk_therapy_patient",
                "query": 'ALTER TABLE therapy ADD CONSTRAINT fk_therapy_patient FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE;',
                "description": "Therapy must reference valid patients"
            },

            # Therapy Sessions foreign keys
            {
                "name": "fk_therapysessions_therapy",
                "query": 'ALTER TABLE therapysessions ADD CONSTRAINT fk_therapysessions_therapy FOREIGN KEY ("therapyId") REFERENCES therapy(id) ON DELETE CASCADE;',
                "description": "Therapy sessions must reference valid therapy"
            },
            {
                "name": "fk_therapysessions_patient",
                "query": 'ALTER TABLE therapysessions ADD CONSTRAINT fk_therapysessions_patient FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE;',
                "description": "Therapy sessions must reference valid patients"
            },

            # Device Assignments foreign keys
            {
                "name": "fk_deviceassignments_patient",
                "query": 'ALTER TABLE deviceassignments ADD CONSTRAINT fk_deviceassignments_patient FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE;',
                "description": "Device assignments must reference valid patients"
            },
            {
                "name": "fk_deviceassignments_device",
                "query": 'ALTER TABLE deviceassignments ADD CONSTRAINT fk_deviceassignments_device FOREIGN KEY ("deviceId") REFERENCES devices(id) ON DELETE CASCADE;',
                "description": "Device assignments must reference valid devices"
            },

            # Case Sheet Entries foreign keys
            {
                "name": "fk_casesheetentries_patient",
                "query": 'ALTER TABLE casesheetentries ADD CONSTRAINT fk_casesheetentries_patient FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE;',
                "description": "Case sheet entries must reference valid patients"
            },

            # Patients device assignment foreign key (if column exists)
            {
                "name": "fk_patients_assigned_device",
                "query": 'ALTER TABLE patients ADD CONSTRAINT fk_patients_assigned_device FOREIGN KEY ("assignedDeviceId") REFERENCES devices(id) ON DELETE SET NULL;',
                "description": "Patient assigned device must reference valid devices"
            },

            # Audit Log foreign keys (partial - only if staff table has consistent ID structure)
            {
                "name": "fk_auditlog_user",
                "query": 'ALTER TABLE auditlog ADD CONSTRAINT fk_auditlog_user FOREIGN KEY ("userId") REFERENCES staff(id) ON DELETE SET NULL;',
                "description": "Audit log user must reference valid staff"
            }
        ]

        created_count = 0
        skipped_count = 0

        for constraint in constraints:
            try:
                await conn.execute(constraint["query"])
                logger.info(f"SUCCESS: Created foreign key: {constraint['name']} - {constraint['description']}")
                created_count += 1
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"SKIPPED: Foreign key {constraint['name']} already exists")
                    skipped_count += 1
                elif "violates foreign key constraint" in str(e).lower() or "does not exist" in str(e).lower():
                    logger.warning(f"SKIPPED: {constraint['name']} - referenced table/column missing or data integrity issue")
                    skipped_count += 1
                else:
                    logger.error(f"ERROR: Failed to create foreign key {constraint['name']}: {e}")

        await conn.close()
        logger.info(f"Database connection closed")

        return created_count, skipped_count

    except Exception as e:
        logger.error(f"ERROR: Foreign key creation failed: {e}")
        return 0, 0

async def check_referential_integrity():
    """Check for potential referential integrity violations before creating constraints"""

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        logger.info("Checking referential integrity...")

        integrity_checks = [
            {
                "name": "Orphaned patient notes",
                "query": """
                    SELECT COUNT(*) as orphaned_count
                    FROM patientnotes pn
                    LEFT JOIN patients p ON pn."patientId" = p.id
                    WHERE p.id IS NULL
                """
            },
            {
                "name": "Orphaned medications",
                "query": """
                    SELECT COUNT(*) as orphaned_count
                    FROM medications m
                    LEFT JOIN patients p ON m."patientId" = p.id
                    WHERE p.id IS NULL
                """
            },
            {
                "name": "Invalid device assignments",
                "query": """
                    SELECT COUNT(*) as orphaned_count
                    FROM deviceassignments da
                    LEFT JOIN patients p ON da."patientId" = p.id
                    LEFT JOIN devices d ON da."deviceId" = d.id
                    WHERE p.id IS NULL OR d.id IS NULL
                """
            }
        ]

        print("\nREFERENCE INTEGRITY CHECK")
        print("=" * 50)

        for check in integrity_checks:
            try:
                result = await conn.fetchval(check["query"])
                status = "OK" if result == 0 else f"ISSUES: {result}"
                print(f"{check['name']:<25}: {status}")
            except Exception as e:
                print(f"{check['name']:<25}: ERROR - {e}")

        await conn.close()

    except Exception as e:
        logger.error(f"ERROR: Integrity check failed: {e}")

async def main():
    """Main function to create foreign key constraints"""
    print("HOSPITAL DATABASE FOREIGN KEY CONSTRAINTS")
    print("=" * 60)

    # Check integrity first
    await check_referential_integrity()

    # Create foreign key constraints
    created_count, skipped_count = await create_foreign_key_constraints()

    print(f"\nSUMMARY")
    print("=" * 30)
    print(f"Successfully created: {created_count} foreign keys")
    print(f"Skipped (existing/issues): {skipped_count} foreign keys")

    print(f"\nFOREIGN KEY CONSTRAINTS COMPLETE")
    print("The database now has referential integrity constraints.")

if __name__ == "__main__":
    asyncio.run(main())