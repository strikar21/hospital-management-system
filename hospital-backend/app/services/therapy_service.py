"""
Therapy Service - Business logic layer for therapy operations
"""

from typing import Dict, List, Optional, Any
from .base_service import BaseService
from ..repositories.therapy_repository import TherapyRepository


class TherapyService(BaseService):
    """Therapy service handling all therapy business logic"""

    def __init__(self):
        self.therapy_repository = TherapyRepository()
        super().__init__(self.therapy_repository)

    async def get_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get therapy sessions by patient ID"""
        results = await self.therapy_repository.get_therapy_sessions_by_patient_id(patient_id)
        return [self.repository.transform_to_camel_case(item) for item in results]

    async def add_therapy(self, patient_id: str, therapy_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """Add therapy with validation"""
        if not therapy_data.get('therapyType'):
            raise ValueError("Therapy type is required")

        snake_data = self.repository.transform_from_camel_case(therapy_data)
        result = await self.therapy_repository.add_therapy(patient_id, snake_data, created_by)

        if result:
            return self.repository.transform_to_camel_case(result)
        return None

    async def update_therapy(self, patient_id: str, therapy_id: str, status: str, updated_by: str) -> bool:
        """Update therapy status"""
        valid_statuses = ['active', 'completed', 'cancelled', 'paused']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

        return await self.therapy_repository.update_therapy_status(
            patient_id, therapy_id, status, updated_by
        )

    async def add_therapy_session(self, patient_id: str, therapy_id: str, session_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """Add therapy session with validation"""
        if not session_data.get('duration'):
            raise ValueError("Session duration is required")

        snake_data = self.repository.transform_from_camel_case(session_data)
        result = await self.therapy_repository.add_therapy_session(
            patient_id, therapy_id, snake_data, created_by
        )

        if result:
            return self.repository.transform_to_camel_case(result)
        return None