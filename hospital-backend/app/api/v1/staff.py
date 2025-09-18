"""
Staff management API endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from ...models.staff import Staff, StaffDB, StaffCreate, StaffUpdate, StaffLogin, StaffLoginResponse
from ...core.database import get_db_connection
from ...core.db_utils import fetch_one, fetch_all, execute_query
from ...core.security import verify_pin, verify_password, validate_pin_format, validate_staff_id_format, hash_pin, hash_password
from ...services.audit import log_audit_event

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/test-simple")
async def test_simple():
    """Simple test endpoint"""
    logger.info("TEST: Simple endpoint called")
    try:
        async with get_db_connection() as conn:
            logger.info("TEST: Database connection established")
            result = await fetch_one(conn, "SELECT COUNT(*) as count FROM staff")
            logger.info(f"TEST: Query result: {result}")
            return {"message": "Staff router working", "status": "OK", "staff_count": dict(result)['count']}
    except Exception as e:
        logger.error(f"TEST: Error in simple endpoint: {e}")
        import traceback
        logger.error(f"TEST: Traceback: {traceback.format_exc()}")
        return {"error": str(e), "status": "ERROR"}

# REMOVED - DUPLICATE ROUTE WITH auth.py - Use /api/v1/auth/login instead
# async def staff_login_disabled(login_data: StaffLogin):
    """
    Staff login endpoint - supports staff ID + PIN and password authentication
    """
    logger.info(f"Login attempt for staff ID: {login_data.staffId}")
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
                WHERE (id = ? OR nfcCardId = ?) AND isActive = true
                """
                staff_row = await fetch_one(conn, query, (login_data.staffId, login_data.nfcCardId))
            else:
                query = "SELECT * FROM staff WHERE id = ? AND isActive = true"
                staff_row = await fetch_one(conn, query, (login_data.staffId,))
            
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
            await execute_query(conn,
                "UPDATE staff SET lastSeen = CURRENT_TIMESTAMP WHERE id = ?",
                (staff_dict['id'],)
            )
            
            # Log successful login
            auth_method = "PIN" if login_data.pin else "Password" if login_data.password else "NFC"
            await log_audit_event(
                user_id=staff_dict['id'],
                action="LOGIN_SUCCESS",
                resource_type="AUTHENTICATION",
                details=f"Staff logged in: {staff_dict['name']} ({staff_dict['role']}) via {auth_method}"
            )
            
            logger.info(f"✅ Staff login successful: {staff_dict['name']} ({staff_dict['role']}) via {auth_method}")
            
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
        logger.error(f"❌ Login error type: {type(e)}")
        import traceback
        logger.error(f"❌ Login error traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.get("/", response_model=List[Staff])
async def get_all_staff(
    role: Optional[str] = Query(None, description="Filter by staff role"),
    department: Optional[str] = Query(None, description="Filter by department"),
    active_only: bool = Query(True, description="Show only active staff")
):
    """
    Get all staff members with optional filtering
    """
    try:
        async with get_db_connection() as conn:
            query = "SELECT * FROM staff WHERE 1=1"
            params = []
            
            param_count = 0
            if role:
                param_count += 1
                query += f" AND role = ${param_count}"
                params.append(role)
            
            if department:
                param_count += 1
                query += f" AND department = ${param_count}"
                params.append(department)
                
            if active_only:
                query += " AND isactive = true"
            
            query += " ORDER BY firstname, lastname"
            
            rows = await conn.fetch(query, *params) if params else await conn.fetch(query)
            
            staff_list = []
            for row in rows:
                staff_dict = dict(row) if hasattr(row, 'keys') else row
                # Create name field from firstname + lastname
                if 'firstname' in staff_dict and 'lastname' in staff_dict:
                    staff_dict['name'] = f"{staff_dict['firstname'] or ''} {staff_dict['lastname'] or ''}".strip()
                staff_list.append(Staff(**staff_dict))
            
            logger.info(f"👥 Retrieved {len(staff_list)} staff members")
            return staff_list
            
    except Exception as e:
        logger.error(f"❌ Get staff error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve staff")

@router.get("/{staff_id}", response_model=Staff)
async def get_staff_member(staff_id: str):
    """
    Get a specific staff member
    """
    try:
        async with get_db_connection() as conn:
            query = "SELECT * FROM staff WHERE id = $1"
            staff_row = await conn.fetchrow(query, staff_id)
            
            if not staff_row:
                raise HTTPException(status_code=404, detail="Staff member not found")
            
            staff_dict = dict(staff_row) if hasattr(staff_row, 'keys') else staff_row
            # Create name field from firstname + lastname
            if 'firstname' in staff_dict and 'lastname' in staff_dict:
                staff_dict['name'] = f"{staff_dict['firstname'] or ''} {staff_dict['lastname'] or ''}".strip()
            return Staff(**staff_dict)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get staff member error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve staff member")

@router.post("/", response_model=Staff)
async def create_staff_member(staff_data: StaffCreate, created_by: str):
    """
    Create a new staff member
    """
    try:
        # Generate next sequence number for the role
        role_prefix = {
            "Doctor": "DOC",
            "Nurse": "NUR", 
            "Technician": "TEC",
            "Administrator": "ADM",
            "Provider": "PRV"
        }.get(staff_data.role, "STF")
        
        async with get_db_connection() as conn:
            # Find the next sequence number
            existing_query = f"SELECT id FROM staff WHERE id LIKE '{role_prefix}%' ORDER BY id DESC LIMIT 1"
            latest_row = await fetch_one(conn, existing_query)
            
            if latest_row:
                latest_id = latest_row[0] if hasattr(latest_row, '__getitem__') else latest_row
                sequence = int(latest_id[-4:]) + 1
            else:
                sequence = 1
                
            staff_id = f"{role_prefix}{sequence:04d}"
            
            # Hash PIN and password if provided
            hashed_pin = hash_pin(staff_data.pin) if staff_data.pin else None
            hashed_password = hash_password(staff_data.password) if staff_data.password else None
            
            query = """
                INSERT INTO staff (
                    id, name, role, email, phoneNumber, department, 
                    pin, password, nfcCardId, isActive, createdAt, updatedAt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, true, ?, ?)
            """
            
            now = datetime.now()
            await conn.execute(query, (
                staff_id, staff_data.name, staff_data.role, staff_data.email,
                staff_data.phoneNumber, staff_data.department, hashed_pin,
                hashed_password, staff_data.nfcCardId, now, now
            ))
            await conn.commit()
            
            # Log audit event
            await log_audit_event(
                user_id=created_by,
                action="STAFF_CREATED",
                resource_type="STAFF",
                resource_id=staff_id,
                details=f"Created staff: {staff_data.name} ({staff_data.role})"
            )
            
            # Get the created staff member
            created_row = await fetch_one(conn, "SELECT * FROM staff WHERE id = ?", (staff_id,))
            staff_dict = dict(created_row) if hasattr(created_row, 'keys') else created_row
            
            logger.info(f"✅ Created staff member: {staff_id} - {staff_data.name}")
            return Staff(**staff_dict)
            
    except Exception as e:
        logger.error(f"❌ Create staff error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create staff member")

# TEMPORARILY COMMENTED OUT - ROUTE ORDERING ISSUE  
# @router.put("/{staff_id}", response_model=Staff)
async def update_staff_member(staff_id: str, staff_data: StaffUpdate, updated_by: str):
    """
    Update an existing staff member
    """
    try:
        async with get_db_connection() as conn:
            # Check if staff member exists
            existing = await fetch_one(conn, "SELECT * FROM staff WHERE id = ?", (staff_id,))
            if not existing:
                raise HTTPException(status_code=404, detail="Staff member not found")
            
            # Build update query for non-None fields
            update_fields = []
            params = []
            
            for field, value in staff_data.dict(exclude_unset=True).items():
                if value is not None:
                    # Hash PIN and password before updating
                    if field == 'pin':
                        update_fields.append(f"{field} = ?")
                        params.append(hash_pin(value))
                    elif field == 'password':
                        update_fields.append(f"{field} = ?")
                        params.append(hash_password(value))
                    else:
                        update_fields.append(f"{field} = ?")
                        params.append(value)
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            update_fields.append("updatedAt = ?")
            params.append(datetime.now())
            params.append(staff_id)
            
            query = f"UPDATE staff SET {', '.join(update_fields)} WHERE id = ?"
            await conn.execute(query, params)
            await conn.commit()
            
            # Log audit event
            await log_audit_event(
                user_id=updated_by,
                action="STAFF_UPDATED",
                resource_type="STAFF",
                resource_id=staff_id,
                details=f"Updated staff fields: {list(staff_data.dict(exclude_unset=True).keys())}"
            )
            
            # Get updated staff member
            updated_row = await fetch_one(conn, "SELECT * FROM staff WHERE id = ?", (staff_id,))
            staff_dict = dict(updated_row) if hasattr(updated_row, 'keys') else updated_row
            
            logger.info(f"✅ Updated staff member: {staff_id}")
            return Staff(**staff_dict)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update staff error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update staff member")

# TEMPORARILY COMMENTED OUT - ROUTE ORDERING ISSUE
# @router.delete("/{staff_id}")
async def deactivate_staff_member(staff_id: str, deactivated_by: str):
    """
    Deactivate a staff member (soft delete)
    """
    try:
        async with get_db_connection() as conn:
            # Check if staff member exists
            existing = await fetch_one(conn, "SELECT * FROM staff WHERE id = ?", (staff_id,))
            if not existing:
                raise HTTPException(status_code=404, detail="Staff member not found")
            
            # Deactivate staff member
            await conn.execute(
                "UPDATE staff SET isActive = false, updatedAt = ? WHERE id = ?",
                (datetime.now(), staff_id)
            )
            await conn.commit()
            
            # Log audit event
            await log_audit_event(
                user_id=deactivated_by,
                action="STAFF_DEACTIVATED",
                resource_type="STAFF",
                resource_id=staff_id,
                details="Staff member deactivated"
            )
            
            logger.info(f"✅ Deactivated staff member: {staff_id}")
            return {"message": "Staff member deactivated successfully", "staffId": staff_id}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Deactivate staff error: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate staff member")