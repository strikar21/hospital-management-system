import asyncio
import asyncpg

async def check_timescaledb():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='hospitaldb',
        user='hospital_user',
        password='hospital123'
    )

    try:
        # Check if TimescaleDB extension exists
        result = await conn.fetchrow("SELECT * FROM pg_extension WHERE extname = 'timescaledb'")
        if result:
            print(">> TimescaleDB extension IS installed")
            print(f"  Version: {result}")
        else:
            print(">> TimescaleDB extension NOT installed")
            print("\nTo install TimescaleDB:")
            print("1. Download from: https://www.timescale.com/download")
            print("2. Or run: CREATE EXTENSION IF NOT EXISTS timescaledb;")

        # Try to create extension
        print("\nAttempting to create TimescaleDB extension...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        print(">> TimescaleDB extension created/verified!")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(check_timescaledb())
