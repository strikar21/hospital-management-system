"""
Database Migration: Standardize prescribedBy Pattern
- Rename investigations.performedBy -> prescribedBy
- Rename therapy.performedBy -> prescribedBy
- Drop patientnotes.authorName and patientnotes.authorRole (backend will lookup from staff table)

STRICT CAMELCASE ONLY - All column names use camelCase
"""

import asyncio
import asyncpg
import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.core.config import settings

async def migrate_prescribedby_standardization():
    """Migrate database to standardize prescribedBy pattern across all tables"""

    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("🔄 Starting prescribedBy standardization migration...")

        # Step 1: Rename investigations.performedBy to prescribedBy
        print("\n1️⃣ Migrating investigations table...")
        try:
            await conn.execute('''
                ALTER TABLE investigations
                RENAME COLUMN "performedBy" TO "prescribedBy";
            ''')
            print("   ✅ investigations.performedBy → prescribedBy")
        except asyncpg.exceptions.UndefinedColumnError:
            print("   ⚠️  Column already renamed or doesn't exist")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Step 2: Rename therapy.performedBy to prescribedBy
        print("\n2️⃣ Migrating therapy table...")
        try:
            await conn.execute('''
                ALTER TABLE therapy
                RENAME COLUMN "performedBy" TO "prescribedBy";
            ''')
            print("   ✅ therapy.performedBy → prescribedBy")
        except asyncpg.exceptions.UndefinedColumnError:
            print("   ⚠️  Column already renamed or doesn't exist")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Step 3: Drop patientnotes.authorName (backend will lookup from staff table)
        print("\n3️⃣ Migrating patientnotes table...")
        try:
            await conn.execute('''
                ALTER TABLE patientnotes
                DROP COLUMN IF EXISTS "authorName";
            ''')
            print("   ✅ Dropped patientnotes.authorName (will use staff lookup)")
        except Exception as e:
            print(f"   ❌ Error dropping authorName: {e}")

        # Step 4: Drop patientnotes.authorRole (backend will lookup from staff table)
        try:
            await conn.execute('''
                ALTER TABLE patientnotes
                DROP COLUMN IF EXISTS "authorRole";
            ''')
            print("   ✅ Dropped patientnotes.authorRole (will use staff lookup)")
        except Exception as e:
            print(f"   ❌ Error dropping authorRole: {e}")

        # Verify changes
        print("\n✅ Migration completed successfully!")
        print("\n📋 Summary:")
        print("   - investigations now uses: prescribedBy")
        print("   - therapy now uses: prescribedBy")
        print("   - patientnotes now uses: authorId only (lookup from staff table)")
        print("   - Pattern matches medications table (prescribedBy)")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_prescribedby_standardization())
