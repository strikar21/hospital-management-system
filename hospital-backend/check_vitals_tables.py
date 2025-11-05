#!/usr/bin/env python3
"""Check if vitals_realtime table exists and has recent data"""
import asyncio
import sys
from datetime import datetime, timedelta
from app.db.database import getTimescaleConnection

async def main():
    print("=" * 80)
    print("VITALS TABLE DIAGNOSTIC")
    print("=" * 80)

    async with getTimescaleConnection() as conn:
        # Check if vitals_realtime table exists
        print("\n[1] Checking for vitals_realtime table...")
        vitals_realtime_exists = await conn.fetchval(
            """SELECT EXISTS (
                SELECT FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename = 'vitals_realtime'
            )"""
        )
        print(f"   vitals_realtime exists: {vitals_realtime_exists}")

        # Check if neural_events table exists
        neural_events_exists = await conn.fetchval(
            """SELECT EXISTS (
                SELECT FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename = 'neural_events'
            )"""
        )
        print(f"   neural_events exists: {neural_events_exists}")

        # Check if waveform_snapshots table exists
        waveform_exists = await conn.fetchval(
            """SELECT EXISTS (
                SELECT FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename = 'waveform_snapshots'
            )"""
        )
        print(f"   waveform_snapshots exists: {waveform_exists}")

        # If vitals_realtime exists, check for recent data
        if vitals_realtime_exists:
            print("\n[2] Checking vitals_realtime data...")
            result = await conn.fetchrow(
                """SELECT
                    COUNT(*) as total_count,
                    MAX(time) as latest_time,
                    COUNT(*) FILTER (WHERE time > NOW() - INTERVAL '1 hour') as last_hour_count,
                    COUNT(*) FILTER (WHERE time > NOW() - INTERVAL '5 minutes') as last_5min_count
                FROM vitals_realtime"""
            )
            print(f"   Total rows: {result['total_count']}")
            print(f"   Latest timestamp: {result['latest_time']}")
            print(f"   Last hour: {result['last_hour_count']} rows")
            print(f"   Last 5 min: {result['last_5min_count']} rows")

            if result['latest_time']:
                age = datetime.now(result['latest_time'].tzinfo) - result['latest_time']
                print(f"   Data age: {age}")
                if age > timedelta(minutes=5):
                    print("   ⚠️ WARNING: No recent data (> 5 minutes old)")
                else:
                    print("   ✅ Recent data present")
        else:
            print("\n[2] ❌ vitals_realtime table does NOT exist!")
            print("   Migration 010 has NOT been applied!")

        # Check old vitals_timeseries table
        print("\n[3] Checking old vitals_timeseries table...")
        vitals_timeseries_exists = await conn.fetchval(
            """SELECT EXISTS (
                SELECT FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename = 'vitals_timeseries'
            )"""
        )

        if vitals_timeseries_exists:
            result = await conn.fetchrow(
                """SELECT
                    COUNT(*) as total_count,
                    MAX(time) as latest_time
                FROM vitals_timeseries"""
            )
            print(f"   vitals_timeseries exists: True")
            print(f"   Total rows: {result['total_count']}")
            print(f"   Latest timestamp: {result['latest_time']}")

            if result['latest_time']:
                age = datetime.now(result['latest_time'].tzinfo) - result['latest_time']
                print(f"   Data age: {age}")

        # Check applied migrations
        print("\n[4] Checking applied migrations...")
        migrations_exist = await conn.fetchval(
            """SELECT EXISTS (
                SELECT FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename = 'schema_migrations'
            )"""
        )

        if migrations_exist:
            migrations = await conn.fetch(
                """SELECT version, applied_at
                FROM schema_migrations
                ORDER BY version"""
            )
            print(f"   Applied migrations: {len(migrations)}")
            for m in migrations:
                print(f"     - {m['version']} (applied {m['applied_at']})")
        else:
            print("   ⚠️ schema_migrations table not found")

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
