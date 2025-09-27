#!/usr/bin/env python3
"""
Test fixed patient notes functionality
"""

import asyncio
from app.services.service_factory import get_patient_service

async def test_fixed_notes_api():
    """Test the fixed patient notes API functionality"""
    patient_service = get_patient_service()
    patient_id = '6b851aa6-e564-40b6-963f-e1a5efdf024c'

    try:
        print('Testing get_complete_patient_data...')
        patient_data = await patient_service.get_complete_patient_data(patient_id)

        if 'notes' in patient_data:
            notes = patient_data['notes']
            print(f'Notes found: {len(notes)} notes')
            for note in notes:
                print(f'  - {note.get("authorName", "Unknown")}: {note.get("content", "No content")[:50]}...')
        else:
            print('No notes field found in patient data')

        print('\nTesting add_note_comment...')
        new_note = await patient_service.add_note_comment(
            patient_id=patient_id,
            content='Test note added via API - patient responding well to treatment and medication compliance is excellent',
            author_id='DOC0001',
            author_name='Dr. Michael Chen',
            author_role='Doctor'
        )

        if new_note:
            print(f'SUCCESS: Added note: {new_note.get("content", "Unknown")[:50]}...')
        else:
            print('FAILED: Could not add note')

        # Check notes again after adding
        print('\nRechecking notes after adding...')
        updated_patient_data = await patient_service.get_complete_patient_data(patient_id)
        updated_notes = updated_patient_data.get('notes', [])
        print(f'Total notes now: {len(updated_notes)}')

        print('\nNOTES FUNCTIONALITY TEST COMPLETE')
        print(f'Original notes: 2')
        print(f'Final notes: {len(updated_notes)}')
        print(f'Status: {"WORKING" if len(updated_notes) > 2 else "FAILED"}')

    except Exception as e:
        print(f'Error testing notes API: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fixed_notes_api())