"""
Authentication API endpoints
"""

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
import json

from ...models.staff import StaffLogin, StaffLoginResponse, Staff
from ...core.database import getDbConnection
from ...core.db_utils import fetchOne
from ...core.security import verify_pin, verify_password, validate_pin_format, validate_staff_id_format
from ...services.audit import logAuditEvent

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/simple-test")
async def simpleTest(data: dict):
    """Ultra simple test endpoint to verify POST requests work"""
    print(f"SIMPLE TEST: Received data: {data}")
    return {"message": "POST works", "received": data}

@router.post("/debug-auth")
async def debugAuth(request: Request):
    """Debug auth endpoint - always succeeds"""
    try:
        body = await request.body()
        requestData = json.loads(body.decode('utf-8'))
        print(f"DEBUG AUTH: Received: {requestData}")

        return {
            "id": "DOC0001",
            "name": "Dr. Sarah Johnson",
            "role": "doctor",
            "department": "Cardiology",
            "lastSeen": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"DEBUG AUTH ERROR: {e}")
        return {"error": str(e)}

@router.get("/test")
async def authTest():
    """Test endpoint to verify auth router is working"""
    logger.info("AUTH TEST: Endpoint reached successfully")
    try:
        async with getDbConnection() as conn:
            result = await fetchOne(conn, "SELECT COUNT(*) as count FROM staff")
            staffCount = dict(result)['count']
            logger.info(f"AUTH TEST: Found {staffCount} staff members")
            return {"message": "Auth router working", "status": "OK", "staffCount": staffCount}
    except Exception as e:
        logger.error(f"AUTH TEST: Database error: {e}")
        import traceback
        logger.error(f"AUTH TEST: Traceback: {traceback.format_exc()}")
        return {"message": "Database error", "error": str(e), "status": "ERROR"}

