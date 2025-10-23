"""
Check actual deviceassignments table schema in running database
"""
import asyncio
import sys
import os

# Add parent directory to path to import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import getDbConnection

async def check_schema():
    """Check deviceassignments table columns"""
    try:
        async with getDbConnection() as conn:
            # Get all columns for deviceassignments table
            query = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'deviceassignments'
            ORDER BY ordinal_position;
            """

            columns = await conn.fetch(query)

            print("\n" + "="*80)
            print("DEVICEASSIGNMENTS TABLE SCHEMA (Actual Database)")
            print("="*80)

            if not columns:
                print("[ERROR] Table 'deviceassignments' does not exist!")
            else:
                print(f"Found {len(columns)} columns:\n")
                for col in columns:
                    nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                    default = f"DEFAULT {col['column_default']}" if col['column_default'] else ""
                    print(f"  - {col['column_name']:<20} {col['data_type']:<20} {nullable:<10} {default}")

            print("\n" + "="*80)
            print("CHECKING FOR MISSING FIELDS")
            print("="*80)

            column_names = [col['column_name'] for col in columns]

            # Check fields that code tries to use
            expected_fields = ['unassignedBy', 'unassignmentReason']

            for field in expected_fields:
                if field in column_names:
                    print(f"  [OK] {field}: EXISTS")
                else:
                    print(f"  [MISSING] {field}: Code tries to use it but field doesn't exist!")

            print("\n" + "="*80)

    except Exception as e:
        print(f"[ERROR] Error checking schema: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_schema())
