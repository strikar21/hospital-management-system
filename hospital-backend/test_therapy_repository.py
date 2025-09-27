#!/usr/bin/env python3
"""
Test therapy repository directly
"""

import asyncio
from app.repositories.therapy_repository import TherapyRepository
from app.services.service_factory import get_therapy_service

async def test_repository():
    """Test therapy repository and service"""

    # Test repository directly
    print("Testing TherapyRepository directly:")
    repo = TherapyRepository()

    try:
        sessions = await repo.get_therapy_sessions_by_patient_id("6b851aa6-e564-40b6-963f-e1a5efdf024c")
        print(f"Repository returned {len(sessions)} sessions")
        for session in sessions[:2]:  # Show first 2
            print(f"- Session {session.get('sessionNumber')}: {session.get('status')}")
    except Exception as e:
        print(f"Repository error: {e}")

    # Test service
    print("\nTesting TherapyService:")
    try:
        service = get_therapy_service()
        sessions = await service.get_by_patient_id("6b851aa6-e564-40b6-963f-e1a5efdf024c")
        print(f"Service returned {len(sessions)} sessions")
        for session in sessions[:2]:  # Show first 2
            print(f"- Session {session.get('sessionNumber')}: {session.get('status')}")
    except Exception as e:
        print(f"Service error: {e}")

if __name__ == "__main__":
    asyncio.run(test_repository())