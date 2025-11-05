import asyncpg
import asyncio

async def check_fit_device():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='hospital_user',
        password='hospital123',
        database='hospitaldb'
    )

    # Check for fit-00001 vitals (quote camelCase column)
    count = await conn.fetchval('SELECT COUNT(*) FROM vitals_timeseries WHERE "deviceId" = $1', 'fit-00001')
    print(f'Total vitals from fit-00001: {count}')

    if count > 0:
        # Get time range
        oldest = await conn.fetchval('SELECT MIN(time) FROM vitals_timeseries WHERE "deviceId" = $1', 'fit-00001')
        newest = await conn.fetchval('SELECT MAX(time) FROM vitals_timeseries WHERE "deviceId" = $1', 'fit-00001')
        print(f'Oldest: {oldest}')
        print(f'Newest: {newest}')

        # Count by time period
        recent = await conn.fetchval('SELECT COUNT(*) FROM vitals_timeseries WHERE "deviceId" = $1 AND time > NOW() - INTERVAL \'1 hour\'', 'fit-00001')
        old = await conn.fetchval('SELECT COUNT(*) FROM vitals_timeseries WHERE "deviceId" = $1 AND time < NOW() - INTERVAL \'2 hours\'', 'fit-00001')
        print(f'\nRecent (<1 hour): {recent}')
        print(f'Old (>2 hours, offline queue): {old}')

        # Get sample vitals
        rows = await conn.fetch('''
            SELECT vitaltype, value, unit, quality, time
            FROM vitals_timeseries
            WHERE "deviceId" = $1
            ORDER BY time DESC
            LIMIT 10
        ''', 'fit-00001')

        print('\nLatest 10 vitals from fit-00001:')
        print('-' * 80)
        for row in rows:
            print(f'{row["vitaltype"]:18} | {row["value"]:6.1f} {row["unit"]:4} | Q:{row["quality"]:2} | {row["time"]}')

    # Check device in devices table
    device = await conn.fetchrow('SELECT * FROM devices WHERE "deviceId" = $1', 'fit-00001')

    if device:
        print(f'\nDevice fit-00001 in devices table:')
        print(f'   Status: {device["status"]}')
        print(f'   Last Heartbeat: {device.get("lastHeartbeat", "N/A")}')
    else:
        print('\nDevice fit-00001 NOT found in devices table')

    await conn.close()

asyncio.run(check_fit_device())
