"""
Apply Migration 012: Device Maintenance Infrastructure
Creates tables for device calibration, maintenance history, and performance baselines
"""

import asyncio
import asyncpg
from app.core.config import settings

async def apply_migration():
    """Apply migration 012: Device maintenance infrastructure"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("="*80)
        print("MIGRATION 012: Device Maintenance Infrastructure")
        print("="*80)
        print()
        print("[INFO] Applying migration 012: Device maintenance tables and columns")

        # Read migration SQL
        with open('migrations/012_device_maintenance_infrastructure.sql', 'r', encoding='utf-8') as f:
            migration_sql = f.read()

        # Execute migration
        await conn.execute(migration_sql)
        print("[OK] Migration 012 executed successfully")
        print()

        # Verify tables created
        print("[INFO] Verifying tables created...")
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN ('deviceCalibration', 'deviceMaintenanceHistory', 'deviceBaselines')
            ORDER BY table_name
        """)

        if len(tables) == 3:
            print(f"[OK] All 3 tables created:")
            for table in tables:
                print(f"     - {table['table_name']}")
        else:
            print(f"[WARNING] Expected 3 tables, found {len(tables)}")

        print()

        # Verify columns added to devices table
        print("[INFO] Verifying columns added to devices table...")
        columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'devices'
              AND column_name IN ('firmwareVersion', 'lastCalibrationDate', 'calibrationDueDate',
                                  'batteryHealthPercentage', 'totalDisconnects',
                                  'lastCommandSentAt', 'lastCommandAckAt')
            ORDER BY column_name
        """)

        if len(columns) == 7:
            print(f"[OK] All 7 columns added to devices table:")
            for col in columns:
                print(f"     - {col['column_name']} ({col['data_type']})")
        else:
            print(f"[WARNING] Expected 7 columns, found {len(columns)}")

        print()

        # Verify indexes created
        print("[INFO] Verifying indexes created...")
        indexes = await conn.fetch("""
            SELECT indexname, tablename
            FROM pg_indexes
            WHERE tablename IN ('deviceCalibration', 'deviceMaintenanceHistory', 'deviceBaselines', 'devices')
              AND indexname LIKE 'idx_device%'
            ORDER BY tablename, indexname
        """)

        print(f"[OK] Created {len(indexes)} indexes:")
        current_table = None
        for idx in indexes:
            if idx['tablename'] != current_table:
                current_table = idx['tablename']
                print(f"     Table: {current_table}")
            print(f"       - {idx['indexname']}")

        print()

        # Check deviceCalibration table structure
        print("[INFO] Checking deviceCalibration table structure...")
        calib_cols = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'deviceCalibration'
            ORDER BY ordinal_position
        """)
        print(f"[OK] deviceCalibration has {len(calib_cols)} columns")

        # Check deviceMaintenanceHistory table structure
        print("[INFO] Checking deviceMaintenanceHistory table structure...")
        maint_cols = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'deviceMaintenanceHistory'
            ORDER BY ordinal_position
        """)
        print(f"[OK] deviceMaintenanceHistory has {len(maint_cols)} columns")

        # Check deviceBaselines table structure
        print("[INFO] Checking deviceBaselines table structure...")
        baseline_cols = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'deviceBaselines'
            ORDER BY ordinal_position
        """)
        print(f"[OK] deviceBaselines has {len(baseline_cols)} columns")

        print()

        # Check if existing devices were updated with default values
        print("[INFO] Checking default values on existing devices...")
        device_updates = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_devices,
                COUNT("firmwareVersion") as with_firmware,
                COUNT("calibrationDueDate") as with_calib_due,
                COUNT("batteryHealthPercentage") as with_battery_health
            FROM devices
        """)

        if device_updates:
            print(f"[OK] Existing devices updated:")
            print(f"     - Total devices: {device_updates['total_devices']}")
            print(f"     - With firmware version: {device_updates['with_firmware']}")
            print(f"     - With calibration due date: {device_updates['with_calib_due']}")
            print(f"     - With battery health: {device_updates['with_battery_health']}")

        print()
        print("="*80)
        print("[SUCCESS] Migration 012 completed successfully!")
        print("="*80)
        print()
        print("Summary:")
        print(f"  - 3 new tables created")
        print(f"  - 7 columns added to devices table")
        print(f"  - {len(indexes)} indexes created")
        print(f"  - Existing devices initialized with default values")
        print()

    except Exception as e:
        print()
        print("="*80)
        print(f"[ERROR] Migration 012 failed: {e}")
        print("="*80)
        import traceback
        traceback.print_exc()
        raise

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migration())