@router.post("/login", response_model=StaffLoginResponse)
async def staffLogin(loginData: StaffLogin):
    """
    Staff login endpoint - supports staff ID + PIN and NFC card authentication - Uses middleware transformation
    """
    print("AUTH: Staff login endpoint called")
    logger.info("AUTH: Staff login endpoint called")
    print(f"AUTH: Received loginData: {loginData}")
    logger.info(f"AUTH: Received loginData: {loginData}")

    staffId = loginData.staffId
    pin = loginData.pin
    password = loginData.password
    nfcCardId = loginData.nfcCardId

    print(f"AUTH: Login attempt for staff ID: {staffId}")
    logger.info(f"AUTH: Login attempt for staff ID: {staffId}")
    try:
        # Validate staff ID format
        if not validate_staff_id_format(staffId):
            raise HTTPException(
                status_code=400,
                detail="Invalid staff ID format. Must be DOC/NUR/ADM/PRV/TEC followed by 4 digits."
            )

        # If PIN is provided, validate format
        if pin and not validate_pin_format(pin):
            raise HTTPException(
                status_code=400,
                detail="Invalid PIN format. Must be 4 digits."
            )

        # Check that either PIN or password is provided
        if not pin and not password and not nfcCardId:
            raise HTTPException(
                status_code=400,
                detail="Either PIN, password, or NFC card is required."
            )
        
        async with getDbConnection() as conn:
            # Try to find staff by ID first, then by NFC card ID
            if nfcCardId:
                query = """
                SELECT * FROM staff
                WHERE (id = $1 OR "nfcCardId" = $2) AND "isActive" = true
                """
                staffRow = await conn.fetchrow(query, staffId, nfcCardId)
            else:
                query = 'SELECT * FROM staff WHERE id = $1 AND "isActive" = true'
                staffRow = await conn.fetchrow(query, staffId)
            
            if not staffRow:
                # Log failed login attempt (temporarily disabled for debugging)
                try:
                    await logAuditEvent(
                        userId=staffId,
                        action="LOGIN_FAILED",
                        resourceType="AUTHENTICATION",
                        details="Invalid staff ID or NFC card"
                    )
                except Exception as audit_e:
                    logger.warning(f"Audit logging failed: {audit_e}")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid staff credentials"
                )
            
            # Convert row to dict
            staffDict = dict(staffRow) if hasattr(staffRow, 'keys') else staffRow
            
            # If PIN is provided, verify it
            if pin:
                if not staffDict.get('pin'):
                    raise HTTPException(
                        status_code=401,
                        detail="PIN not set for this staff member"
                    )

                if not verify_pin(pin, staffDict['pin']):
                    try:
                        await logAuditEvent(
                            userId=staffId,
                            action="LOGIN_FAILED",
                            resourceType="AUTHENTICATION",
                            details="Invalid PIN"
                        )
                    except Exception as audit_e:
                        logger.warning(f"Audit logging failed: {audit_e}")
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid PIN"
                    )

            # If password is provided, verify it
            if password:
                if not staffDict.get('password'):
                    raise HTTPException(
                        status_code=401,
                        detail="Password not set for this staff member"
                    )

                if not verify_password(password, staffDict['password']):
                    try:
                        await logAuditEvent(
                            userId=staffId,
                            action="LOGIN_FAILED",
                            resourceType="AUTHENTICATION",
                            details="Invalid password"
                        )
                    except Exception as audit_e:
                        logger.warning(f"Audit logging failed: {audit_e}")
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid password"
                    )
            
            # Update last seen timestamp
            await conn.execute(
                'UPDATE staff SET "lastSeen" = CURRENT_TIMESTAMP WHERE id = $1',
                staffDict['id']
            )
            
            # Log successful login
            try:
                await logAuditEvent(
                    userId=staffDict['id'],
                    action="LOGIN_SUCCESS",
                    resourceType="AUTHENTICATION",
                    details=f"Staff logged in: {staffDict['name']} ({staffDict['role']})"
                )
            except Exception as audit_e:
                logger.warning(f"Audit logging failed: {audit_e}")
            
            logger.info(f"Staff login successful: {staffDict['firstName']} {staffDict['lastName']} ({staffDict['role']})")

            return StaffLoginResponse(
                id=staffDict['id'],
                firstName=staffDict['firstName'],
                lastName=staffDict['lastName'],
                role=staffDict['role'],
                department=staffDict.get('department'),
                lastSeen=datetime.now()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LOGIN ERROR: {e}", exc_info=True)
        import traceback
        logger.error(f"LOGIN ERROR TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/logout")
async def staffLogout(staffId: str):
    """
    Staff logout endpoint
    """
    try:
        # Log logout event
        await logAuditEvent(
            userId=staffId,
            action="LOGOUT",
            resourceType="AUTHENTICATION",
            details="Staff logged out"
        )
        
        logger.info(f"🔓 Staff logout: {staffId}")
        
        return JSONResponse({
            "message": "Logout successful",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Logout error: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")

@router.get("/me/{staffId}", response_model=Staff)
async def getCurrentStaff(staffId: str):
    """
    Get current staff information
    """
    try:
        async with getDbConnection() as conn:
            query = 'SELECT * FROM staff WHERE id = $1 AND "isActive" = true'
            staffRow = await conn.fetchrow(query, staffId)

            if not staffRow:
                raise HTTPException(status_code=404, detail="Staff not found")

            staffDict = dict(staffRow) if hasattr(staffRow, 'keys') else staffRow
            # Create name field from "firstName" and "lastName"
            staffDict['name'] = f"{staffDict.get('firstName', '') or ''} {staffDict.get('lastName', '') or ''}".strip()
            
            return Staff(**staffDict)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get staff error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get staff information")

@router.get("/check-type")
async def checkAuthType(staffId: str = Query(..., description="Staff ID to check auth methods")):
    """
    Check what authentication methods are available for a staff member
    Used by HybridLogin.tsx
    """
    try:
        # Validate staff ID format
        if not validate_staff_id_format(staffId):
            raise HTTPException(
                status_code=400,
                detail="Invalid staff ID format. Must be DOC/NUR/ADM/PRV/TEC followed by 4 digits."
            )

        async with getDbConnection() as conn:
            query = 'SELECT pin, password, "nfcCardId" FROM staff WHERE id = $1 AND "isActive" = true'
            staffRow = await conn.fetchrow(query, staffId)

            if not staffRow:
                raise HTTPException(status_code=404, detail="Staff not found")

            staffDict = dict(staffRow) if hasattr(staffRow, 'keys') else staffRow

            # Determine available authentication methods
            authMethods = []
            if staffDict.get('pin'):
                authMethods.append('pin')
            if staffDict.get('password'):
                authMethods.append('password')
            if staffDict.get('nfcCardId'):
                authMethods.append('nfc')

            logger.info(f"🔍 Auth check for {staffId}: {authMethods}")

            return {
                "authMethods": authMethods,
                "staffId": staffId,
                "hasPin": bool(staffDict.get('pin')),
                "hasPassword": bool(staffDict.get('password')),
                "hasNfc": bool(staffDict.get('nfcCardId'))
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Check auth type error: {e}")
        raise HTTPException(status_code=500, detail="Failed to check authentication methods")

@router.post("/nfc")
async def authenticateNfc(nfcData: dict):
    """
    Authenticate staff using NFC card
    Used by Login.tsx
    """
    try:
        nfcCardId = nfcData.get('nfcId')
        if not nfcCardId:
            raise HTTPException(status_code=400, detail="NFC card ID is required")

        async with getDbConnection() as conn:
            query = 'SELECT * FROM staff WHERE "nfcCardId" = $1 AND "isActive" = true'
            staffRow = await conn.fetchrow(query, nfcCardId)

            if not staffRow:
                await logAuditEvent(
                    userId="unknown",
                    action="NFC_AUTH_FAILED",
                    resourceType="AUTHENTICATION",
                    details=f"Invalid NFC card ID: {nfcCardId}"
                )
                raise HTTPException(status_code=401, detail="Invalid NFC card")

            staffDict = dict(staffRow) if hasattr(staffRow, 'keys') else staffRow

            # Update last seen
            await conn.execute(
                'UPDATE staff SET "lastSeen" = CURRENT_TIMESTAMP WHERE id = $1',
                staffDict['id']
            )

            # Log NFC authentication
            await logAuditEvent(
                userId=staffDict['id'],
                action="NFC_AUTH_SUCCESS",
                resourceType="AUTHENTICATION",
                details=f"NFC authentication: {staffDict['firstName']} {staffDict['lastName']}"
            )

            logger.info(f"📱 NFC authentication: {staffDict['firstName']} {staffDict['lastName']} ({staffDict['role']})")

            return StaffLoginResponse(
                id=staffDict['id'],
                firstName=staffDict['firstName'],
                lastName=staffDict['lastName'],
                role=staffDict['role'],
                department=staffDict.get('department'),
                lastSeen=datetime.now()
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ NFC authentication error: {e}")
        raise HTTPException(status_code=500, detail="NFC authentication failed")

@router.post("/nfc-tap")
async def nfcTapLogin(nfcCardId: str):
    """
    NFC card tap authentication (legacy endpoint)
    """
    try:
        async with getDbConnection() as conn:
            query = 'SELECT * FROM staff WHERE "nfcCardId" = $1 AND "isActive" = true'
            staffRow = await conn.fetchrow(query, nfcCardId)

            if not staffRow:
                await logAuditEvent(
                    userId="unknown",
                    action="NFC_TAP_FAILED",
                    resourceType="AUTHENTICATION",
                    details=f"Invalid NFC card ID: {nfcCardId}"
                )
                raise HTTPException(status_code=401, detail="Invalid NFC card")

            staffDict = dict(staffRow) if hasattr(staffRow, 'keys') else staffRow
            # Create name field from "firstName" and "lastName"
            staffDict['name'] = f"{staffDict.get('firstName', '') or ''} {staffDict.get('lastName', '') or ''}".strip()

            # Update last seen
            await conn.execute(
                'UPDATE staff SET "lastSeen" = CURRENT_TIMESTAMP WHERE id = $1',
                staffDict['id']
            )

            # Log NFC tap
            await logAuditEvent(
                userId=staffDict['id'],
                action="NFC_TAP_SUCCESS",
                resourceType="AUTHENTICATION",
                details=f"NFC tap login: {staffDict['name']}"
            )

            logger.info(f"📱 NFC tap login: {staffDict['name']} ({staffDict['role']})")

            return StaffLoginResponse(
                id=staffDict['id'],
                name=staffDict['name'],
                role=staffDict['role'],
                department=staffDict.get('department'),
                lastSeen=datetime.now()
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ NFC tap error: {e}")
        raise HTTPException(status_code=500, detail="NFC authentication failed")