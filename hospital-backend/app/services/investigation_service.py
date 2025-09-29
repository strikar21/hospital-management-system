"""
Investigation Service - Business logic layer for investigation operations
"""

from typing import Dict, List, Optional, Any
from .base_service import BaseService
from ..repositories.investigation_repository import InvestigationRepository


class InvestigationService(BaseService):
    """Investigation service handling all investigation business logic"""

    def __init__(self):
        self.investigation_repository = InvestigationRepository()
        super().__init__(self.investigation_repository)

    async def get_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get investigations by patient ID"""
        results = await self.investigation_repository.get_by_patient_id(patient_id)
        return [self.repository.transform_to_camel_case(item) for item in results]

    async def add_investigation(self, patient_id: str, investigation_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """Add investigation with validation"""
        # Accept both 'investigationType' (from frontend) and 'type' (database field)
        investigation_type = investigation_data.get('investigationType') or investigation_data.get('type')
        if not investigation_type:
            raise ValueError("Investigation type is required")

        # Ensure 'type' field is set for database (database uses 'type' not 'investigationType')
        if 'investigationType' in investigation_data and 'type' not in investigation_data:
            investigation_data['type'] = investigation_data['investigationType']

        snake_data = self.repository.transform_from_camel_case(investigation_data)
        result = await self.investigation_repository.add_investigation(patient_id, snake_data, created_by)

        if result:
            return self.repository.transform_to_camel_case(result)
        return None

    async def update_investigation(self, patient_id: str, investigation_id: str, status: str, updated_by: str) -> bool:
        """Update investigation status"""
        valid_statuses = ['pending', 'inProgress', 'completed', 'cancelled']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

        return await self.investigation_repository.update_investigation_status(
            patient_id, investigation_id, status, updated_by
        )

    async def complete_investigation(self, patient_id: str, investigation_id: str, results: str, completed_by: str) -> bool:
        """Complete investigation with results"""
        return await self.investigation_repository.complete_investigation(
            patient_id, investigation_id, results, completed_by
        )