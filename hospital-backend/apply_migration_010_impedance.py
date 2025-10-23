import asyncio
import asyncpg
from app.core.config import settings

async def apply_migration():
    """Apply migration 010: Impedance tracking tables"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        with open('migrations/010_add_impedance_tracking.sql', 'r') as f:
            migration_sql = f.read()

        await conn.execute(migration_sql)
        print("[OK] Migration 010 applied: impedance tracking tables created")

        # Verify tables were created
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN ('impedancereadings', 'watchremovalevents')
        """)

        print(f"[OK] Tables created: {[t['table_name'] for t in tables]}")

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migration())
