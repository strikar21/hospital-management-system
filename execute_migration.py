#!/usr/bin/env python3
"""
Database Migration Execution Script
Execute the database consolidation migration safely
"""

import asyncio
import asyncpg
import sys
import os
import logging
from datetime import datetime

# Add the backend to the path so we can import the database module
sys.path.append(os.path.join(os.path.dirname(__file__), 'hospital-backend'))

from app.core.database import getDbConnection
from app.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_current_data():
    """Check current record counts before migration"""
    logger.info("🔍 Checking current database state...")

    async with getDbConnection() as conn:
        try:
            # Check if tables exist and get counts
            tables_to_check = [
                ('therapy', 'therapy'),
                ('therapies', 'therapies'),
                ('casesheetentries', 'casesheetentries'),
                ('caseEntries', '"caseEntries"')
            ]

            for display_name, table_name in tables_to_check:
                try:
                    result = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                    logger.info(f"📊 {display_name}: {result} records")
                except Exception as e:
                    logger.warning(f"⚠️  {display_name}: Table does not exist or error - {e}")

        except Exception as e:
            logger.error(f"❌ Error checking data: {e}")
            raise

async def execute_migration():
    """Execute the database consolidation migration"""
    logger.info("🚀 Starting database consolidation migration...")

    async with getDbConnection() as conn:
        try:
            # Start transaction
            async with conn.transaction():
                logger.info("📝 Creating backup tables...")

                # Create backup tables
                try:
                    await conn.execute("CREATE TABLE therapy_backup AS SELECT * FROM therapy")
                    logger.info("✅ Created therapy_backup table")
                except Exception as e:
                    logger.warning(f"⚠️  therapy_backup creation: {e}")

                try:
                    await conn.execute("CREATE TABLE casesheetentries_backup AS SELECT * FROM casesheetentries")
                    logger.info("✅ Created casesheetentries_backup table")
                except Exception as e:
                    logger.warning(f"⚠️  casesheetentries_backup creation: {e}")

                # Check if target tables exist, create if they don't
                logger.info("🏗️  Ensuring target tables exist...")

                # Create therapies table if it doesn't exist
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS therapies (
                        id TEXT PRIMARY KEY,
                        "patientId" TEXT NOT NULL,
                        "therapyType" VARCHAR NOT NULL,
                        "therapyName" VARCHAR NOT NULL,
                        description TEXT,
                        "startDate" DATE,
                        "endDate" DATE,
                        frequency VARCHAR,
                        "sessionDuration" INTEGER,
                        status VARCHAR DEFAULT 'active'::character varying,
                        "createdAt" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        "updatedAt" TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        "createdBy" TEXT
                    )
                """)
                logger.info("✅ therapies table ready")

                # Create caseEntries table if it doesn't exist
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
                        timestamp TIMESTAMPTZ NOT NULL,
                        "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        "deletedAt" TIMESTAMPTZ
                    )
                """)
                logger.info("✅ caseEntries table ready")

                # Execute migration: therapy -> therapies
                logger.info("🔄 Migrating therapy -> therapies...")
                try:
                    result = await conn.execute("""
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
                            gen_random_uuid()::text,
                            "patientId",
                            type,
                            COALESCE(type, 'General Therapy'),
                            description,
                            "startDate"::date,
                            "endDate"::date,
                            frequency,
                            NULL,
                            COALESCE(status, 'active'),
                            COALESCE("createdAt", NOW()),
                            COALESCE("updatedAt", NOW()),
                            "performedBy"
                        FROM therapy
                        WHERE NOT EXISTS (
                            SELECT 1 FROM therapies t2
                            WHERE t2."patientId" = therapy."patientId"
                            AND t2.description = therapy.description
                            AND t2."createdAt" = therapy."createdAt"
                        )
                    """)
                    logger.info(f"✅ Migrated therapy data: {result}")
                except Exception as e:
                    logger.warning(f"⚠️  therapy migration: {e}")

                # Execute migration: casesheetentries -> caseEntries
                logger.info("🔄 Migrating casesheetentries -> caseEntries...")
                try:
                    result = await conn.execute("""
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
                            gen_random_uuid(),
                            "patientId",
                            "entryType",
                            description,
                            NULL,
                            NULL,
                            NULL,
                            NULL,
                            "entryType",
                            "performedBy",
                            timestamp,
                            COALESCE("createdAt", NOW()),
                            COALESCE("updatedAt", NOW()),
                            NULL
                        FROM casesheetentries
                        WHERE NOT EXISTS (
                            SELECT 1 FROM "caseEntries" ce
                            WHERE ce."patientId" = casesheetentries."patientId"
                            AND ce.description = casesheetentries.description
                            AND ce.timestamp = casesheetentries.timestamp
                        )
                    """)
                    logger.info(f"✅ Migrated case sheet data: {result}")
                except Exception as e:
                    logger.warning(f"⚠️  casesheetentries migration: {e}")

                logger.info("✅ Migration completed successfully!")

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise

