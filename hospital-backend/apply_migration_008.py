"""
Apply Migration 008: Drop Redundant Device Assignment Fields

This script applies the migration that removes redundant device-patient
assignment fields from the database, leaving deviceassignments as the
single source of truth.
"""

import asyncio
import asyncpg
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration - matches hospital management system settings
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'hospitaldb',
    'user': 'hospital_user',
    'password': 'hospital123'
}

async def apply_migration():
    """Apply migration 008 to drop redundant device assignment fields"""

    # Read migration SQL file
    migration_file = Path(__file__).parent / 'migrations' / '008_drop_redundant_device_fields.sql'

    if not migration_file.exists():
        logger.error(f"❌ Migration file not found: {migration_file}")
        return False

    logger.info(f"📄 Reading migration file: {migration_file.name}")

    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()

    try:
        # Connect to database
        logger.info("🔌 Connecting to database...")
        conn = await asyncpg.connect(**DATABASE_CONFIG)

        logger.info("=" * 80)
        logger.info("APPLYING MIGRATION 008: Drop Redundant Device Assignment Fields")
        logger.info("=" * 80)

        # Execute migration
        logger.info("⚙️ Executing migration SQL...")
        await conn.execute(migration_sql)

        logger.info("=" * 80)
        logger.info("✅ MIGRATION 008 COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)

        # Verify the changes
        logger.info("\n🔍 Verifying schema changes...")

        # Check devices table
        devices_cols = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'devices'
            ORDER BY ordinal_position
        """)
        device_col_names = [row['column_name'] for row in devices_cols]

        logger.info(f"📋 Devices table columns: {', '.join(device_col_names)}")

        if 'assignedPatientId' in device_col_names:
            logger.warning("⚠️ WARNING: devices.assignedPatientId still exists!")
        else:
            logger.info("✓ Confirmed: devices.assignedPatientId removed")

        # Check patients table
        patients_cols = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'patients'
            ORDER BY ordinal_position
        """)
        patient_col_names = [row['column_name'] for row in patients_cols]

        logger.info(f"📋 Patients table columns: {', '.join(patient_col_names)}")

        if 'assignedDeviceId' in patient_col_names:
            logger.warning("⚠️ WARNING: patients.assignedDeviceId still exists!")
        else:
            logger.info("✓ Confirmed: patients.assignedDeviceId removed")

        # Check deviceassignments indices
        indices = await conn.fetch("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'deviceassignments'
            ORDER BY indexname
        """)
        index_names = [row['indexname'] for row in indices]

        logger.info(f"📋 Deviceassignments indices: {', '.join(index_names)}")

        if 'idx_deviceassignments_patient_active' in index_names:
            logger.info("✓ Confirmed: Patient index created")
        if 'idx_deviceassignments_device_active' in index_names:
            logger.info("✓ Confirmed: Device index created")

        # Count active assignments
        active_count = await conn.fetchval("""
            SELECT COUNT(*)
            FROM deviceassignments
            WHERE status = 'active'
        """)
        logger.info(f"📊 Active device assignments in deviceassignments table: {active_count}")

        await conn.close()
        logger.info("\n🎉 Migration 008 applied successfully!")
        logger.info("\n📌 Next steps:")
        logger.info("   1. Update database.py schema definition (Phase 4)")
        logger.info("   2. Run comprehensive tests (Phase 5)")
        logger.info("   3. If issues occur, run: python apply_rollback_008.py")

        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        logger.error(f"📋 Error details: {type(e).__name__}: {str(e)}")
        logger.info("\n🔄 To rollback, run: python apply_rollback_008.py")
        return False

async def main():
    """Main entry point"""
    success = await apply_migration()

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
