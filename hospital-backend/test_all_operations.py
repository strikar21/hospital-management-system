#!/usr/bin/env python3
"""
Test all patient operations - investigations, therapy, medications, notes
"""

import asyncio
from app.services.service_factory import get_patient_service, get_medication_service, get_therapy_service

async def test_all_operations():
    """Test adding/modifying various patient data"""
    patient_id = '6b851aa6-e564-40b6-963f-e1a5efdf024c'

    print("=" * 60)
    print("TESTING ALL PATIENT OPERATIONS")
    print("=" * 60)

    # Test 1: Notes (we know this works)
    print("\n1. TESTING NOTES...")
    try:
        patient_service = get_patient_service()
        note = await patient_service.add_note_comment(
            patient_id=patient_id,
            content='Testing all operations - patient doing well',
            author_id='DOC0001',
            author_name='Dr. Michael Chen',
            author_role='Doctor'
        )
        print(f"   Notes: {'SUCCESS' if note else 'FAILED'}")
    except Exception as e:
        print(f"   Notes: FAILED - {e}")

    # Test 2: Medications
    print("\n2. TESTING MEDICATIONS...")
    try:
        med_service = get_medication_service()
        new_med = await med_service.add_medication(
            patient_id=patient_id,
            medication_data={
                'medicationName': 'Acetaminophen',
                'dosage': '500mg',
                'frequency': 'Every 4 hours',
                'route': 'Oral',
                'duration': '5 days',
                'prescribedBy': 'DOC0001'
            },
            created_by='DOC0001'
        )
        print(f"   Medications: {'SUCCESS' if new_med else 'FAILED'}")
        if new_med:
            print(f"     Added: {new_med.get('name')} - {new_med.get('dosage')}")
    except Exception as e:
        print(f"   Medications: FAILED - {e}")

    # Test 3: Therapy Sessions
    print("\n3. TESTING THERAPY SESSIONS...")
    try:
        therapy_service = get_therapy_service()

        # First add a therapy program
        therapy = await therapy_service.add_therapy(
            patient_id=patient_id,
            therapy_data={
                'therapyType': 'Occupational Therapy',
                'description': 'Hand coordination exercises',
                'duration': '4 weeks',
                'frequency': 'Twice weekly',
                'therapist': 'Sarah Thompson'
            },
            created_by='DOC0001'
        )

        print(f"   Therapy Program: {'SUCCESS' if therapy else 'FAILED'}")

        if therapy:
            # Add a therapy session
            session = await therapy_service.add_therapy_session(
                patient_id=patient_id,
                therapy_id=str(therapy.get('id')),
                session_data={
                    'duration': 45,
                    'sessionNotes': 'Patient showed good progress with fine motor skills',
                    'patientResponse': 'positive'
                },
                created_by='DOC0001'
            )
            print(f"   Therapy Session: {'SUCCESS' if session else 'FAILED'}")

    except Exception as e:
        print(f"   Therapy: FAILED - {e}")

    # Test 4: Check final patient data
    print("\n4. CHECKING FINAL PATIENT DATA...")
    try:
        patient_data = await patient_service.get_complete_patient_data(patient_id)

        notes_count = len(patient_data.get('notes', []))
        medications_count = len(patient_data.get('medications', []))
        investigations_count = len(patient_data.get('investigations', []))
        therapies_count = len(patient_data.get('therapies', []))

        print(f"   Notes: {notes_count}")
        print(f"   Medications: {medications_count}")
        print(f"   Investigations: {investigations_count}")
        print(f"   Therapies: {therapies_count}")

        # Test medication status update
        print("\n5. TESTING MEDICATION STATUS UPDATE...")
        if medications_count > 0:
            medications = patient_data.get('medications', [])
            first_med = medications[0]
            med_id = str(first_med.get('id'))

            success = await med_service.update_medication(
                patient_id=patient_id,
                medication_id=med_id,
                status='held',
                updated_by='DOC0001'
            )
            print(f"   Medication Status Update: {'SUCCESS' if success else 'FAILED'}")

    except Exception as e:
        print(f"   Final Data Check: FAILED - {e}")

    print("\n" + "=" * 60)
    print("ALL OPERATIONS TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_all_operations())