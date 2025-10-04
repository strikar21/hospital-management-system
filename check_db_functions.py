#!/usr/bin/env python3
"""
Check if database functions exist
"""

import asyncio
import asyncpg

async def check_database_functions():
    conn = await asyncpg.connect("postgresql://hospital_user:hospital123@localhost:5432/hospitaldb")

    try:
        # Check if create_atomic_case_entry function exists
        functions = await conn.fetch("""
            SELECT
                proname as function_name,
                pg_get_function_arguments(p.oid) as arguments,
                pg_get_function_result(p.oid) as returns
            FROM pg_proc p
            LEFT JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname = 'public'
            AND proname LIKE '%case%'
        """)

        print(f"[INFO] Found {len(functions)} case-related functions:")
        for func in functions:
            print(f"  - {func['function_name']}({func['arguments']}) -> {func['returns']}")

        # Check case_entries table structure
        columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'caseEntries'
            ORDER BY ordinal_position
        """)

        print(f"\n[INFO] caseEntries table structure:")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']}")

        # Check if there are any case entries
        count = await conn.fetchval("SELECT COUNT(*) FROM \"caseEntries\"")
        print(f"\n[INFO] Total case entries in database: {count}")

        # Try to create a simple case entry to test
        print(f"\n[TEST] Testing manual case entry creation...")
        try:
            result = await conn.execute("""
                INSERT INTO "caseEntries" ("patientId", type, description, "performedBy", timestamp)
                VALUES ($1, $2, $3, $4, NOW())
                RETURNING id
            """, "6b851aa6-e564-40b6-963f-e1a5efdf024c", "medicationStatusChange", "Test medication status change", "DOC0001")
            print(f"[OK] Manual case entry creation works")
        except Exception as e:
            print(f"[ERROR] Manual case entry failed: {e}")

    except Exception as e:
        print(f"[ERROR] Database check failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_database_functions())