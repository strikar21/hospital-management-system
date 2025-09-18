"""
Authentication API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

from ...models.staff import StaffLogin, StaffLoginResponse, Staff
from ...core.database import get_db_connection
from ...core.db_utils import fetch_one, execute_query
from ...core.security import verify_pin, verify_password, validate_pin_format, validate_staff_id_format
from ...services.audit import log_audit_event

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/test")
async def auth_test():
    """Test endpoint to verify auth router is working"""
    logger.info("AUTH TEST: Endpoint reached successfully")
    try:
        async with get_db_connection() as conn:
            result = await fetch_one(conn, "SELECT COUNT(*) as count FROM staff")
            staff_count = dict(result)['count']
            logger.info(f"AUTH TEST: Found {staff_count} staff members")
            return {"message": "Auth router working", "status": "OK", "staff_count": staff_count}
    except Exception as e:
        logger.error(f"AUTH TEST: Database error: {e}")
        import traceback
        logger.error(f"AUTH TEST: Traceback: {traceback.format_exc()}")
        return {"message": "Database error", "error": str(e), "status": "ERROR"}

@router.post("/login", response_model=StaffLoginResponse)
async def staff_login(login_data: StaffLogin):
    """
    Staff login endpoint - supports staff ID + PIN and NFC card authentication
    """
    print(f"AUTH: Login attempt for staff ID: {login_data.staffId}")
    logger.info(f"AUTH: Login attempt for staff ID: {login_data.staffId}")
    try:
        # Validate staff ID format
        if not validate_staff_id_format(login_data.staffId):
            raise HTTPException(
                status_code=400,
                detail="Invalid staff ID format. Must be DOC/NUR/ADM/PRV/TEC followed by 4 digits."
            )
        
        # If PIN is provided, validate format
        if login_data.pin and not validate_pin_format(login_data.pin):
            raise HTTPException(
                status_code=400,
                detail="Invalid PIN format. Must be 4 digits."
            )
        
        # Check that either PIN or password is provided
        if not login_data.pin and not login_data.password and not login_data.nfcCardId:
            raise HTTPException(
                status_code=400,
                detail="Either PIN, password, or NFC card is required."
            )
        
        async with get_db_connection() as conn:
            # Try to find staff by ID first, then by NFC card ID
            if login_data.nfcCardId:
                query = """
                SELECT * FROM staff 
                WHERE (id = $1 OR nfccardid = $2) AND isactive = true
                """
                staff_row = await conn.fetchrow(query, login_data.staffId, login_data.nfcCardId)
            else:
                query = "SELECT * FROM staff WHERE id = $1 AND isactive = true"
                staff_row = await conn.fetchrow(query, login_data.staffId)
            
            if not staff_row:
                # Log failed login attempt
                await log_audit_event(
                    user_id=login_data.staffId,
                    action="LOGIN_FAILED",
                    resource_type="AUTHENTICATION",
                    details=f"Invalid staff ID or NFC card"
                )
                raise HTTPException(
                    status_code=401,
                    detail="Invalid staff credentials"
                )
            
            # Convert row to dict
            staff_dict = dict(staff_row) if hasattr(staff_row, 'keys') else staff_row
            # Create name field from firstname + lastname
            if 'firstname' in staff_dict and 'lastname' in staff_dict:
                staff_dict['name'] = f"{staff_dict['firstname'] or ''} {staff_dict['lastname'] or ''}".strip()
            
            # If PIN is provided, verify it
            if login_data.pin:
                if not staff_dict.get('pin'):
                    raise HTTPException(
                        status_code=401,
                        detail="PIN not set for this staff member"
                    )
                
                if not verify_pin(login_data.pin, staff_dict['pin']):
                    await log_audit_event(
                        user_id=login_data.staffId,
                        action="LOGIN_FAILED",
                        resource_type="AUTHENTICATION",
                        details="Invalid PIN"
                    )
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid PIN"
                    )
            
            # If password is provided, verify it
            if login_data.password:
                if not staff_dict.get('password'):
                    raise HTTPException(
                        status_code=401,
                        detail="Password not set for this staff member"
                    )
                
                if not verify_password(login_data.password, staff_dict['password']):
                    await log_audit_event(
                        user_id=login_data.staffId,
                        action="LOGIN_FAILED",
                        resource_type="AUTHENTICATION",
                        details="Invalid password"
                    )
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid password"
                    )
            
            # Update last seen timestamp
            await conn.execute(
                "UPDATE staff SET lastseen = CURRENT_TIMESTAMP WHERE id = $1",
                staff_dict['id']
            )
            
            # Log successful login
            await log_audit_event(
                user_id=staff_dict['id'],
                action="LOGIN_SUCCESS",
                resource_type="AUTHENTICATION",
                details=f"Staff logged in: {staff_dict['name']} ({staff_dict['role']})"
            )
            
            logger.info(f"✅ Staff login successful: {staff_dict['name']} ({staff_dict['role']})")
            
            return StaffLoginResponse(
                id=staff_dict['id'],
                name=staff_dict['name'],
                role=staff_dict['role'],
                department=staff_dict.get('department'),
                lastSeen=datetime.now()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        import traceback
        logger.error(f"❌ Login error traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.post("/simple-login", response_model=StaffLoginResponse)
async def simple_login(login_data: StaffLogin):
    """Simple login endpoint (alias for main login) - Frontend expects this endpoint"""
    return await staff_login(login_data)

@router.post("/logout")
async def staff_logout(staff_id: str):
    """
    Staff logout endpoint
    """
    try:
        # Log logout event
        await log_audit_event(
            user_id=staff_id,
            action="LOGOUT",
            resource_type="AUTHENTICATION",
            details="Staff logged out"
        )
        
        logger.info(f"🔓 Staff logout: {staff_id}")
        
        return JSONResponse({
            "message": "Logout successful",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Logout error: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")

@router.get("/me/{staff_id}", response_model=Staff)
async def get_current_staff(staff_id: str):
    """
    Get current staff information
    """
    try:
        async with get_db_connection() as conn:
            query = "SELECT * FROM staff WHERE id = $1 AND isactive = true"
            staff_row = await conn.fetchrow(query, staff_id)
            
            if not staff_row:
                raise HTTPException(status_code=404, detail="Staff not found")
            
            staff_dict = dict(staff_row) if hasattr(staff_row, 'keys') else staff_row
            # Create name field from firstname + lastname
            if 'firstname' in staff_dict and 'lastname' in staff_dict:
                staff_dict['name'] = f"{staff_dict['firstname'] or ''} {staff_dict['lastname'] or ''}".strip()
            
            return Staff(**staff_dict)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get staff error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get staff information")

@router.post("/nfc-tap")
async def nfc_tap_login(nfc_card_id: str):
    """
    NFC card tap authentication
    """
    try:
        async with get_db_connection() as conn:
            query = "SELECT * FROM staff WHERE nfccardid = $1 AND isactive = true"
            staff_row = await conn.fetchrow(query, nfc_card_id)
            
            if not staff_row:
                await log_audit_event(
                    user_id="unknown",
                    action="NFC_TAP_FAILED",
                    resource_type="AUTHENTICATION",
                    details=f"Invalid NFC card ID: {nfc_card_id}"
                )
                raise HTTPException(status_code=401, detail="Invalid NFC card")
            
            staff_dict = dict(staff_row) if hasattr(staff_row, 'keys') else staff_row
            # Create name field from firstname + lastname
            if 'firstname' in staff_dict and 'lastname' in staff_dict:
                staff_dict['name'] = f"{staff_dict['firstname'] or ''} {staff_dict['lastname'] or ''}".strip()
            
            # Update last seen
            await conn.execute(
                "UPDATE staff SET lastseen = CURRENT_TIMESTAMP WHERE id = $1",
                staff_dict['id']
            )
            
            # Log NFC tap
            await log_audit_event(
                user_id=staff_dict['id'],
                action="NFC_TAP_SUCCESS",
                resource_type="AUTHENTICATION",
                details=f"NFC tap login: {staff_dict['name']}"
            )
            
            logger.info(f"📱 NFC tap login: {staff_dict['name']} ({staff_dict['role']})")
            
            return StaffLoginResponse(
                id=staff_dict['id'],
                name=staff_dict['name'],
                role=staff_dict['role'],
                department=staff_dict.get('department'),
                lastSeen=datetime.now()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ NFC tap error: {e}")
        raise HTTPException(status_code=500, detail="NFC authentication failed")