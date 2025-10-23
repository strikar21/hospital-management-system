"""
Test script to check exact query return types for getWatchConnectionStatus
"""
import asyncio
import asyncpg
from decimal import Decimal

async def test_query():
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')

    # Exact query from getWatchConnectionStatus
    query = """
    SELECT d.*, da."patientId", p."firstName", p."lastName",
           CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                ELSE 'offline' END as "connectionStatus",
           CAST(EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 AS DOUBLE PRECISION) as "minutesSinceLastSeen"
    FROM devices d
    LEFT JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
    LEFT JOIN patients p ON da."patientId" = p.id
    WHERE d."deviceType" = 'watch'
    ORDER BY d.status, d."lastSeen" DESC
    LIMIT 1
    """

    rows = await conn.fetch(query)

    if rows:
        print(f"\nFound {len(rows)} row(s)\n")
        row = rows[0]
        statusDict = dict(row)

        print("=" * 80)
        print("COLUMN TYPES IN RESULT:")
        print("=" * 80)

        decimal_found = False
        for key, value in statusDict.items():
            value_type = type(value).__name__
            if isinstance(value, Decimal):
                decimal_found = True
                print(f"[DECIMAL] {key:<30} = {value_type:<20} VALUE: {value}")
            else:
                print(f"[OK] {key:<30} = {value_type:<20}")

        print("=" * 80)
        if decimal_found:
            print("\nDECIMAL VALUES FOUND - These will cause JSON serialization error!")
        else:
            print("\nNO DECIMAL VALUES - Query should serialize correctly")
        print("=" * 80)
    else:
        print("No watches found in database")

    await conn.close()

asyncio.run(test_query())
