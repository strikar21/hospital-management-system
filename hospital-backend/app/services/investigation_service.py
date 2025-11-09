"""
Investigation Service - Business logic layer for investigation operations
"""

from typing import Dict, List, Optional, Any
import asyncpg

from .base_service import BaseService
from ..repositories.investigation_repository import InvestigationRepository
from ..domain import StaffResolver


class InvestigationService(BaseService):
    """Investigation service handling all investigation business logic"""

    def __init__(self, pool: Optional[asyncpg.Pool] = None):
        self.investigation_repository = InvestigationRepository()
        super().__init__(self.investigation_repository)

        # Initialize StaffResolver with database pool
        if pool:
            self.staff_resolver = StaffResolver(pool)
        else:
            self.staff_resolver = None
            self.logger.warning("InvestigationService initialized without database pool - staff resolution will be limited")

    async def get_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get investigations by patient ID with staff name resolution"""
        results = await self.investigation_repository.get_by_patient_id(patient_id)
        investigations = [self.repository.transform_to_camel_case(item) for item in results]

        # Enrich with staff names using StaffResolver
        if investigations and self.staff_resolver:
            investigations = await self.staff_resolver.enrich_records_batch(
                investigations,
                {
                    'orderedBy': 'orderedByName',
                    'performedBy': 'performedByName',
                    'createdBy': 'createdByName'
                }
            )

        return investigations

    async def add_investigation(self, patient_id: str, investigation_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """Add investigation with validation and staff name resolution"""
        if not investigation_data.get('type'):
            raise ValueError("Investigation type is required")

        # Use direct field names - no transformation needed
        result = await self.investigation_repository.add_investigation(patient_id, investigation_data, created_by)

        if result:
            investigation = self.repository.transform_to_camel_case(result)

            # Enrich with staff names using StaffResolver
            if self.staff_resolver:
                investigation = await self.staff_resolver.enrich_record_with_staff(
                    investigation,
                    {
                        'orderedBy': 'orderedByName',
                        'createdBy': 'createdByName'
                    }
                )

            return investigation
        return None

    async def update_investigation(self, patient_id: str, investigation_id: str, status: str, updated_by: str) -> bool:
        """Update investigation status"""
        valid_statuses = ['pending', 'inProgress', 'completed', 'cancelled']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

        return await self.investigation_repository.update_investigation_status(
            patient_id, investigation_id, status, updated_by
        )

    async def update_investigation_results(self, investigation_id: str, results: str, updated_by: str) -> bool:
        """Update investigation results"""
        update_data = {
            'results': results,
            'status': 'completed'
        }
        result = await self.investigation_repository.update(investigation_id, update_data, updated_by)
        return result is not None

    async def complete_investigation(self, patient_id: str, investigation_id: str, results: str, completed_by: str) -> bool:
        """Complete investigation with results"""
        return await self.investigation_repository.complete_investigation(
            patient_id, investigation_id, results, completed_by
        )