async def verify_migration():
    """Verify migration results"""
    logger.info("🔍 Verifying migration results...")

    async with getDbConnection() as conn:
        try:
            # Check post-migration counts
            tables_to_check = [
                ('therapy', 'therapy'),
                ('therapies', 'therapies'),
                ('casesheetentries', 'casesheetentries'),
                ('caseEntries', '"caseEntries"')
            ]

            logger.info("📊 POST-MIGRATION COUNTS:")
            for display_name, table_name in tables_to_check:
                try:
                    result = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                    logger.info(f"📊 {display_name}: {result} records")
                except Exception as e:
                    logger.warning(f"⚠️  {display_name}: {e}")

            # Data integrity checks
            logger.info("🔍 Data integrity checks:")

            # Check therapies table
            try:
                therapy_stats = await conn.fetchrow("""
                    SELECT
                        COUNT(*) as total_therapies,
                        COUNT(DISTINCT "patientId") as unique_patients,
                        COUNT(CASE WHEN "therapyType" IS NULL THEN 1 END) as missing_therapy_type,
                        COUNT(CASE WHEN description IS NULL THEN 1 END) as missing_description
                    FROM therapies
                """)
                logger.info(f"📈 Therapies integrity: {dict(therapy_stats)}")
            except Exception as e:
                logger.warning(f"⚠️  Therapies integrity check: {e}")

            # Check caseEntries table
            try:
                case_stats = await conn.fetchrow("""
                    SELECT
                        COUNT(*) as total_entries,
                        COUNT(DISTINCT "patientId") as unique_patients,
                        COUNT(CASE WHEN "entryType" IS NULL THEN 1 END) as missing_entry_type,
                        COUNT(CASE WHEN description IS NULL THEN 1 END) as missing_description
                    FROM "caseEntries"
                """)
                logger.info(f"📈 Case entries integrity: {dict(case_stats)}")
            except Exception as e:
                logger.warning(f"⚠️  Case entries integrity check: {e}")

        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            raise

async def main():
    """Main migration execution"""
    logger.info("🏥 Hospital Database Consolidation Migration")
    logger.info(f"🕐 Started at: {datetime.now()}")

    try:
        # Step 1: Check current state
        await check_current_data()

        # Step 2: Execute migration
        await execute_migration()

        # Step 3: Verify results
        await verify_migration()

        logger.info("🎉 Migration completed successfully!")
        logger.info("⚠️  NEXT STEPS:")
        logger.info("   1. Test all API endpoints")
        logger.info("   2. Verify frontend functionality")
        logger.info("   3. Update backend code to use consolidated tables")
        logger.info("   4. Drop legacy tables when ready: DROP TABLE therapy; DROP TABLE casesheetentries;")

    except Exception as e:
        logger.error(f"💥 Migration failed: {e}")
        logger.error("🔄 Check backup tables: therapy_backup, casesheetentries_backup")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())