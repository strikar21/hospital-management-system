"""
FHIR R5 Patient Clinical Context API
Endpoints for syncing patient data from HMS for AI vitals analysis
"""

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
from datetime import datetime, date
import logging

from ...services.fhir.patient_clinical_context_service import PatientClinicalContextService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fhir/r5/patient-context", tags=["FHIR R5 - Patient Context"])

# Initialize service
patient_service = PatientClinicalContextService()


# ================================
# HMS SYNC ENDPOINTS
# ================================

@router.post("/sync")
async def syncPatientFromHms(context_data: Dict[str, Any]):
    """
    Sync patient clinical context from HMS

    HMS pushes this when patient is admitted or data changes

    Request body:
    {
        "abhaNumber": "91-1234-5678-9012",
        "mrn": "MRN001",
        "externalPatientUrl": "https://hms.hospital.com/fhir/Patient/123",
        "birthDate": "1985-06-15",
        "gender": "male",
        "weight": 75.5,
        "height": 175,
        "isPregnant": false,
        "comorbidities": {"hypertension": true, "diabetes": false},
        "currentMedications": ["Lisinopril", "Metformin"],
        "allergies": ["Penicillin"],
        "roomNumber": "201",
        "bedNumber": "A",
        "admissionDate": "2025-11-18T10:00:00Z"
    }
    """
    try:
        # Validate required fields
        if not context_data.get('abhaNumber') and not context_data.get('mrn'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either abhaNumber or mrn is required"
            )

        if not context_data.get('birthDate'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="birthDate is required for AI analysis"
            )

        if not context_data.get('gender'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="gender is required for AI analysis"
            )

        # Create or update
        result = await patient_service.create_or_update_from_hms(context_data)

        logger.info(f"✅ Synced patient context: ABHA={context_data.get('abhaNumber')}, MRN={context_data.get('mrn')}")

        return JSONResponse({
            "success": True,
            "patientContextId": str(result['id']),
            "abhaNumber": result.get('abhaNumber'),
            "mrn": result.get('mrn'),
            "syncedAt": result['updatedAt'].isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error syncing patient context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync patient context: {str(e)}"
        )


@router.patch("/{patientContextId}")
async def updatePatientContext(patientContextId: str, updates: Dict[str, Any]):
    """
    Update patient clinical context

    Use for updating weight, room assignment, comorbidities, etc.
    """
    try:
        result = await patient_service.update_context(patientContextId, updates)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient context not found: {patientContextId}"
            )

        logger.info(f"✅ Updated patient context: {patientContextId}")

        return JSONResponse({
            "success": True,
            "patientContextId": str(result['id']),
            "updatedAt": result['updatedAt'].isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating patient context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update patient context: {str(e)}"
        )


# ================================
# QUERY ENDPOINTS
# ================================

@router.get("/{patientContextId}")
async def getPatientContext(patientContextId: str):
    """Get patient clinical context by ID"""
    try:
        result = await patient_service.get_by_id(patientContextId)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient context not found: {patientContextId}"
            )

        return JSONResponse({
            "success": True,
            "patientContext": {
                "id": str(result['id']),
                "abhaNumber": result.get('abhaNumber'),
                "mrn": result.get('mrn'),
                "externalPatientUrl": result.get('externalPatientUrl'),
                "birthDate": result.get('birthDate').isoformat() if result.get('birthDate') else None,
                "gender": result.get('gender'),
                "weight": float(result.get('weight')) if result.get('weight') else None,
                "height": float(result.get('height')) if result.get('height') else None,
                "bmi": float(result.get('bmi')) if result.get('bmi') else None,
                "isPregnant": result.get('isPregnant', False),
                "comorbidities": result.get('comorbidities', {}),
                "currentMedications": result.get('currentMedications', []),
                "allergies": result.get('allergies', []),
                "roomNumber": result.get('roomNumber'),
                "bedNumber": result.get('bedNumber'),
                "admissionDate": result.get('admissionDate').isoformat() if result.get('admissionDate') else None,
                "admissionStatus": result.get('admissionStatus'),
                "lastSyncedFromHms": result.get('lastSyncedFromHms').isoformat() if result.get('lastSyncedFromHms') else None
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting patient context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patient context: {str(e)}"
        )


@router.get("/abha/{abhaNumber}")
async def getPatientByAbha(abhaNumber: str):
    """Get patient context by ABHA number"""
    try:
        result = await patient_service.get_by_abha_number(abhaNumber)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient not found with ABHA: {abhaNumber}"
            )

        return JSONResponse({
            "success": True,
            "patientContextId": str(result['id']),
            "patientContext": {
                "id": str(result['id']),
                "abhaNumber": result.get('abhaNumber'),
                "mrn": result.get('mrn'),
                "roomNumber": result.get('roomNumber'),
                "bedNumber": result.get('bedNumber'),
                "admissionStatus": result.get('admissionStatus')
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting patient by ABHA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patient by ABHA: {str(e)}"
        )


@router.get("/mrn/{mrn}")
async def getPatientByMrn(mrn: str):
    """Get patient context by Medical Record Number"""
    try:
        result = await patient_service.get_by_mrn(mrn)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient not found with MRN: {mrn}"
            )

        return JSONResponse({
            "success": True,
            "patientContextId": str(result['id']),
            "patientContext": {
                "id": str(result['id']),
                "abhaNumber": result.get('abhaNumber'),
                "mrn": result.get('mrn'),
                "roomNumber": result.get('roomNumber'),
                "bedNumber": result.get('bedNumber'),
                "admissionStatus": result.get('admissionStatus')
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting patient by MRN: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patient by MRN: {str(e)}"
        )


@router.get("/room/{roomNumber}/bed/{bedNumber}")
async def getPatientByRoomBed(roomNumber: str, bedNumber: str):
    """Get patient currently in specific room/bed"""
    try:
        result = await patient_service.get_by_room_bed(roomNumber, bedNumber)

        if not result:
            return JSONResponse({
                "success": True,
                "roomNumber": roomNumber,
                "bedNumber": bedNumber,
                "patient": None,
                "message": "No patient currently assigned to this bed"
            })

        return JSONResponse({
            "success": True,
            "roomNumber": roomNumber,
            "bedNumber": bedNumber,
            "patient": {
                "id": str(result['id']),
                "abhaNumber": result.get('abhaNumber'),
                "mrn": result.get('mrn'),
                "admissionDate": result.get('admissionDate').isoformat() if result.get('admissionDate') else None
            }
        })

    except Exception as e:
        logger.error(f"❌ Error getting patient by room/bed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patient by room/bed: {str(e)}"
        )


@router.get("/")
async def getActivePatients(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get all currently admitted patients"""
    try:
        results = await patient_service.get_active_patients(limit=limit, offset=offset)

        patients = []
        for r in results:
            patients.append({
                "id": str(r['id']),
                "abhaNumber": r.get('abhaNumber'),
                "mrn": r.get('mrn'),
                "roomNumber": r.get('roomNumber'),
                "bedNumber": r.get('bedNumber'),
                "admissionDate": r.get('admissionDate').isoformat() if r.get('admissionDate') else None,
                "gender": r.get('gender'),
                "age": patient_service._calculate_age(r['birthDate']) if r.get('birthDate') else None
            })

        return JSONResponse({
            "success": True,
            "count": len(patients),
            "patients": patients
        })

    except Exception as e:
        logger.error(f"❌ Error getting active patients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active patients: {str(e)}"
        )


# ================================
# AI CONTEXT ENDPOINT
# ================================

@router.get("/{patientContextId}/ai-context")
async def getPatientAiContext(patientContextId: str):
    """
    Get patient clinical context optimized for AI vitals analysis

    Returns minimal data needed by AI:
    - age (calculated from birthDate)
    - gender
    - weight, height, BMI
    - pregnancy status
    - comorbidities
    """
    try:
        context = await patient_service.get_clinical_context_for_ai(patientContextId)

        return JSONResponse({
            "success": True,
            "patientContextId": patientContextId,
            "aiContext": context
        })

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"❌ Error getting AI context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get AI context: {str(e)}"
        )


# ================================
# ADMISSION/DISCHARGE
# ================================

@router.post("/{patientContextId}/admit")
async def admitPatient(
    patientContextId: str,
    admission_data: Dict[str, Any]
):
    """
    Admit patient to room/bed

    Request body:
    {
        "roomNumber": "201",
        "bedNumber": "A",
        "admissionDate": "2025-11-18T10:00:00Z"  // optional, defaults to now
    }
    """
    try:
        if not admission_data.get('roomNumber') or not admission_data.get('bedNumber'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="roomNumber and bedNumber are required"
            )

        admission_date = None
        if admission_data.get('admissionDate'):
            admission_date = datetime.fromisoformat(admission_data['admissionDate'].replace('Z', '+00:00'))

        result = await patient_service.admit_patient(
            patientContextId,
            admission_data['roomNumber'],
            admission_data['bedNumber'],
            admission_date
        )

        logger.info(f"✅ Patient admitted: {patientContextId} → Room {admission_data['roomNumber']}, Bed {admission_data['bedNumber']}")

        return JSONResponse({
            "success": True,
            "patientContextId": str(result['id']),
            "roomNumber": result['roomNumber'],
            "bedNumber": result['bedNumber'],
            "admissionDate": result['admissionDate'].isoformat() if result.get('admissionDate') else None
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error admitting patient: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to admit patient: {str(e)}"
        )


@router.post("/{patientContextId}/discharge")
async def dischargePatient(patientContextId: str):
    """Discharge patient (mark as inactive)"""
    try:
        result = await patient_service.discharge_patient(patientContextId)

        logger.info(f"✅ Patient discharged: {patientContextId}")

        return JSONResponse({
            "success": True,
            "patientContextId": str(result['id']),
            "admissionStatus": result['admissionStatus'],
            "active": result['active']
        })

    except Exception as e:
        logger.error(f"❌ Error discharging patient: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discharge patient: {str(e)}"
        )
