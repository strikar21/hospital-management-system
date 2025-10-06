"""
Discharge Workflow Service - Multi-step discharge approval process
"""
from typing import Dict, Optional
from datetime import datetime
import logging

from .base_service import BaseService

logger = logging.getLogger(__name__)


class DischargeService(BaseService):
    """
    Handles multi-step discharge workflow:
    1. Doctor requests discharge (requestedBy)
    2. Admin approves discharge (approvedBy)
    3. Nurse completes discharge (performedBy)
    """

    async def request_discharge(
        self,
        patient_id: str,
        requested_by: str,
        reason: str,
        notes: Optional[str] = None
    ) -> Dict:
        """Doctor requests patient discharge"""
        query = """
            INSERT INTO discharge_requests
            ("patientId", "requestedBy", reason, notes, status)
            VALUES ($1, $2, $3, $4, 'requested')
            RETURNING *
        """

        result = await self.execute_custom_query(
            query,
            [patient_id, requested_by, reason, notes]
        )

        logger.info(f"Discharge requested for patient {patient_id} by {requested_by}")
        return result[0] if result else None

    async def approve_discharge(
        self,
        request_id: int,
        approved_by: str,
        approval_notes: Optional[str] = None
    ) -> Dict:
        """Admin approves discharge request"""
        query = """
            UPDATE discharge_requests
            SET status = 'approved',
                "approvedBy" = $1,
                "approvedAt" = NOW(),
                "approvalNotes" = $2,
                "updatedAt" = NOW()
            WHERE id = $3 AND status = 'requested'
            RETURNING *
        """

        result = await self.execute_custom_query(
            query,
            [approved_by, approval_notes, request_id]
        )

        if result:
            logger.info(f"Discharge request {request_id} approved by {approved_by}")
        return result[0] if result else None

    async def complete_discharge(
        self,
        request_id: int,
        performedBy: str,
        discharge_notes: Optional[str] = None
    ) -> Dict:
        """Nurse completes patient discharge"""
        query = """
            UPDATE discharge_requests
            SET status = 'completed',
                "performedBy" = $1,
                "performedAt" = NOW(),
                "dischargeNotes" = $2,
                "updatedAt" = NOW()
            WHERE id = $3 AND status = 'approved'
            RETURNING *
        """

        result = await self.execute_custom_query(
            query,
            [performedBy, discharge_notes, request_id]
        )

        if result:
            # Update patient status
            patient_query = """
                UPDATE patients
                SET status = 'discharged',
                    "updatedAt" = NOW()
                WHERE id = (
                    SELECT "patientId" FROM discharge_requests WHERE id = $1
                )
            """
            await self.execute_custom_query(patient_query, [request_id])

            logger.info(f"Discharge completed for request {request_id} by {performedBy}")

        return result[0] if result else None

    async def get_pending_requests(self) -> list[Dict]:
        """Get all pending discharge requests"""
        query = """
            SELECT dr.*, p.name as "patientName"
            FROM discharge_requests dr
            JOIN patients p ON dr."patientId" = p.id
            WHERE dr.status = 'requested'
            ORDER BY dr."requestedAt" DESC
        """
        return await self.execute_custom_query(query)

    async def get_approved_requests(self) -> list[Dict]:
        """Get approved but not completed discharge requests"""
        query = """
            SELECT dr.*, p.name as "patientName"
            FROM discharge_requests dr
            JOIN patients p ON dr."patientId" = p.id
            WHERE dr.status = 'approved'
            ORDER BY dr."approvedAt" DESC
        """
        return await self.execute_custom_query(query)
