#!/usr/bin/env python3
"""
Test script to check therapy sessions in database
"""

import asyncio
import asyncpg
from app.core.config import settings

async def test_therapy_sessions():
    """Test therapy sessions data"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        # Check therapysessions table
        sessions = await conn.fetch("""
            SELECT ts.*, p."firstName", p."lastName"
            FROM therapysessions ts
            JOIN patients p ON ts."patientId" = p.id
            ORDER BY ts."patientId"
        """)

        print(f"Found {len(sessions)} therapy sessions:")
        for session in sessions:
            print(f"- {session['firstName']} {session['lastName']}: Session #{session['sessionNumber']} - {session['status']}")

        # Check Jennifer Lee specifically
        jennifer_sessions = await conn.fetch("""
            SELECT * FROM therapysessions
            WHERE "patientId" = '6b851aa6-e564-40b6-963f-e1a5efdf024c'
            ORDER BY "sessionNumber"
        """)

        print(f"\nJennifer Lee has {len(jennifer_sessions)} sessions:")
        for session in jennifer_sessions:
            print(f"- Session {session['sessionNumber']}: {session['status']} - {session.get('sessionNotes', 'No notes')}")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_therapy_sessions())