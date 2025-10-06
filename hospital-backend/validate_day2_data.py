"""
Validate data quality for Day 2 FK constraints
Check if all staff IDs and patient IDs are valid
"""
import asyncio
import asyncpg
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.core.config import settings


async def validate_fk_data(conn, table_name, column_name, ref_table, ref_column='id'):
    """Validate FK column data against reference table"""
    print(f"\nValidating {table_name}.{column_name} -> {ref_table}({ref_column}):")

    # Get invalid values
    invalid_query = f"""
        SELECT DISTINCT "{column_name}" as invalid_value, COUNT(*) as count
        FROM {table_name}
        WHERE "{column_name}" IS NOT NULL
        AND "{column_name}" NOT IN (SELECT {ref_column} FROM {ref_table})
        GROUP BY "{column_name}"
    """

    invalid_values = await conn.fetch(invalid_query)

    if invalid_values:
        print(f"  [FAIL] Found {len(invalid_values)} invalid values:")
        for row in invalid_values:
            print(f"    - '{row['invalid_value']}' ({row['count']} records)")
        return False
    else:
        # Get total count of non-null values
        total = await conn.fetchval(f"""
            SELECT COUNT(*)
            FROM {table_name}
            WHERE "{column_name}" IS NOT NULL
        """)
        print(f"  [PASS] All {total} values are valid")
        return True


async def validate_all_data():
    """Validate all Day 2 FK constraints"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("=" * 60)
        print("DAY 2 DATA QUALITY VALIDATION")
        print("=" * 60)

        all_valid = True

        # INVESTIGATIONS table
        print("\n--- INVESTIGATIONS TABLE ---")

        # patientId (already has FK, but let's verify)
        result = await validate_fk_data(conn, 'investigations', 'patientId', 'patients')
        all_valid = all_valid and result

        # prescribedBy -> staff
        result = await validate_fk_data(conn, 'investigations', 'prescribedBy', 'staff')
        all_valid = all_valid and result

        # performedBy -> staff
        result = await validate_fk_data(conn, 'investigations', 'performedBy', 'staff')
        all_valid = all_valid and result

        # THERAPY table
        print("\n--- THERAPY TABLE ---")

        # patientId -> patients
        result = await validate_fk_data(conn, 'therapy', 'patientId', 'patients')
        all_valid = all_valid and result

        # prescribedBy -> staff
        result = await validate_fk_data(conn, 'therapy', 'prescribedBy', 'staff')
        all_valid = all_valid and result

        # CASESHEETENTRIES table
        print("\n--- CASESHEETENTRIES TABLE ---")

        # Check if table has any data
        row_count = await conn.fetchval('SELECT COUNT(*) FROM casesheetentries')
        print(f"\n  Total records: {row_count}")

        if row_count > 0:
            # patientId -> patients
            result = await validate_fk_data(conn, 'casesheetentries', 'patientId', 'patients')
            all_valid = all_valid and result

            # createdBy -> staff
            result = await validate_fk_data(conn, 'casesheetentries', 'createdBy', 'staff')
            all_valid = all_valid and result

            # performedBy -> staff
            result = await validate_fk_data(conn, 'casesheetentries', 'performedBy', 'staff')
            all_valid = all_valid and result
        else:
            print("  [INFO] No data to validate (table is empty)")

        # Summary
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)

        if all_valid:
            print("\n[SUCCESS] All data is valid for FK constraints!")
            print("Safe to proceed with FK constraint migrations.")
        else:
            print("\n[FAIL] Data quality issues found!")
            print("Need data cleanup before applying FK constraints.")

        print("\n" + "=" * 60)

        return all_valid

    finally:
        await conn.close()


if __name__ == "__main__":
    success = asyncio.run(validate_all_data())
    sys.exit(0 if success else 1)
