"""
HMS Integration API Endpoints
Pulls patient data from external Hospital Management System
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
import logging
from pydantic import BaseModel

from ...core.auth_dependencies import require_medical_staff
from ...core.database import getDbConnection
from ...services.hms_adapter import hms_adapter

logger = logging.getLogger(__name__)
router = APIRouter()


class SyncPatientRequest(BaseModel):
    hmsPatientId: str
    assignDevice: bool = False  # If True, also assign device
    deviceId: Optional[str] = None
    roomNumber: Optional[str] = None
    bedNumber: Optional[str] = None


@router.get("/patients")
async def getHmsPatients(
    search: Optional[str] = Query(None, description="Search by name or MRN"),
    hasAbha: Optional[bool] = Query(None, description="Filter by ABHA status"),
    current_user: dict = Depends(require_medical_staff)
):
    """
    Get patient list from external HMS with ABHA information

    This endpoint pulls patients from the configured HMS adapter (CSV, database, or API)
    and returns them with ABHA status for watch assignment workflow.

    Query Parameters:
    - search: Optional search term (firstName, lastName, MRN)
    - hasAbha: Optional filter - true (only with ABHA), false (only without ABHA)

    Returns:
    {
        "success": true,
        "patients": [
            {
                "hmsPatientId": "HMS2024000001",
                "mrn": "MRN001",
                "firstName": "Rajesh",
                "lastName": "Kumar",
                "abhaNumber": "12-3456-7890-1234",
                "abhaAddress": "rajesh.kumar@abdm",
                "hasAbha": true
            }
        ],
        "total": 10,
        "withAbha": 7,
        "withoutAbha": 3
    }
    """
    try:
        if not hms_adapter:
            raise HTTPException(
                status_code=503,
                detail="HMS adapter not configured. Set HMS_ADAPTER_TYPE environment variable."
            )

        logger.info(f"Fetching HMS patients (search={search}, hasAbha={hasAbha}) by {current_user['id']}")

        # Get patients from HMS
        patients = hms_adapter.get_patients(search=search, has_abha=hasAbha)

        # Convert to dict
        patients_data = [p.to_dict() for p in patients]

        # Calculate stats
        total = len(patients_data)
        with_abha = sum(1 for p in patients_data if p['hasAbha'])
        without_abha = total - with_abha

        logger.info(f"Retrieved {total} patients from HMS ({with_abha} with ABHA, {without_abha} without)")

        return JSONResponse(content={
            "success": True,
            "patients": patients_data,
            "total": total,
            "withAbha": with_abha,
            "withoutAbha": without_abha
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch HMS patients: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch HMS patients: {str(e)}")


@router.post("/sync-patient")
async def syncPatientFromHms(
    request: SyncPatientRequest,
    current_user: dict = Depends(require_medical_staff)
):
    """
    Sync single patient from HMS to local vital monitoring database

    This endpoint:
    1. Fetches patient details from HMS (demographics, admission, staff assignments)
    2. Creates patient in local database with all clinical data
    3. Imports medications from HMS
    4. Imports case entries from HMS
    5. If patient has ABHA, creates abha_sessions record
    6. Optionally assigns watch to patient

    Request Body:
    {
        "hmsPatientId": "HMS2024000001",
        "assignDevice": false,  // Optional: also assign device
        "deviceId": "fit-00001",  // Required if assignDevice=true
        "roomNumber": "ICU-101",  // Optional: use HMS room if not provided
        "bedNumber": "B1"  // Optional: use HMS bed if not provided
    }

    Response:
    {
        "success": true,
        "patientId": "PAT0001",
        "created": true,
        "abhaLinked": true,
        "deviceAssigned": false,
        "medicationsImported": 3,
        "caseEntriesImported": 2,
        "patient": {...}
    }
    """
    try:
        if not hms_adapter:
            raise HTTPException(
                status_code=503,
                detail="HMS adapter not configured"
            )

        logger.info(f"Syncing patient {request.hmsPatientId} from HMS by {current_user['id']}")

        # Step 1: Fetch patient from HMS
        hms_patient = hms_adapter.get_patient_by_id(request.hmsPatientId)

        if not hms_patient:
            raise HTTPException(
                status_code=404,
                detail=f"Patient {request.hmsPatientId} not found in HMS"
            )

        # Fetch medications and case entries
        hms_medications = hms_adapter.get_medications_for_patient(hms_patient_id=request.hmsPatientId)
        hms_case_entries = hms_adapter.get_case_entries_for_patient(hms_patient_id=request.hmsPatientId)

        # Step 2: Check if patient already exists in local DB (by MRN)
        async with getDbConnection() as conn:
            existing_patient = await conn.fetchrow("""
                SELECT id, mrn FROM patients WHERE mrn = $1
            """, hms_patient.mrn)

            if existing_patient:
                # Patient already exists - update with HMS data
                patient_id = existing_patient['id']
                created = False
                logger.info(f"Patient {hms_patient.mrn} already exists with ID {patient_id}, updating...")

                await conn.execute("""
                    UPDATE patients SET
                        "firstName" = $1,
                        "lastName" = $2,
                        "dateOfBirth" = $3,
                        gender = $4,
                        "phoneNumber" = $5,
                        "admissionDate" = $6,
                        "roomNumber" = $7,
                        "bedNumber" = $8,
                        "attendingPhysician" = $9,
                        "nurseInCharge" = $10,
                        diagnosis = $11,
                        "bloodType" = $12,
                        allergies = $13,
                        weight = $14,
                        "emergencyContactName" = $15,
                        "emergencyContactPhone" = $16,
                        "medicalHistory" = $17,
                        "currentMedications" = $18,
                        "updatedAt" = NOW()
                    WHERE id = $19
                """,
                    hms_patient.firstName, hms_patient.lastName, hms_patient.dateOfBirth,
                    hms_patient.gender, hms_patient.phoneNumber,
                    hms_patient.admissionDate, hms_patient.roomNumber, hms_patient.bedNumber,
                    hms_patient.attendingPhysician, hms_patient.nurseInCharge,
                    hms_patient.diagnosis, hms_patient.bloodType, hms_patient.allergies,
                    hms_patient.weight,
                    hms_patient.emergencyContactName, hms_patient.emergencyContactPhone,
                    hms_patient.medicalHistory, hms_patient.currentMedications,
                    patient_id
                )

            else:
                # Create new patient with complete HMS data
                patient_id = await conn.fetchval("""
                    INSERT INTO patients (
                        mrn, "firstName", "lastName", "dateOfBirth", gender, "phoneNumber",
                        "admissionDate", "roomNumber", "bedNumber",
                        "attendingPhysician", "nurseInCharge",
                        diagnosis, "bloodType", allergies, weight,
                        "emergencyContactName", "emergencyContactPhone",
                        "medicalHistory", "currentMedications",
                        status, "createdAt"
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6,
                        $7, $8, $9,
                        $10, $11,
                        $12, $13, $14, $15,
                        $16, $17,
                        $18, $19,
                        'active', NOW()
                    )
                    RETURNING id
                """,
                    hms_patient.mrn, hms_patient.firstName, hms_patient.lastName,
                    hms_patient.dateOfBirth, hms_patient.gender, hms_patient.phoneNumber,
                    hms_patient.admissionDate, hms_patient.roomNumber, hms_patient.bedNumber,
                    hms_patient.attendingPhysician, hms_patient.nurseInCharge,
                    hms_patient.diagnosis, hms_patient.bloodType, hms_patient.allergies, hms_patient.weight,
                    hms_patient.emergencyContactName, hms_patient.emergencyContactPhone,
                    hms_patient.medicalHistory, hms_patient.currentMedications
                )
                created = True
                logger.info(f"Created new patient {patient_id} from HMS patient {request.hmsPatientId}")

            # Step 3: Import medications
            medications_imported = 0
            for hms_med in hms_medications:
                # Check if medication already exists
                existing_med = await conn.fetchrow("""
                    SELECT id FROM medications
                    WHERE "patientId" = $1 AND name = $2 AND "prescribedBy" = $3
                """, patient_id, hms_med.medicationName, hms_med.prescribedBy)

                if not existing_med:
                    await conn.execute("""
                        INSERT INTO medications (
                            "patientId", name, dosage, frequency, route,
                            "startDate", duration, "prescribedBy", status, "createdAt"
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                    """,
                        patient_id, hms_med.medicationName, hms_med.dosage, hms_med.frequency,
                        hms_med.route, hms_med.startDate, hms_med.duration,
                        hms_med.prescribedBy, hms_med.status
                    )
                    medications_imported += 1

            logger.info(f"Imported {medications_imported} medications for patient {patient_id}")

            # Step 4: Import case entries
            case_entries_imported = 0
            for hms_case in hms_case_entries:
                # Check if case entry already exists
                existing_case = await conn.fetchrow("""
                    SELECT id FROM "caseEntries"
                    WHERE "patientId" = $1 AND timestamp = $2 AND "performedBy" = $3
                """, patient_id, hms_case.timestamp, hms_case.performedBy)

                if not existing_case:
                    await conn.execute("""
                        INSERT INTO "caseEntries" (
                            "patientId", "entryType", description, findings, recommendations,
                            severity, category, "performedBy", timestamp, "createdAt"
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                    """,
                        patient_id, hms_case.entryType, hms_case.description, hms_case.findings,
                        hms_case.recommendations, hms_case.severity, hms_case.category,
                        hms_case.performedBy, hms_case.timestamp
                    )
                    case_entries_imported += 1

            logger.info(f"Imported {case_entries_imported} case entries for patient {patient_id}")

            # Step 5: If patient has ABHA, create/update abha_sessions
            abha_linked = False
            if hms_patient.hasAbha:
                existing_session = await conn.fetchrow("""
                    SELECT id FROM abha_sessions WHERE "patientId" = $1
                """, patient_id)

                if existing_session:
                    await conn.execute("""
                        UPDATE abha_sessions
                        SET "abhaNumber" = $1, "abhaAddress" = $2,
                            status = 'pending', "linkedAt" = NOW()
                        WHERE "patientId" = $3
                    """, hms_patient.abhaNumber, hms_patient.abhaAddress, patient_id)
                else:
                    await conn.execute("""
                        INSERT INTO abha_sessions (
                            "patientId", "abhaNumber", "abhaAddress",
                            status, "linkedAt", "createdAt"
                        ) VALUES ($1, $2, $3, 'pending', NOW(), NOW())
                    """, patient_id, hms_patient.abhaNumber, hms_patient.abhaAddress)

                abha_linked = True
                logger.info(f"ABHA linked for patient {patient_id}: {hms_patient.abhaAddress}")

            # Step 6: Optionally assign device
            device_assigned = False
            if request.assignDevice:
                if not request.deviceId:
                    raise HTTPException(status_code=400, detail="deviceId required when assignDevice=true")

                # Use HMS room/bed if not provided in request
                room = request.roomNumber or hms_patient.roomNumber
                bed = request.bedNumber or hms_patient.bedNumber

                if not room or not bed:
                    raise HTTPException(status_code=400, detail="roomNumber and bedNumber required")

                await conn.execute("""
                    INSERT INTO deviceassignments (
                        "deviceId", "patientId", "assignedAt", "assignedBy",
                        "roomNumber", "bedNumber"
                    ) VALUES ($1, $2, NOW(), $3, $4, $5)
                """, request.deviceId, patient_id, current_user['id'], room, bed)

                await conn.execute("""
                    UPDATE devices SET status = 'assigned' WHERE "deviceId" = $1
                """, request.deviceId)

                device_assigned = True
                logger.info(f"Device {request.deviceId} assigned to patient {patient_id}")

        return JSONResponse(content={
            "success": True,
            "patientId": patient_id,
            "created": created,
            "abhaLinked": abha_linked,
            "deviceAssigned": device_assigned,
            "medicationsImported": medications_imported,
            "caseEntriesImported": case_entries_imported,
            "patient": {
                "id": patient_id,
                "mrn": hms_patient.mrn,
                "firstName": hms_patient.firstName,
                "lastName": hms_patient.lastName,
                "abhaNumber": hms_patient.abhaNumber,
                "abhaAddress": hms_patient.abhaAddress,
                "hasAbha": hms_patient.hasAbha,
                "roomNumber": hms_patient.roomNumber,
                "bedNumber": hms_patient.bedNumber,
                "attendingPhysician": hms_patient.attendingPhysician,
                "nurseInCharge": hms_patient.nurseInCharge
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync patient from HMS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to sync patient: {str(e)}")


@router.get("/config")
async def getHmsConfig(current_user: dict = Depends(require_medical_staff)):
    """
    Get current HMS integration configuration

    Returns adapter type, status, etc.
    """
    import os

    adapter_type = os.getenv("HMS_ADAPTER_TYPE", "csv")
    csv_path = os.getenv("HMS_CSV_PATH", "data/hms_patients.csv")

    return JSONResponse(content={
        "success": True,
        "adapterType": adapter_type,
        "configured": hms_adapter is not None,
        "csvPath": csv_path if adapter_type == "csv" else None,
        "message": (
            f"HMS adapter configured: {adapter_type}"
            if hms_adapter
            else "HMS adapter not configured"
        )
    })
