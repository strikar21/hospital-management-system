#!/usr/bin/env python3
"""Check CURRENT vitals data - what's in database RIGHT NOW"""
import asyncpg
import asyncio
from datetime import datetime, timezone

async def main():
    print("=" * 80)
    print("CHECKING CURRENT VITALS DATA (RIGHT NOW)")
    print("=" * 80)

    # Connect to TimescaleDB
    conn = await asyncpg.connect(
        host='localhost',
        port=5433,
        user='hospital_user',
        password='hospital123',
        database='hospitaltimescale'
    )

    try:
        # Check what tables actually exist
        print("\n[1] TABLES IN DATABASE:")
        tables = await conn.fetch("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        for t in tables:
            print(f"   - {t['tablename']}")

        # Check vitals_realtime if it exists
        has_vitals_realtime = any(t['tablename'] == 'vitals_realtime' for t in tables)

        if has_vitals_realtime:
            print("\n[2] VITALS_REALTIME TABLE - LAST 10 ROWS:")
            rows = await conn.fetch("""
                SELECT time, "patientId", "deviceId", mode, "heartRate",
                       "oxygenSaturation", "skinTemperature"
                FROM vitals_realtime
                ORDER BY time DESC
                LIMIT 10
            """)

            if rows:
                for r in rows:
                    age = datetime.now(timezone.utc) - r['time']
                    print(f"   {r['time']} ({age.total_seconds():.0f}s ago)")
                    print(f"      Device: {r['deviceId']}, Patient: {r['patientId']}")
                    print(f"      HR: {r['heartRate']}, SpO2: {r['oxygenSaturation']}, Temp: {r['skinTemperature']}")
            else:
                print("   ❌ NO DATA in vitals_realtime")
        else:
            print("\n[2] ❌ vitals_realtime TABLE DOES NOT EXIST")

        # Check vitals_timeseries (old table)
        has_vitals_timeseries = any(t['tablename'] == 'vitals_timeseries' for t in tables)

        if has_vitals_timeseries:
            print("\n[3] VITALS_TIMESERIES TABLE (OLD) - LAST 10 ROWS:")
            rows = await conn.fetch("""
                SELECT time, "patientId", "deviceId", vitaltype, value, unit
                FROM vitals_timeseries
                ORDER BY time DESC
                LIMIT 10
            """)

            if rows:
                for r in rows:
                    age = datetime.now(timezone.utc) - r['time']
                    print(f"   {r['time']} ({age.total_seconds():.0f}s ago)")
                    print(f"      Device: {r['deviceId']}, {r['vitaltype']}: {r['value']} {r['unit']}")
            else:
                print("   ❌ NO DATA in vitals_timeseries")

        # Check for data in last 5 minutes
        print("\n[4] DATA IN LAST 5 MINUTES:")
        if has_vitals_realtime:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM vitals_realtime
                WHERE time > NOW() - INTERVAL '5 minutes'
            """)
            print(f"   vitals_realtime: {count} rows")

        if has_vitals_timeseries:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM vitals_timeseries
                WHERE time > NOW() - INTERVAL '5 minutes'
            """)
            print(f"   vitals_timeseries: {count} rows")

    finally:
        await conn.close()

    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
