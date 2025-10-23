import asyncio
import asyncpg
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def apply_migration():
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')
    try:
        logger.info("🔄 Applying migration 009 - Remove deviceKey column...")
        with open('migrations/009_remove_device_key.sql', 'r') as f:
            await conn.execute(f.read())
        logger.info("✅ Migration 009 complete - deviceKey removed, HMAC authentication active")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migration())
