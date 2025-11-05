#!/usr/bin/env python3
"""Check device connection status"""

import asyncio
import asyncpg
from datetime import datetime

async def check_devices():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='hospital_user',
        password='hospital123',
        database='hospitaldb'
    )

    query = """
        SELECT
            d.id,
            d."serialNumber",
            d."lastSeen",
            NOW() - d."lastSeen" as "timeSinceLastSeen",
            CASE
                WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                ELSE 'offline'
            END as "deviceStatus",
            da."patientId",
            p."firstName",
            p."lastName"
        FROM devices d
        LEFT JOIN deviceassignments da ON d.id = da."deviceId" AND da."unassignedAt" IS NULL
        LEFT JOIN patients p ON da."patientId" = p.id
        ORDER BY d."lastSeen" DESC NULLS LAST
        LIMIT 10
    """

    result = await conn.fetch(query)

    print('=' * 80)
    print('DEVICE CONNECTION STATUS REPORT')
    print('=' * 80)
    print()

    if not result:
        print('No devices found in database')
    else:
        for row in result:
            status_emoji = '🔌' if row['deviceStatus'] == 'connected' else '📴' if row['deviceStatus'] == 'offline' else '⏸️'
            print(f"{status_emoji} Device: {row['id']}")
            print(f"   Serial: {row['serialNumber']}")
            if row['patientId']:
                print(f"   Patient: {row['firstName']} {row['lastName']} (ID: {row['patientId']})")
            else:
                print(f"   Patient: Not assigned")
            print(f"   Last Seen: {row['lastSeen']}")
            print(f"   Time Since: {row['timeSinceLastSeen']}")
            print(f"   Status: {row['deviceStatus'].upper()}")
            print()

    # Also check MQTT vitals
    print('=' * 80)
    print('RECENT VITALS (Last 5 minutes)')
    print('=' * 80)

    vitals_conn = await asyncpg.connect(
        host='localhost',
        port=5433,
        user='hospital_user',
        password='hospital123',
        database='hospitaltimescale'
    )

    vitals_query = """
        SELECT
            "patientId",
            time,
            "heartRate",
            "respiratoryRate",
            "skinTemperature",
            "oxygenSaturation"
        FROM vitals_realtime
        WHERE time > NOW() - INTERVAL '5 minutes'
        ORDER BY time DESC
        LIMIT 10
    """

    vitals_result = await vitals_conn.fetch(vitals_query)

    if not vitals_result:
        print('No recent vitals in last 5 minutes')
    else:
        for row in vitals_result:
            print(f"📊 Patient: {row['patientId']}")
            print(f"   Time: {row['time']}")
            print(f"   HR: {row['heartRate']} | RR: {row['respiratoryRate']} | Temp: {row['skinTemperature']} | SpO2: {row['oxygenSaturation']}")
            print()

    await conn.close()
    await vitals_conn.close()

if __name__ == '__main__':
    asyncio.run(check_devices())
