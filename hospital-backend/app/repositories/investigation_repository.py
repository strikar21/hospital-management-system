"""
Investigation Repository - Data access layer for investigation operations
"""

from typing import Dict, List, Optional, Any
from .base_repository import BaseRepository


class InvestigationRepository(BaseRepository):
    """Investigation repository for all investigation-related database operations"""

    def __init__(self):
        super().__init__("investigations", None)

    async def get_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get investigations by patient ID"""
        return await self.get_all(filters={'patientId': patient_id})

    async def add_investigation(self, patient_id: str, investigation_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """Add investigation to patient"""
        investigation_data['patientId'] = patient_id
        investigation_data['status'] = 'pending'
        investigation_data['createdBy'] = created_by  # Audit trail - who created this record
        return await self.create(investigation_data, created_by)

    async def update_investigation_status(self, patient_id: str, investigation_id: str, status: str, updated_by: str) -> bool:
        """Update investigation status"""
        result = await self.update(investigation_id, {'status': status}, updated_by)
        return result is not None

    async def complete_investigation(self, patient_id: str, investigation_id: str, results: str, completed_by: str) -> bool:
        """Complete investigation with results"""
        update_data = {
            'status': 'completed',
            'results': results,
            'completedBy': completed_by,
            'completedAt': self.get_current_timestamp()
        }
        result = await self.update(investigation_id, update_data, completed_by)
        return result is not None

    def get_current_timestamp(self):
        from datetime import datetime
        return datetime.utcnow().isoformat()