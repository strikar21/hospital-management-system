"""
Run operational tables migration - Fix snake_case to camelCase
"""
import asyncio
import asyncpg

DATABASE_URL = "postgresql://hospital_user:hospital123@localhost:5432/hospitaldb"

async def run_migration():
    conn = await asyncpg.connect(DATABASE_URL)

    print("=" * 80)
    print("OPERATIONAL TABLES CAMELCASE MIGRATION")
    print("=" * 80)

    try:
        # Phase 1: Fix atomic_transactions
        print("\n[PHASE 1] Fixing atomic_transactions table...")

        await conn.execute('ALTER TABLE atomic_transactions RENAME COLUMN transaction_id TO "transactionId"')
        print("  - Renamed transaction_id -> transactionId")

        await conn.execute('ALTER TABLE atomic_transactions RENAME COLUMN patient_id TO "patientId"')
        print("  - Renamed patient_id -> patientId")

        await conn.execute('ALTER TABLE atomic_transactions RENAME COLUMN operation_type TO "operationType"')
        print("  - Renamed operation_type -> operationType")

        await conn.execute('ALTER TABLE atomic_transactions RENAME COLUMN operation_data TO "operationData"')
        print("  - Renamed operation_data -> operationData")

        await conn.execute('ALTER TABLE atomic_transactions RENAME COLUMN started_at TO "startedAt"')
        print("  - Renamed started_at -> startedAt")

        await conn.execute('ALTER TABLE atomic_transactions RENAME COLUMN completed_at TO "completedAt"')
        print("  - Renamed completed_at -> completedAt")

        await conn.execute('ALTER TABLE atomic_transactions RENAME COLUMN error_message TO "errorMessage"')
        print("  - Renamed error_message -> errorMessage")

        await conn.execute('ALTER TABLE atomic_transactions RENAME COLUMN retry_count TO "retryCount"')
        print("  - Renamed retry_count -> retryCount")

        print("\n[OK] atomic_transactions table fixed!")

        # Phase 2: Fix medical_operations
        print("\n[PHASE 2] Fixing medical_operations table...")

        await conn.execute('ALTER TABLE medical_operations RENAME COLUMN idempotency_key TO "idempotencyKey"')
        print("  - Renamed idempotency_key -> idempotencyKey")

        await conn.execute('ALTER TABLE medical_operations RENAME COLUMN operation_type TO "operationType"')
        print("  - Renamed operation_type -> operationType")

        await conn.execute('ALTER TABLE medical_operations RENAME COLUMN patient_id TO "patientId"')
        print("  - Renamed patient_id -> patientId")

        await conn.execute('ALTER TABLE medical_operations RENAME COLUMN created_at TO "createdAt"')
        print("  - Renamed created_at -> createdAt")

        await conn.execute('ALTER TABLE medical_operations RENAME COLUMN completed_at TO "completedAt"')
        print("  - Renamed completed_at -> completedAt")

        print("\n[OK] medical_operations table fixed!")

        # Phase 3: Verification
        print("\n[PHASE 3] Verifying changes...")

        print("\n  atomic_transactions columns:")
        columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'atomic_transactions'
            ORDER BY ordinal_position
        """)
        for col in columns:
            print(f"    - {col['column_name']}: {col['data_type']}")

        print("\n  medical_operations columns:")
        columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'medical_operations'
            ORDER BY ordinal_position
        """)
        for col in columns:
            print(f"    - {col['column_name']}: {col['data_type']}")

        print("\n" + "=" * 80)
        print("[SUCCESS] Migration completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        print("\nYou may need to rollback. See fix_operational_tables_camelcase.sql for rollback script.")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())
