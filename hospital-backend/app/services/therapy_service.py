"""
Therapy Service - Business logic layer for therapy operations
"""

from typing import Dict, List, Optional, Any
import asyncpg

from .base_service import BaseService
from ..repositories.therapy_repository import TherapyRepository
from ..domain import StaffResolver


class TherapyService(BaseService):
    """Therapy service handling all therapy business logic"""

    def __init__(self, pool: Optional[asyncpg.Pool] = None):
        self.therapy_repository = TherapyRepository()
        super().__init__(self.therapy_repository)

        # Initialize StaffResolver with database pool
        if pool:
            self.staff_resolver = StaffResolver(pool)
        else:
            self.staff_resolver = None
            self.logger.warning("TherapyService initialized without database pool - staff resolution will be limited")

    async def get_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get therapy sessions by patient ID with staff name resolution"""
        results = await self.therapy_repository.get_therapy_sessions_by_patient_id(patient_id)
        therapies = [self.repository.transform_to_camel_case(item) for item in results]

        # Enrich with staff names using StaffResolver
        if therapies and self.staff_resolver:
            therapies = await self.staff_resolver.enrich_records_batch(
                therapies,
                {
                    'prescribedBy': 'prescribedByName',
                    'performedBy': 'performedByName',
                    'createdBy': 'createdByName'
                }
            )

        return therapies

    async def add_therapy(self, patient_id: str, therapy_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """Add therapy with validation and staff name resolution"""
        if not therapy_data.get('type'):
            raise ValueError("Therapy type is required")

        # Use direct field names - no transformation needed
        result = await self.therapy_repository.add_therapy(patient_id, therapy_data, created_by)

        if result:
            therapy = self.repository.transform_to_camel_case(result)

            # Enrich with staff names using StaffResolver
            if self.staff_resolver:
                therapy = await self.staff_resolver.enrich_record_with_staff(
                    therapy,
                    {
                        'prescribedBy': 'prescribedByName',
                        'createdBy': 'createdByName'
                    }
                )

            return therapy
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
        """Add therapy session with validation and staff name resolution"""
        if not session_data.get('duration'):
            raise ValueError("Session duration is required")

        snake_data = self.repository.transform_from_camel_case(session_data)
        result = await self.therapy_repository.add_therapy_session(
            patient_id, therapy_id, snake_data, created_by
        )

        if result:
            session = self.repository.transform_to_camel_case(result)

            # Enrich with staff names using StaffResolver
            if self.staff_resolver:
                session = await self.staff_resolver.enrich_record_with_staff(
                    session,
                    {
                        'performedBy': 'performedByName',
                        'createdBy': 'createdByName'
                    }
                )

            return session
        return None
