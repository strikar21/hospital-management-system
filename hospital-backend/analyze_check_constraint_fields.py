"""
Analyze fields that need CHECK constraints
Look at actual data to determine valid values and validation rules
"""
import asyncio
import asyncpg
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.core.config import settings


async def analyze_table(conn, table_name, fields_to_check):
    """Analyze specific fields in a table"""
    print(f"\n{'=' * 60}")
    print(f"{table_name.upper()} TABLE")
    print('=' * 60)

    # Get row count
    row_count = await conn.fetchval(f'SELECT COUNT(*) FROM {table_name}')
    print(f"\nTotal Records: {row_count}")

    if row_count == 0:
        print("  [INFO] No data to analyze (table is empty)")
        return

    for field_info in fields_to_check:
        field_name = field_info['name']
        field_type = field_info.get('type', 'enum')  # enum, date_range, etc.

        print(f"\n--- {field_name} ({field_type}) ---")

        if field_type == 'enum':
            # Get distinct values
            distinct_values = await conn.fetch(f"""
                SELECT DISTINCT "{field_name}", COUNT(*) as count
                FROM {table_name}
                WHERE "{field_name}" IS NOT NULL
                GROUP BY "{field_name}"
                ORDER BY count DESC
            """)

            if distinct_values:
                print(f"  Distinct values ({len(distinct_values)}):")
                for row in distinct_values:
                    print(f"    - '{row[field_name]}' ({row['count']} records)")
            else:
                print("  No non-NULL values found")

            # Check for NULL values
            null_count = await conn.fetchval(f"""
                SELECT COUNT(*)
                FROM {table_name}
                WHERE "{field_name}" IS NULL
            """)
            if null_count > 0:
                print(f"  NULL values: {null_count} records")

        elif field_type == 'date_range':
            # Analyze date ranges
            start_field = field_info['start']
            end_field = field_info['end']

            # Check for invalid date ranges (end before start)
            invalid_ranges = await conn.fetchval(f"""
                SELECT COUNT(*)
                FROM {table_name}
                WHERE "{end_field}" IS NOT NULL
                AND "{start_field}" IS NOT NULL
                AND "{end_field}" < "{start_field}"
            """)

            print(f"  Start: {start_field}, End: {end_field}")
            print(f"  Invalid ranges (end < start): {invalid_ranges} records")

            # Sample data
            samples = await conn.fetch(f"""
                SELECT "{start_field}", "{end_field}"
                FROM {table_name}
                WHERE "{start_field}" IS NOT NULL
                OR "{end_field}" IS NOT NULL
                LIMIT 3
            """)

            if samples:
                print(f"  Sample date ranges:")
                for row in samples:
                    start = row[start_field] or 'NULL'
                    end = row[end_field] or 'NULL'
                    print(f"    {start} -> {end}")


async def analyze_all_tables():
    """Analyze all tables for CHECK constraint candidates"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("=" * 60)
        print("CHECK CONSTRAINT ANALYSIS")
        print("=" * 60)

        # MEDICATIONS table
        await analyze_table(conn, 'medications', [
            {'name': 'status', 'type': 'enum'},
            {'name': 'route', 'type': 'enum'},
            {'name': 'frequency', 'type': 'enum'},
            {'name': 'startDate', 'type': 'date_range', 'start': 'startDate', 'end': 'endDate'},
        ])

        # INVESTIGATIONS table
        await analyze_table(conn, 'investigations', [
            {'name': 'status', 'type': 'enum'},
            {'name': 'type', 'type': 'enum'},
            {'name': 'priority', 'type': 'enum'},
            {'name': 'urgency', 'type': 'enum'},
        ])

        # THERAPY table
        await analyze_table(conn, 'therapy', [
            {'name': 'status', 'type': 'enum'},
            {'name': 'type', 'type': 'enum'},
            {'name': 'frequency', 'type': 'enum'},
            {'name': 'startDate', 'type': 'date_range', 'start': 'startDate', 'end': 'endDate'},
        ])

        # CASESHEETENTRIES table
        await analyze_table(conn, 'casesheetentries', [
            {'name': 'entryType', 'type': 'enum'},
        ])

        # PATIENTS table
        await analyze_table(conn, 'patients', [
            {'name': 'status', 'type': 'enum'},
            {'name': 'gender', 'type': 'enum'},
        ])

        # STAFF table
        await analyze_table(conn, 'staff', [
            {'name': 'role', 'type': 'enum'},
        ])

        print("\n" + "=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(analyze_all_tables())
