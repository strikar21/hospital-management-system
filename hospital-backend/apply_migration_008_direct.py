"""
Apply Migration 008: Drop Redundant Device Assignment Fields (Direct Method)

This script applies the migration using direct SQL commands that work with asyncpg.
"""

import asyncio
import asyncpg
import logging
import sys

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

    try:
        # Connect to database
        logger.info("🔌 Connecting to database...")
        conn = await asyncpg.connect(**DATABASE_CONFIG)

        logger.info("=" * 80)
        logger.info("APPLYING MIGRATION 008: Drop Redundant Device Assignment Fields")
        logger.info("=" * 80)

        # Step 1: Check data consistency before migration
        logger.info("\n🔍 STEP 1: Checking data consistency...")

        inconsistent_devices = await conn.fetch("""
            SELECT COUNT(*) as count
            FROM devices d
            LEFT JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
            WHERE d."assignedPatientId" IS DISTINCT FROM da."patientId"
        """)
        device_inconsistency_count = inconsistent_devices[0]['count']

        inconsistent_patients = await conn.fetch("""
            SELECT COUNT(*) as count
            FROM patients p
            LEFT JOIN deviceassignments da ON p.id = da."patientId" AND da.status = 'active'
            WHERE p."assignedDeviceId" IS DISTINCT FROM da."deviceId"
        """)
        patient_inconsistency_count = inconsistent_patients[0]['count']

        if device_inconsistency_count > 0:
            logger.warning(f"⚠️ Found {device_inconsistency_count} devices with inconsistent assignedPatientId")
        else:
            logger.info("✓ All devices.assignedPatientId values are consistent")

        if patient_inconsistency_count > 0:
            logger.warning(f"⚠️ Found {patient_inconsistency_count} patients with inconsistent assignedDeviceId")
        else:
            logger.info("✓ All patients.assignedDeviceId values are consistent")

        # Step 2: Drop devices.assignedPatientId column
        logger.info("\n🔧 STEP 2: Dropping devices.assignedPatientId column...")

        # Check if column exists
        devices_col_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'devices' AND column_name = 'assignedPatientId'
            )
        """)

        if devices_col_exists:
            await conn.execute('ALTER TABLE devices DROP COLUMN "assignedPatientId"')
            logger.info("✓ Dropped column devices.assignedPatientId")
        else:
            logger.info("⊘ Column devices.assignedPatientId does not exist (already dropped)")

        # Step 3: Drop patients.assignedDeviceId column
        logger.info("\n🔧 STEP 3: Dropping patients.assignedDeviceId column...")

        # Check if column exists
        patients_col_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'patients' AND column_name = 'assignedDeviceId'
            )
        """)

        if patients_col_exists:
            await conn.execute('ALTER TABLE patients DROP COLUMN "assignedDeviceId"')
            logger.info("✓ Dropped column patients.assignedDeviceId")
        else:
            logger.info("⊘ Column patients.assignedDeviceId does not exist (already dropped)")

        # Step 4: Create performance indices
        logger.info("\n⚡ STEP 4: Creating performance indices...")

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_deviceassignments_patient_active
                ON deviceassignments("patientId")
                WHERE status = 'active'
        """)
        logger.info("✓ Created index idx_deviceassignments_patient_active")

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_deviceassignments_device_active
                ON deviceassignments("deviceId")
                WHERE status = 'active'
        """)
        logger.info("✓ Created index idx_deviceassignments_device_active")

        # Step 5: Verify migration
        logger.info("\n🔍 STEP 5: Verifying migration...")

        # Check devices table
        devices_cols = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'devices'
            ORDER BY ordinal_position
        """)
        device_col_names = [row['column_name'] for row in devices_cols]

        if 'assignedPatientId' in device_col_names:
            logger.error("❌ ERROR: devices.assignedPatientId still exists!")
            await conn.close()
            return False
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

        if 'assignedDeviceId' in patient_col_names:
            logger.error("❌ ERROR: patients.assignedDeviceId still exists!")
            await conn.close()
            return False
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
        logger.info(f"✓ Active device assignments: {active_count}")

        await conn.close()

        logger.info("=" * 80)
        logger.info("✅ MIGRATION 008 COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
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
