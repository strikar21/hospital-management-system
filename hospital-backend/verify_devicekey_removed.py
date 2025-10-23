import asyncio
import asyncpg
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_schema():
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')
    try:
        # Check if deviceKey column exists
        column_check = await conn.fetchval("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = 'devices'
            AND column_name = 'deviceKey'
        """)

        if column_check == 0:
            logger.info("✅ deviceKey column successfully removed from devices table")
        else:
            logger.error("❌ deviceKey column still exists in devices table")

        # Check if MAC index exists
        index_check = await conn.fetchval("""
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE tablename = 'devices'
            AND indexname = 'idx_devices_mac'
        """)

        if index_check > 0:
            logger.info("✅ MAC address index (idx_devices_mac) exists")
        else:
            logger.warning("⚠️ MAC address index not found")

        # Show current devices table schema
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'devices'
            ORDER BY ordinal_position
        """)

        logger.info("\n📋 Current devices table schema:")
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            logger.info(f"   - {col['column_name']}: {col['data_type']} ({nullable})")

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(verify_schema())
