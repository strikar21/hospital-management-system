#!/usr/bin/env python3
"""
Debug script to check therapy JOIN issue
"""

import asyncio
import asyncpg
from app.core.config import settings

async def debug_therapy_join():
    """Debug therapy JOIN"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        # Check therapy table
        therapies = await conn.fetch("SELECT id, \"patientId\", type FROM therapy")
        print("Therapy records:")
        for t in therapies:
            print(f"- ID: {t['id']} (type: {type(t['id'])}) | Patient: {t['patientId']} | Type: {t['type']}")

        # Check therapy sessions
        sessions = await conn.fetch("""SELECT "therapyId", "patientId", "sessionNumber" FROM therapysessions LIMIT 3""")
        print("\nTherapy sessions:")
        for s in sessions:
            print(f"- TherapyID: {s['therapyId']} (type: {type(s['therapyId'])}) | Patient: {s['patientId']}")

        # Try the JOIN query manually
        print("\nTrying JOIN query...")
        joined = await conn.fetch("""
            SELECT ts.*, t.type as therapy_type
            FROM therapysessions ts
            JOIN therapy t ON ts."therapyId" = t.id::text
            WHERE ts."patientId" = '6b851aa6-e564-40b6-963f-e1a5efdf024c'
            ORDER BY ts."scheduledDate" DESC
        """)

        print(f"JOIN result: {len(joined)} records")
        for j in joined:
            print(f"- Session {j['sessionNumber']}: {j['therapy_type']}")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(debug_therapy_join())