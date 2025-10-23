"""
Rollback Migration 008: Restore Redundant Device Assignment Fields

This script rolls back migration 008, restoring the redundant columns
devices.assignedPatientId and patients.assignedDeviceId.

WARNING: The application code has been updated to NOT use these fields.
If you rollback this migration, you may also need to rollback code changes.
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

async def rollback_migration():
    """Rollback migration 008 to restore redundant device assignment fields"""

    # Read rollback SQL file
    rollback_file = Path(__file__).parent / 'migrations' / '008_rollback.sql'

    if not rollback_file.exists():
        logger.error(f"❌ Rollback file not found: {rollback_file}")
        return False

    logger.info(f"📄 Reading rollback file: {rollback_file.name}")

    with open(rollback_file, 'r', encoding='utf-8') as f:
        rollback_sql = f.read()

    try:
        # Connect to database
        logger.info("🔌 Connecting to database...")
        conn = await asyncpg.connect(**DATABASE_CONFIG)

        logger.info("=" * 80)
        logger.info("ROLLING BACK MIGRATION 008: Restore Redundant Fields")
        logger.info("=" * 80)
        logger.warning("⚠️ WARNING: Application code has been updated to use JOINs")
        logger.warning("⚠️ The restored fields will NOT be maintained by current code")

        # Execute rollback
        logger.info("⚙️ Executing rollback SQL...")
        await conn.execute(rollback_sql)

        logger.info("=" * 80)
        logger.info("✅ ROLLBACK 008 COMPLETED")
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

        if 'assignedPatientId' in device_col_names:
            logger.info("✓ Confirmed: devices.assignedPatientId restored")

            # Check population
            populated_devices = await conn.fetchval("""
                SELECT COUNT(*) FROM devices WHERE "assignedPatientId" IS NOT NULL
            """)
            logger.info(f"   → {populated_devices} devices have assignedPatientId populated")
        else:
            logger.warning("⚠️ WARNING: devices.assignedPatientId NOT restored!")

        # Check patients table
        patients_cols = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'patients'
            ORDER BY ordinal_position
        """)
        patient_col_names = [row['column_name'] for row in patients_cols]

        if 'assignedDeviceId' in patient_col_names:
            logger.info("✓ Confirmed: patients.assignedDeviceId restored")

            # Check population
            populated_patients = await conn.fetchval("""
                SELECT COUNT(*) FROM patients WHERE "assignedDeviceId" IS NOT NULL
            """)
            logger.info(f"   → {populated_patients} patients have assignedDeviceId populated")
        else:
            logger.warning("⚠️ WARNING: patients.assignedDeviceId NOT restored!")

        # Check consistency
        logger.info("\n🔍 Checking data consistency...")

        inconsistent_devices = await conn.fetch("""
            SELECT d.id, d."assignedPatientId" as device_says, da."patientId" as deviceassignments_says
            FROM devices d
            LEFT JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
            WHERE d."assignedPatientId" IS DISTINCT FROM da."patientId"
            LIMIT 5
        """)

        if inconsistent_devices:
            logger.warning(f"⚠️ Found {len(inconsistent_devices)} devices with inconsistent data:")
            for row in inconsistent_devices[:3]:
                logger.warning(f"   Device {row['id']}: device field={row['device_says']}, deviceassignments={row['deviceassignments_says']}")
        else:
            logger.info("✓ All devices are consistent with deviceassignments")

        await conn.close()

        logger.info("\n🔄 Rollback 008 completed")
        logger.info("\n⚠️ IMPORTANT REMINDERS:")
        logger.info("   1. Application code uses JOINs and does NOT write to these fields")
        logger.info("   2. New assignments will NOT update these redundant fields")
        logger.info("   3. Consider whether code rollback is also needed")
        logger.info("   4. To re-apply migration: python apply_migration_008.py")

        return True

    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        logger.error(f"📋 Error details: {type(e).__name__}: {str(e)}")
        return False

async def main():
    """Main entry point"""
    logger.info("🚨 You are about to rollback migration 008")
    logger.info("   This will restore redundant device assignment fields")
    logger.info("")

    # In a real scenario, you might want to add a confirmation prompt here
    # For now, we'll proceed directly
    success = await rollback_migration()

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
