#!/usr/bin/env python3
"""
Add sample alerts to patient_alerts table
"""

import asyncio
import asyncpg

async def add_sample_alerts():
    conn = await asyncpg.connect("postgresql://hospital_user:hospital123@localhost:5432/hospitaldb")

    try:
        # Check table structure first
        columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'patient_alerts'
            ORDER BY ordinal_position
        """)

        print("PATIENT_ALERTS TABLE STRUCTURE:")
        for col in columns:
            print(f"- {col['column_name']}: {col['data_type']}")

        # Get patient IDs
        patients = await conn.fetch("SELECT id FROM patients LIMIT 2")
        print(f"\nFound {len(patients)} patients")

        # Add sample alerts
        for patient in patients:
            patient_id = patient['id']
            print(f"Adding alerts for patient: {patient_id}")

            # Alert 1: Active heart rate alert
            await conn.execute("""
                INSERT INTO patient_alerts ("patientId", type, message, severity, status)
                VALUES ($1, $2, $3, $4, $5)
            """, patient_id, 'vital', 'Heart rate high', 'high', 'active')

            # Alert 2: Acknowledged blood pressure alert
            await conn.execute("""
                INSERT INTO patient_alerts ("patientId", type, message, severity, status, "acknowledgedBy")
                VALUES ($1, $2, $3, $4, $5, $6)
            """, patient_id, 'vital', 'Blood pressure critical', 'critical', 'acknowledged', 'DOC0001')

        # Show results
        total_alerts = await conn.fetchval("SELECT COUNT(*) FROM patient_alerts")
        print(f"\nTotal alerts in database: {total_alerts}")

        # Show alert details
        alerts = await conn.fetch("""
            SELECT "patientId", message, severity, status, "acknowledgedBy"
            FROM patient_alerts
            ORDER BY "createdAt" DESC
        """)

        print("\nCreated alerts:")
        for alert in alerts:
            ack_status = f"(acknowledged by {alert['acknowledgedBy']})" if alert['acknowledgedBy'] else "(not acknowledged)"
            print(f"  - Patient {alert['patientId']}: {alert['message']} [{alert['severity']}] {ack_status}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(add_sample_alerts())