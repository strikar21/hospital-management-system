"""
Admission workflow API endpoints for hospital management system
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import asyncpg
import logging
from datetime import datetime, date
import uuid
from dateutil import parser as dateParser

from ...core.database import getDbConnection
from ...core.auth_dependencies import require_medical_staff

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_medical_staff)])

@router.post("/recommendations")
async def createAdmissionRecommendation(admissionData: dict):
    """Create a new admission recommendation from doctor assessment"""

    try:
        async with getDbConnection() as conn:
            async with conn.transaction():
                # Generate systematic recommendation ID (REC + date + sequence)
                today = datetime.now().strftime('%Y%m%d')

                # Get count of recommendations today for sequence number
                countQuery = """
                    SELECT COUNT(*) FROM admissionrecommendations
                    WHERE DATE("createdAt") = CURRENT_DATE
                """
                countResult = await conn.fetchval(countQuery)
                sequence = (countResult or 0) + 1

                recId = f"REC{today}{sequence:03d}"  # REC20250907001, REC20250907002, etc.

                # Insert admission recommendation
                query = """
                    INSERT INTO admissionrecommendations (
                        id, "patientName", age, gender, diagnosis, priority, department,
                        "recommendedWard", "assignedDoctor", "recommendedBy", status,
                        weight, "admissionDate", "insuranceType", "emergencyContact",
                        allergies, "admissionNotes", "createdAt", "updatedAt"
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, NOW(), NOW())
                    RETURNING id, "createdAt"
                """

                result = await conn.fetchrow(query,
                    recId,
                    admissionData.get('patientName', ''),
                    admissionData.get('age'),
                    admissionData.get('gender', ''),
                    admissionData.get('diagnosis', ''),
                    admissionData.get('priority', 'routine'),
                    admissionData.get('department', ''),
                    admissionData.get('recommendedWard', ''),
                    admissionData.get('assignedDoctor', ''),
                    admissionData.get('recommendedBy', ''),
                    'pending',
                    admissionData.get('weight'),
                    admissionData.get('admissionDate'),
                    admissionData.get('insuranceType', ''),
                    admissionData.get('emergencyContact', ''),
                    admissionData.get('allergies', ''),
                    admissionData.get('admissionNotes', '')
                )

                logger.info(f"✅ Created admission recommendation ID: {result['id']}")

                return JSONResponse(content={
                    "success": True,
                    "recommendationId": result['id'],
                    "status": "pending",
                    "message": "Admission recommendation created successfully. Waiting for nursing staff to process.",
                    "createdAt": result["createdAt"].isoformat()
                })

    except Exception as e:
        logger.error(f"❌ Error creating admission recommendation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create admission recommendation: {str(e)}")

@router.get("/recommendations")
async def getAdmissionRecommendations(status: Optional[str] = None):
    """Get admission recommendations with optional status filter"""
    try:
        async with getDbConnection() as conn:
            if status:
                query = """
                SELECT * FROM admissionrecommendations
                WHERE status = $1
                ORDER BY "createdAt" DESC
                """
                rows = await conn.fetch(query, status)
            else:
                query = """
                SELECT * FROM admissionrecommendations
                ORDER BY "createdAt" DESC
                """
                rows = await conn.fetch(query)

            recommendations = []
            for row in rows:
                recDict = dict(row)
                recommendations.append(recDict)

            return JSONResponse(content={
                "success": True,
                "recommendations": recommendations,
                "count": len(recommendations)
            })

    except Exception as e:
        logger.error(f"❌ Error getting admission recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get admission recommendations: {str(e)}")
