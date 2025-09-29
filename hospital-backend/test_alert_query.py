#!/usr/bin/env python3
"""Test alert query for timeline"""

import asyncio
import asyncpg

async def test_alert_query():
    conn = await asyncpg.connect("postgresql://hospital_user:hospital123@localhost:5432/hospitaldb")

    try:
        patient_id = "6b851aa6-e564-40b6-963f-e1a5efdf024c"

        # Test simple alert query
        print("Testing simple alert query...")
        alerts = await conn.fetch('SELECT * FROM patient_alerts WHERE "patientId" = $1', patient_id)
        print(f"Found {len(alerts)} alerts for patient {patient_id}")

        for alert in alerts:
            print(f"- {alert['message']} | {alert['status']} | {alert['createdAt']}")

        # Test the exact query that should be in timeline
        print("\nTesting timeline format query...")
        timeline_alerts = await conn.fetch("""
            SELECT id, message, severity, "createdAt" as timestamp,
                   status, "acknowledgedBy", "acknowledgedAt"
            FROM patient_alerts
            WHERE "patientId" = $1
            ORDER BY "createdAt" DESC
        """, patient_id)

        print(f"Timeline format found {len(timeline_alerts)} alerts")
        for alert in timeline_alerts:
            ack_info = f" (ack by {alert['acknowledgedBy']})" if alert['acknowledgedBy'] else " (not ack)"
            print(f"- ID: {alert['id']} | {alert['message']} | {alert['status']}{ack_info}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_alert_query())