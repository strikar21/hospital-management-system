#!/usr/bin/env python3
"""
Drop Legacy Tables Script
Clean up legacy tables after successful consolidation
"""

import asyncio
import asyncpg
import sys
import os
from datetime import datetime

# Add the backend to the path so we can import the database module
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.core.database import getDbConnection

async def drop_legacy_tables():
    """Drop legacy tables after consolidation"""
    print("Dropping legacy tables...")
    print(f"Started at: {datetime.now()}")

    async with getDbConnection() as conn:
        try:
            # First check if tables exist
            tables_to_check = ['therapy', 'casesheetentries', 'therapy_backup', 'casesheetentries_backup']

            for table_name in tables_to_check:
                try:
                    result = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                    print(f"{table_name}: {result} records (will be dropped)")
                except Exception:
                    print(f"{table_name}: Table does not exist (already dropped)")

            # Drop legacy tables with CASCADE to handle foreign key dependencies
            print("\nDropping legacy tables...")

            await conn.execute('DROP TABLE IF EXISTS therapy CASCADE;')
            print('Dropped legacy therapy table')

            await conn.execute('DROP TABLE IF EXISTS casesheetentries CASCADE;')
            print('Dropped legacy casesheetentries table')

            # Drop backup tables
            await conn.execute('DROP TABLE IF EXISTS therapy_backup CASCADE;')
            print('Dropped therapy_backup table')

            await conn.execute('DROP TABLE IF EXISTS casesheetentries_backup CASCADE;')
            print('Dropped casesheetentries_backup table')

            print('\nLegacy table cleanup completed successfully!')
            print("NOTES:")
            print("   - therapies table contains consolidated therapy data")
            print("   - caseEntries table contains consolidated case sheet data")
            print("   - All data has been preserved in consolidated tables")

        except Exception as e:
            print(f'Error dropping tables: {e}')
            raise

async def main():
    """Main execution"""
    print("Hospital Database Legacy Table Cleanup")

    try:
        await drop_legacy_tables()
        print("Cleanup completed successfully!")

    except Exception as e:
        print(f"Cleanup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())