#!/usr/bin/env python3
"""
Script to add therapy sessions for patients with therapy records
"""

import asyncio
import asyncpg
from datetime import datetime, timedelta
import uuid
from app.core.config import settings

async def add_therapy_sessions():
    """Add therapy sessions for patients with active therapy"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        # Get therapy records that need sessions
        therapy_records = await conn.fetch("""
            SELECT t.id as therapy_id, t."patientId", t.type, t.description, t.frequency, p."firstName", p."lastName"
            FROM therapy t
            JOIN patients p ON t."patientId" = p.id
            WHERE t.status = 'active'
        """)

        print(f"Found {len(therapy_records)} active therapy records")

        for therapy in therapy_records:
            therapy_id = therapy['therapy_id']
            patient_id = therapy['patientId']
            patient_name = f"{therapy['firstName']} {therapy['lastName']}"
            therapy_type = therapy['type']
            frequency = therapy['frequency']

            print(f"Adding sessions for {patient_name} - {therapy_type}")

            # Create therapy sessions based on therapy type and patient
            if patient_name == "Jennifer Lee":  # Behavioral Therapy - Weekly
                sessions_data = [
                    {
                        "id": str(uuid.uuid4()),
                        "therapyId": str(therapy_id),
                        "patientId": patient_id,
                        "sessionNumber": 1,
                        "scheduledDate": datetime.now() - timedelta(days=7),
                        "completedAt": datetime.now() - timedelta(days=7),
                        "performedBy": "PSY001",
                        "sessionNotes": "Initial CBT session. Identified work-related stress triggers. Introduced breathing techniques.",
                        "status": "completed",
                        "duration": "60 minutes"
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "therapyId": str(therapy_id),
                        "patientId": patient_id,
                        "sessionNumber": 2,
                        "scheduledDate": datetime.now(),
                        "completedAt": datetime.now(),
                        "performedBy": "PSY001",
                        "sessionNotes": "Progress on anxiety management. Practiced mindfulness exercises. Patient reports less work stress.",
                        "status": "completed",
                        "duration": "60 minutes"
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "therapyId": str(therapy_id),
                        "patientId": patient_id,
                        "sessionNumber": 3,
                        "scheduledDate": datetime.now() + timedelta(days=7),
                        "performedBy": "PSY001",
                        "status": "scheduled",
                        "duration": "60 minutes"
                    }
                ]

            elif patient_name == "William Johnson":  # Respiratory Therapy - Daily
                sessions_data = [
                    {
                        "id": str(uuid.uuid4()),
                        "therapyId": str(therapy_id),
                        "patientId": patient_id,
                        "sessionNumber": 1,
                        "scheduledDate": datetime.now() - timedelta(days=2),
                        "completedAt": datetime.now() - timedelta(days=2),
                        "performedBy": "TEC0001",
                        "sessionNotes": "Initial pulmonary rehabilitation assessment. Baseline spirometry performed. Introduced pursed lip breathing.",
                        "status": "completed",
                        "duration": "45 minutes"
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "therapyId": str(therapy_id),
                        "patientId": patient_id,
                        "sessionNumber": 2,
                        "scheduledDate": datetime.now() - timedelta(days=1),
                        "completedAt": datetime.now() - timedelta(days=1),
                        "performedBy": "TEC0001",
                        "sessionNotes": "Breathing exercises and chest percussion. Patient tolerated treatment well. Oxygen saturation improved.",
                        "status": "completed",
                        "duration": "30 minutes"
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "therapyId": str(therapy_id),
                        "patientId": patient_id,
                        "sessionNumber": 3,
                        "scheduledDate": datetime.now(),
                        "performedBy": "TEC0001",
                        "status": "scheduled",
                        "duration": "30 minutes"
                    }
                ]

            elif patient_name == "Thomas Brown":  # Physical Therapy - 3x weekly
                sessions_data = [
                    {
                        "id": str(uuid.uuid4()),
                        "therapyId": str(therapy_id),
                        "patientId": patient_id,
                        "sessionNumber": 1,
                        "scheduledDate": datetime.now() - timedelta(days=3),
                        "completedAt": datetime.now() - timedelta(days=3),
                        "performedBy": "PT001",
                        "sessionNotes": "Initial PT evaluation for arthritis. Range of motion assessment. Gentle joint mobilization performed.",
                        "status": "completed",
                        "duration": "45 minutes"
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "therapyId": str(therapy_id),
                        "patientId": patient_id,
                        "sessionNumber": 2,
                        "scheduledDate": datetime.now() - timedelta(days=1),
                        "completedAt": datetime.now() - timedelta(days=1),
                        "performedBy": "PT001",
                        "sessionNotes": "Continued ROM exercises. Added light resistance training. Patient reports decreased stiffness.",
                        "status": "completed",
                        "duration": "45 minutes"
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "therapyId": str(therapy_id),
                        "patientId": patient_id,
                        "sessionNumber": 3,
                        "scheduledDate": datetime.now() + timedelta(days=1),
                        "performedBy": "PT001",
                        "status": "scheduled",
                        "duration": "45 minutes"
                    }
                ]

            else:
                continue  # Skip patients without specific session plans

            # Insert therapy sessions
            for session in sessions_data:
                await conn.execute("""
                    INSERT INTO therapysessions (
                        id, "therapyId", "patientId", "sessionNumber", "scheduledDate",
                        "completedAt", "performedBy", "sessionNotes", status, duration,
                        "createdAt", "updatedAt"
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """, session["id"], session["therapyId"], session["patientId"],
                    session["sessionNumber"], session["scheduledDate"],
                    session.get("completedAt"), session["performedBy"],
                    session.get("sessionNotes"), session["status"], session["duration"],
                    datetime.now(), datetime.now())

            print(f"Added {len(sessions_data)} therapy sessions for {patient_name}")

        print("Therapy sessions added successfully!")

    finally:
        await conn.close()

async def main():
    """Main function"""
    print("Adding therapy sessions for patients...")

    try:
        await add_therapy_sessions()
        print("Therapy sessions update completed successfully!")

    except Exception as e:
        print(f"Error adding therapy sessions: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())