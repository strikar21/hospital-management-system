"""
Apply deviceassignments migration to add unassignedBy and unassignmentReason fields
"""
import asyncio
import sys
import os

# Add parent directory to path to import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import getDbConnection

async def apply_migration():
    """Add missing fields to deviceassignments table"""
    try:
        async with getDbConnection() as conn:
            print("\n" + "="*80)
            print("APPLYING DEVICEASSIGNMENTS MIGRATION")
            print("="*80)

            # Add unassignedBy field
            print("\n1. Adding 'unassignedBy' field...")
            await conn.execute('ALTER TABLE deviceassignments ADD COLUMN IF NOT EXISTS "unassignedBy" TEXT')
            print("   [OK] unassignedBy field added")

            # Add unassignmentReason field
            print("\n2. Adding 'unassignmentReason' field...")
            await conn.execute('ALTER TABLE deviceassignments ADD COLUMN IF NOT EXISTS "unassignmentReason" TEXT')
            print("   [OK] unassignmentReason field added")

            # Verify columns were added
            print("\n3. Verifying fields...")
            result = await conn.fetch("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'deviceassignments'
                ORDER BY ordinal_position
            """)

            print(f"\n   deviceassignments table now has {len(result)} columns:")
            for row in result:
                nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
                print(f"     - {row['column_name']:<25} {row['data_type']:<20} {nullable}")

            # Check if our fields exist
            column_names = [row['column_name'] for row in result]
            if 'unassignedBy' in column_names and 'unassignmentReason' in column_names:
                print("\n" + "="*80)
                print("[SUCCESS] Migration completed successfully!")
                print("="*80 + "\n")
            else:
                print("\n" + "="*80)
                print("[ERROR] Migration failed - fields not found!")
                print("="*80 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(apply_migration())
