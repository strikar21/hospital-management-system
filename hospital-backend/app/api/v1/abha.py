"""
ABHA (Ayushman Bharat Health Account) OTP API Endpoints
Uses REAL ABDM API with fallback to mock for testing
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import os
from pydantic import BaseModel

from ...core.auth_dependencies import require_medical_staff, get_current_user
from ...services.abdm_api_client import abdm_client
from ...services.mock_abha_service import mock_abha_service
from ...core.database import getDbConnection

logger = logging.getLogger(__name__)
router = APIRouter()

# Determine if we should use real ABDM or mock
USE_REAL_ABDM = os.getenv("ABDM_USE_REAL", "false").lower() == "true"
HAS_ABDM_CREDENTIALS = bool(os.getenv("ABDM_CLIENT_SECRET"))

if USE_REAL_ABDM and HAS_ABDM_CREDENTIALS:
    logger.info("✅ Using REAL ABDM API")
    abha_service = abdm_client
else:
    logger.info("⚠️ Using MOCK ABHA service (set ABDM_USE_REAL=true and provide ABDM_CLIENT_SECRET to use real ABDM)")
    abha_service = mock_abha_service


# Request/Response Models
class SendOtpRequest(BaseModel):
    patientId: str
    abhaAddress: str  # ABHA Address (username@abdm) - NOT abhaNumber!


class VerifyOtpRequest(BaseModel):
    patientId: str
    txnId: str
    otp: str  # 6-digit OTP


@router.post("/send-otp")
async def sendAbhaOtp(
    request: SendOtpRequest,
    current_user: dict = Depends(require_medical_staff)
):
    """
    Send OTP to patient's ABHA-registered mobile

    REAL ABDM Flow:
    1. Nurse enters patient ID and ABHA Address (username@abdm)
    2. Backend calls ABDM /v1/auth/init
    3. ABDM sends SMS to patient's registered mobile
    4. Returns transaction ID for OTP verification

    Request Body:
    {
        "patientId": "PAT0001",
        "abhaAddress": "rajesh.kumar@abdm"  // ABHA Address (NOT 14-digit number!)
    }

    Response:
    {
        "success": true,
        "txnId": "a825f76b-0696-40f3-864c-5a3a5b389a83",
        "message": "OTP sent to registered mobile",
        "authMode": "MOBILE_OTP",
        "mockOtp": "123456"  // ONLY if using mock
    }
    """
    try:
        logger.info(f"Sending ABHA OTP for patient {request.patientId} ({request.abhaAddress}) by {current_user['id']}")

        # Call ABDM API (real or mock)
        if USE_REAL_ABDM and HAS_ABDM_CREDENTIALS:
            # REAL ABDM API
            result = await abdm_client.init_auth(
                abha_address=request.abhaAddress,
                auth_method="MOBILE_OTP"
            )

            # Store txnId in database
            async with getDbConnection() as conn:
                await conn.execute("""
                    UPDATE abha_sessions
                    SET "otpTxnId" = $1,
                        "otpSentAt" = NOW(),
                        status = 'pending'
                    WHERE "patientId" = $2
                      AND "abhaAddress" = $3
                """, result['txnId'], request.patientId, request.abhaAddress)

            return JSONResponse(content={
                "success": True,
                "txnId": result['txnId'],
                "message": result.get('message', 'OTP sent to registered mobile'),
                "authMode": result.get('authMode', 'MOBILE_OTP')
            })

        else:
            # MOCK ABDM (for testing without credentials)
            result = await mock_abha_service.send_otp(
                patient_id=request.patientId,
                abha_number=request.abhaAddress  # Mock accepts both
            )

            return JSONResponse(content={
                "success": True,
                **result
            })

    except ValueError as e:
        logger.error(f"Invalid ABHA OTP request: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to send ABHA OTP: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send OTP: {str(e)}")


@router.post("/verify-otp")
async def verifyAbhaOtp(
    request: VerifyOtpRequest,
    current_user: dict = Depends(require_medical_staff)
):
    """
    Verify OTP and activate ABHA session

    REAL ABDM Flow:
    1. Nurse enters 6-digit OTP from patient
    2. Backend calls ABDM /v1/auth/confirmWithMobileOTP
    3. If valid: ABDM returns auth token
    4. Store token in abha_sessions table
    5. Patient's vitals will now push to PHR app

    Request Body:
    {
        "patientId": "PAT0001",
        "txnId": "a825f76b-0696-40f3-864c-5a3a5b389a83",
        "otp": "123456"
    }

    Response:
    {
        "success": true,
        "status": "verified",
        "message": "ABHA account linked successfully",
        "patientId": "PAT0001",
        "abhaLinked": true,
        "abhaAddress": "rajesh.kumar@abdm",
        "abhaNumber": "12-3456-7890-1234"
    }
    """
    try:
        logger.info(f"Verifying ABHA OTP for patient {request.patientId} by {current_user['id']}")

        # Call ABDM API (real or mock)
        if USE_REAL_ABDM and HAS_ABDM_CREDENTIALS:
            # REAL ABDM API
            result = await abdm_client.confirm_otp(
                txn_id=request.txnId,
                otp=request.otp
            )

            # Store ABHA session in database
            await abdm_client.link_abha_to_patient(
                patient_id=request.patientId,
                abha_data=result,
                auth_token=result['token'],
                refresh_token=result['refreshToken']
            )

            return JSONResponse(content={
                "success": True,
                "status": "verified",
                "message": "ABHA account linked successfully",
                "patientId": request.patientId,
                "abhaLinked": True,
                "abhaAddress": result.get('healthId'),
                "abhaNumber": result.get('healthIdNumber')
            })

        else:
            # MOCK ABDM
            result = await mock_abha_service.verify_otp(
                txn_id=request.txnId,
                otp=request.otp,
                patient_id=request.patientId
            )

            return JSONResponse(content={
                "success": True,
                "status": result['status'],
                "message": "ABHA account linked successfully",
                "patientId": request.patientId,
                "abhaLinked": True
            })

    except ValueError as e:
        logger.error(f"Invalid ABHA OTP: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to verify ABHA OTP: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify OTP: {str(e)}")


@router.get("/session/{patientId}")
async def getAbhaSession(
    patientId: str,
    current_user: dict = Depends(require_medical_staff)
):
    """
    Get active ABHA session for patient

    Returns session status, ABHA number, token expiry, etc.
    Automatically refreshes token if expired.

    Response:
    {
        "success": true,
        "hasActiveSession": true,
        "session": {
            "patientId": "PAT0001",
            "abhaNumber": "12-3456-7890-1234",
            "abhaAddress": "rajesh.kumar@abdm",
            "status": "active",
            "linkedAt": "2025-11-18T14:30:00Z",
            "tokenExpiresAt": "2025-11-18T15:00:00Z"
        }
    }
    """
    try:
        logger.info(f"Getting ABHA session for patient {patientId}")

        # Use real or mock service
        if USE_REAL_ABDM and HAS_ABDM_CREDENTIALS:
            session = await abdm_client.get_active_session(patientId)
        else:
            session = await mock_abha_service.get_active_session(patientId)

        if not session:
            return JSONResponse(content={
                "success": True,
                "hasActiveSession": False,
                "session": None
            })

        # Convert datetime to ISO string
        if session.get('linkedAt'):
            session['linkedAt'] = session['linkedAt'].isoformat()
        if session.get('tokenExpiresAt'):
            session['tokenExpiresAt'] = session['tokenExpiresAt'].isoformat()
        if session.get('lastPushAt'):
            session['lastPushAt'] = session['lastPushAt'].isoformat()

        # Don't expose sensitive tokens in response
        session.pop('authToken', None)
        session.pop('refreshToken', None)

        return JSONResponse(content={
            "success": True,
            "hasActiveSession": True,
            "session": session
        })

    except Exception as e:
        logger.error(f"Failed to get ABHA session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ABHA session: {str(e)}")


@router.get("/patient-by-mrn/{mrn}")
async def getPatientByMrn(
    mrn: str,
    current_user: dict = Depends(require_medical_staff)
):
    """
    Get patient details by MRN (Medical Record Number)

    This is a convenience endpoint for patient lookup during watch assignment

    Response:
    {
        "success": true,
        "patient": {
            "id": "PAT0001",
            "mrn": "HMS2024000001",
            "firstName": "Rajesh",
            "lastName": "Kumar",
            "phoneNumber": "+91-9876543210",
            "hasAbhaSession": true,
            "abhaNumber": "12-3456-7890-1234",
            "abhaAddress": "rajesh.kumar@abdm"
        }
    }
    """
    try:
        async with getDbConnection() as conn:
            # Get patient by MRN
            patient = await conn.fetchrow("""
                SELECT id, mrn, "firstName", "lastName", "phoneNumber",
                       "dateOfBirth", gender
                FROM patients
                WHERE mrn = $1 AND status = 'active'
            """, mrn)

            if not patient:
                raise HTTPException(status_code=404, detail=f"Patient with MRN {mrn} not found")

            patient_dict = dict(patient)

            # Convert date to string
            if patient_dict.get('dateOfBirth'):
                patient_dict['dateOfBirth'] = patient_dict['dateOfBirth'].isoformat()

            # Check if patient has ABHA session
            if USE_REAL_ABDM and HAS_ABDM_CREDENTIALS:
                session = await abdm_client.get_active_session(patient_dict['id'])
            else:
                session = await mock_abha_service.get_active_session(patient_dict['id'])

            patient_dict['hasAbhaSession'] = session is not None
            patient_dict['abhaNumber'] = session.get('abhaNumber') if session else None
            patient_dict['abhaAddress'] = session.get('abhaAddress') if session else None

            logger.info(f"Found patient by MRN {mrn}: {patient_dict['id']}")

            return JSONResponse(content={
                "success": True,
                "patient": patient_dict
            })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get patient by MRN: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get patient by MRN: {str(e)}")


@router.get("/config")
async def getAbdmConfig(
    current_user: dict = Depends(require_medical_staff)
):
    """
    Get current ABDM configuration

    Returns whether using real ABDM or mock, environment, etc.
    Useful for frontend to display appropriate UI messages.

    Response:
    {
        "success": true,
        "usingRealAbdm": false,
        "environment": "sandbox",
        "hasCredentials": false,
        "message": "Using mock ABHA service for testing"
    }
    """
    return JSONResponse(content={
        "success": True,
        "usingRealAbdm": USE_REAL_ABDM and HAS_ABDM_CREDENTIALS,
        "environment": "sandbox" if abdm_client.USE_SANDBOX else "production",
        "hasCredentials": HAS_ABDM_CREDENTIALS,
        "message": (
            "Connected to ABDM Sandbox" if (USE_REAL_ABDM and HAS_ABDM_CREDENTIALS and abdm_client.USE_SANDBOX)
            else "Connected to ABDM Production" if (USE_REAL_ABDM and HAS_ABDM_CREDENTIALS)
            else "Using mock ABHA service for testing (set ABDM_USE_REAL=true and provide ABDM_CLIENT_SECRET)"
        )
    })
