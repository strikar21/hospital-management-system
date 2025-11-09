"""
Cleanup Duplicate Alerts - Remove 471K+ old duplicate alerts

This script removes all duplicate alerts created before the deduplication fix,
keeping only the MOST RECENT alert per (patientId, type, status) combination.

Run this ONCE after deploying the alert deduplication fix.
"""

import asyncio
import asyncpg
from datetime import datetime

async def cleanup_duplicates():
    print("\n" + "="*70)
    print("ALERT CLEANUP SCRIPT - Remove Duplicate Alerts")
    print("="*70)

    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')

    # First, show current state
    print("\n[1/4] Checking current alert counts...")
    total_before = await conn.fetchval('SELECT COUNT(*) FROM patient_alerts')
    print(f"   Total alerts in database: {total_before:,}")

    # Count duplicates
    duplicates = await conn.fetchval('''
        SELECT COUNT(*)
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY "patientId", type, status
                       ORDER BY "createdAt" DESC
                   ) as rn
            FROM patient_alerts
        ) t
        WHERE t.rn > 1
    ''')
    print(f"   Duplicate alerts to remove: {duplicates:,}")
    print(f"   Alerts to keep: {total_before - duplicates:,}")

    # Confirm before deleting
    print("\n[2/4] This will DELETE {:,} duplicate alerts.".format(duplicates))
    print("      Only the MOST RECENT alert per (patient, type, status) will be kept.")

    # Delete duplicates
    print("\n[3/4] Deleting duplicate alerts...")
    result = await conn.execute('''
        DELETE FROM patient_alerts
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY "patientId", type, status
                           ORDER BY "createdAt" DESC
                       ) as rn
                FROM patient_alerts
            ) t
            WHERE t.rn > 1
        )
    ''')

    # Extract deleted count from result string
    deleted_count = int(result.split()[-1]) if result else 0
    print(f"   Deleted {deleted_count:,} duplicate alerts")

    # Show final state
    print("\n[4/4] Verification - Final alert counts...")
    total_after = await conn.fetchval('SELECT COUNT(*) FROM patient_alerts')
    print(f"   Total alerts remaining: {total_after:,}")
    print(f"   Space saved: {total_before - total_after:,} alerts removed")

    # Show breakdown by patient
    patient_counts = await conn.fetch('''
        SELECT p."firstName", p."lastName", COUNT(a.id) as alert_count
        FROM patient_alerts a
        JOIN patients p ON a."patientId" = p.id
        WHERE a.status = 'active'
        GROUP BY p.id, p."firstName", p."lastName"
        ORDER BY alert_count DESC
        LIMIT 5
    ''')

    print("\n   Top 5 patients by active alert count:")
    for row in patient_counts:
        print(f"      {row['firstName']} {row['lastName']}: {row['alert_count']} active alerts")

    await conn.close()

    print("\n" + "="*70)
    print("CLEANUP COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print("1. Refresh your frontend (browser reload)")
    print("2. Test alert acknowledgement - should work immediately now")
    print("3. Alert count should decrease when you click acknowledge")
    print("\n")

if __name__ == '__main__':
    asyncio.run(cleanup_duplicates())
