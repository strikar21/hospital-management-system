#!/usr/bin/env python3
"""
Test patient notes functionality
"""

import asyncio
import asyncpg
from app.core.config import settings

async def test_notes():
    """Test patient notes table and functionality"""
    conn = await asyncpg.connect(settings.databaseUrl)
    try:
        # Check patientnotes table structure
        schema = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'patientnotes'
            ORDER BY ordinal_position
        """)
        print('patientnotes table structure:')
        for col in schema:
            print(f'  {col["column_name"]}: {col["data_type"]} (nullable: {col["is_nullable"]}) (default: {col["column_default"]})')

        # Check if there are any existing notes
        notes = await conn.fetch('SELECT * FROM patientnotes LIMIT 3')
        print(f'\nExisting notes ({len(notes)} found):')
        for note in notes:
            content = note.get('content')
            preview = content[:50] + '...' if content and len(content) > 50 else content or 'None'
            print(f'  - Patient: {note.get("patientId")} | Author: {note.get("authorName")} | Content: {preview}')

        # Check specifically for Jennifer Lee
        patient_id = '6b851aa6-e564-40b6-963f-e1a5efdf024c'
        jennifer_notes = await conn.fetch('SELECT * FROM patientnotes WHERE "patientId" = $1', patient_id)
        print(f'\nJennifer Lee notes ({len(jennifer_notes)} found):')
        for note in jennifer_notes:
            print(f'  - {note.get("authorName", "Unknown")}: {note.get("content", "No content")}')

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_notes())