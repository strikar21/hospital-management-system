"""
Staff management API endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from ...models.staff import Staff, StaffDB, StaffCreate, StaffUpdate, StaffLogin, StaffLoginResponse
from ...core.database import getDbConnection
from ...core.db_utils import fetchOne, fetchAll, executeQuery
from ...core.security import verify_pin, verify_password, validate_pin_format, validate_staff_id_format, hash_pin, hash_password
from ...services.audit import logAuditEvent
from ...core.auth_dependencies import require_admin, require_any_staff

router = APIRouter(dependencies=[Depends(require_any_staff)])
logger = logging.getLogger(__name__)
# NOTE: Router-level dependency requires ANY staff authentication for ALL endpoints
# Individual endpoints may have additional role requirements (admin, doctor, etc.)

@router.get("/test-simple")
async def testSimple(current_user: dict = Depends(require_any_staff)):
    """Simple test endpoint"""
    logger.info("TEST: Simple endpoint called")
    try:
        async with getDbConnection() as conn:
            logger.info("TEST: Database connection established")
            result = await fetchOne(conn, "SELECT COUNT(*) as count FROM staff")
            logger.info(f"TEST: Query result: {result}")
            return {"message": "Staff router working", "status": "OK", "staffCount": dict(result)['count']}
    except Exception as e:
        logger.error(f"TEST: Error in simple endpoint: {e}")
        import traceback
        logger.error(f"TEST: Traceback: {traceback.format_exc()}")
        return {"error": str(e), "status": "ERROR"}

# REMOVED - DUPLICATE ROUTE WITH auth.py - Use /api/v1/auth/login instead
# async def staffLoginDisabled(loginData: StaffLogin):
    """
    Staff login endpoint - supports staff ID + PIN and password authentication
    """
    logger.info(f"Login attempt for staff ID: {loginData.staffId}")
    try:
        # Validate staff ID format
        if not validate_staff_id_format(loginData.staffId):
            raise HTTPException(
                status_code=400,
                detail="Invalid staff ID format. Must be DOC/NUR/ADM/PRV/TEC followed by 4 digits."
            )
        
        # If PIN is provided, validate format
        if loginData.pin and not validate_pin_format(loginData.pin):
            raise HTTPException(
                status_code=400,
                detail="Invalid PIN format. Must be 4 digits."
            )
        
        # Check that either PIN or password is provided
        if not loginData.pin and not loginData.password and not loginData.nfccardid:
            raise HTTPException(
                status_code=400,
                detail="Either PIN, password, or NFC card is required."
            )
        
        async with getDbConnection() as conn:
            # Try to find staff by ID first, then by NFC card ID
            if loginData.nfcCardId:
                query = """
                SELECT * FROM staff
                WHERE (id = ? OR nfcCardId = ?) AND isActive = true
                """
                staffRow = await fetchOne(conn, query, (loginData.staffId, loginData.nfcCardId))
            else:
                query = 'SELECT * FROM staff WHERE id = $1 AND \"isActive\" = true'
                staffRow = await fetchOne(conn, query, (loginData.staffId,))
            
            if not staffRow:
                # Log failed login attempt
                await logAuditEvent(
                    userId=loginData.staffId,
                    action="LOGIN_FAILED",
                    resourceType="AUTHENTICATION",
                    details=f"Invalid staff ID or NFC card"
                )
                raise HTTPException(
                    status_code=401,
                    detail="Invalid staff credentials"
                )
            
            # Convert row to dict
            staffDict = dict(staffRow) if hasattr(staffRow, 'keys') else staffRow
            
            # If PIN is provided, verify it
            if loginData.pin:
                if not staffDict.get('pin'):
                    raise HTTPException(
                        status_code=401,
                        detail="PIN not set for this staff member"
                    )
                
                if not verify_pin(loginData.pin, staffDict['pin']):
                    await logAuditEvent(
                        userId=loginData.staffId,
                        action="LOGIN_FAILED",
                        resourceType="AUTHENTICATION",
                        details="Invalid PIN"
                    )
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid PIN"
                    )
            
            # If password is provided, verify it
            if loginData.password:
                if not staffDict.get('password'):
                    raise HTTPException(
                        status_code=401,
                        detail="Password not set for this staff member"
                    )
                
                if not verify_password(loginData.password, staffDict['password']):
                    await logAuditEvent(
                        userId=loginData.staffId,
                        action="LOGIN_FAILED",
                        resourceType="AUTHENTICATION",
                        details="Invalid password"
                    )
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid password"
                    )
            
            # Update last seen timestamp
            await executeQuery(conn,
                'UPDATE staff SET lastSeen = CURRENT_TIMESTAMP WHERE id = $1',
                (staffDict['id'],)
            )
            
            # Log successful login
            authMethod = "PIN" if loginData.pin else "Password" if loginData.password else "NFC"
            await logAuditEvent(
                userId=staffDict['id'],
                action="LOGIN_SUCCESS",
                resourceType="AUTHENTICATION",
                details=f"Staff logged in: {staffDict['name']} ({staffDict['role']}) via {authMethod}"
            )
            
            logger.info(f"✅ Staff login successful: {staffDict['name']} ({staffDict['role']}) via {authMethod}")
            
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
        logger.error(f"❌ Login error: {e}")
        logger.error(f"❌ Login error type: {type(e)}")
        import traceback
        logger.error(f"❌ Login error traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.get("/", response_model=List[Staff])
async def getAllStaff(
    current_user: dict = Depends(require_admin),
    role: Optional[str] = Query(None, description="Filter by staff role"),
    department: Optional[str] = Query(None, description="Filter by department"),
    activeOnly: bool = Query(True, description="Show only active staff")
):
    """
    Get all staff members with optional filtering
    """
    try:
        async with getDbConnection() as conn:
            query = "SELECT * FROM staff WHERE 1=1"
            params = []

            paramCount = 0
            if role:
                paramCount += 1
                query += f" AND role = ${paramCount}"
                params.append(role)

            if department:
                paramCount += 1
                query += f" AND department = ${paramCount}"
                params.append(department)

            if activeOnly:
                query += ' AND "isActive" = true'

            query += " ORDER BY \"firstName\", \"lastName\""

            rows = await conn.fetch(query, *params) if params else await conn.fetch(query)

            staffList = []
            for row in rows:
                staffDict = dict(row) if hasattr(row, 'keys') else row
                staffList.append(Staff(**staffDict))

            logger.info(f"👥 Retrieved {len(staffList)} staff members")
            return staffList
            
    except Exception as e:
        logger.error(f"❌ Get staff error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve staff")

@router.get("/{staffId}", response_model=Staff)
async def getStaffMember(staffId: str, current_user: dict = Depends(require_admin)):
    """
    Get a specific staff member
    """
    try:
        async with getDbConnection() as conn:
            query = "SELECT * FROM staff WHERE id = $1"
            staffRow = await conn.fetchrow(query, staffId)
            
            if not staffRow:
                raise HTTPException(status_code=404, detail="Staff member not found")
            
            staffDict = dict(staffRow) if hasattr(staffRow, 'keys') else staffRow
            return Staff(**staffDict)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get staff member error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve staff member")

@router.post("/", response_model=Staff)
async def createStaffMember(staffData: StaffCreate, current_user: dict = Depends(require_admin)):
    """
    Create a new staff member
    """
    try:
        # Extract createdBy from JWT token (current authenticated user)
        createdBy = current_user.get("id")

        # Generate next sequence number for the role
        rolePrefix = {
            "doctor": "DOC",
            "nurse": "NUR",
            "technician": "TEC",
            "administrator": "ADM",
            "provider": "PRV"
        }.get(staffData.role, "STF")

        async with getDbConnection() as conn:
            # Find the next sequence number - FIXED: Use parameterized query to prevent SQL injection
            existingQuery = "SELECT id FROM staff WHERE id LIKE $1 || '%' ORDER BY id DESC LIMIT 1"
            latestRow = await fetchOne(conn, existingQuery, (rolePrefix,))

            if latestRow:
                latestId = latestRow[0] if hasattr(latestRow, '__getitem__') else latestRow
                sequence = int(latestId[-4:]) + 1
            else:
                sequence = 1

            staffId = f"{rolePrefix}{sequence:04d}"

            # Hash PIN and password if provided
            hashedPin = hash_pin(staffData.pin) if staffData.pin else None
            hashedPassword = hash_password(staffData.password) if staffData.password else None

            query = """
                INSERT INTO staff (
                    id, "firstName", "lastName", role, email, "phoneNumber", department,
                    pin, password, "nfcCardId", "isActive", "createdAt", "updatedAt"
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, true, $11, $12)
            """

            now = datetime.now()

            # FIXED: Use transaction to ensure atomicity (staff creation + audit log)
            async with conn.transaction():
                await conn.execute(query,
                    staffId, staffData.firstName, staffData.lastName, staffData.role, staffData.email,
                    staffData.phoneNumber, staffData.department, hashedPin,
                    hashedPassword, staffData.nfcCardId, now, now
                )

                # Log audit event (inside transaction - will rollback if this fails)
                await logAuditEvent(
                    userId=createdBy,
                    action="STAFF_CREATED",
                    resourceType="STAFF",
                    resourceId=staffId,
                    details=f"Created staff: {staffData.firstName} {staffData.lastName} ({staffData.role})"
                )

            # Get the created staff member
            createdRow = await fetchOne(conn, "SELECT * FROM staff WHERE id = $1", (staffId,))
            staffDict = dict(createdRow) if hasattr(createdRow, 'keys') else createdRow

            logger.info(f"✅ Created staff member: {staffId} - {staffData.firstName} {staffData.lastName}")
            return Staff(**staffDict)
            
    except Exception as e:
        logger.error(f"❌ Create staff error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create staff member")

@router.put("/update/{staffId}", response_model=Staff)
async def updateStaffMember(staffId: str, staffData: StaffUpdate, current_user: dict = Depends(require_admin)):
    """
    Update an existing staff member
    """
    try:
        # Extract updatedBy from JWT token (current authenticated user)
        updatedBy = current_user.get("id")

        async with getDbConnection() as conn:
            # Check if staff member exists
            existing = await fetchOne(conn, "SELECT * FROM staff WHERE id = $1", (staffId,))
            if not existing:
                raise HTTPException(status_code=404, detail="Staff member not found")

            # Build update query for non-None fields
            updateFields = []
            params = []

            paramCounter = 1
            for field, value in staffData.dict(exclude_unset=True).items():
                if value is not None:
                    # Hash PIN and password before updating
                    if field == 'pin':
                        updateFields.append(f"{field} = ${paramCounter}")
                        params.append(hash_pin(value))
                    elif field == 'password':
                        updateFields.append(f"{field} = ${paramCounter}")
                        params.append(hash_password(value))
                    else:
                        updateFields.append(f"{field} = ${paramCounter}")
                        params.append(value)
                    paramCounter += 1

            if not updateFields:
                raise HTTPException(status_code=400, detail="No fields to update")

            updateFields.append(f"updatedAt = ${paramCounter}")
            params.append(datetime.now())
            paramCounter += 1
            params.append(staffId)

            query = f"UPDATE staff SET {', '.join(updateFields)} WHERE id = ${paramCounter}"

            # FIXED: Use transaction to ensure atomicity (staff update + audit log)
            async with conn.transaction():
                await conn.execute(query, params)

                # Log audit event (inside transaction)
                await logAuditEvent(
                    userId=updatedBy,
                    action="STAFF_UPDATED",
                    resourceType="STAFF",
                    resourceId=staffId,
                    details=f"Updated staff fields: {list(staffData.dict(exclude_unset=True).keys())}"
                )

            # Get updated staff member
            updatedRow = await fetchOne(conn, "SELECT * FROM staff WHERE id = $1", (staffId,))
            staffDict = dict(updatedRow) if hasattr(updatedRow, 'keys') else updatedRow

            logger.info(f"✅ Updated staff member: {staffId}")
            return Staff(**staffDict)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update staff error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update staff member")

@router.put("/deactivate/{staffId}")
async def deactivateStaffMember(staffId: str, current_user: dict = Depends(require_admin)):
    """
    Deactivate a staff member (soft delete)
    """
    try:
        # Extract deactivatedBy from JWT token (current authenticated user)
        deactivatedBy = current_user.get("id")

        async with getDbConnection() as conn:
            # Check if staff member exists
            existing = await fetchOne(conn, "SELECT * FROM staff WHERE id = $1", (staffId,))
            if not existing:
                raise HTTPException(status_code=404, detail="Staff member not found")

            # FIXED: Use transaction to ensure atomicity (staff deactivation + audit log)
            async with conn.transaction():
                # Deactivate staff member
                await conn.execute(
                    'UPDATE staff SET "isActive" = false, "updatedAt" = $1 WHERE id = $2',
                    datetime.now(), staffId
                )

                # Log audit event (inside transaction)
                await logAuditEvent(
                    userId=deactivatedBy,
                    action="STAFF_DEACTIVATED",
                    resourceType="STAFF",
                    resourceId=staffId,
                    details="Staff member deactivated"
                )

            logger.info(f"✅ Deactivated staff member: {staffId}")
            return {"message": "Staff member deactivated successfully", "staffId": staffId}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Deactivate staff error: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate staff member")

# New staff management endpoints for your requirements

@router.put("/change-pin/{staffId}")
async def changeStaffPin(
    staffId: str,
    current_user: dict = Depends(require_admin),
    newPin: str = Query(..., description="New 4-digit PIN"),
    changedBy: str = Query(..., description="ID of user making the change")
):
    """
    Allow staff to change their PIN (self-service or admin)
    """
    try:
        # Validate PIN format
        if not validate_pin_format(newPin):
            raise HTTPException(status_code=400, detail="Invalid PIN format. Must be 4 digits.")

        async with getDbConnection() as conn:
            # Check if staff member exists
            staffRow = await conn.fetchrow("SELECT * FROM staff WHERE id = $1", staffId)
            if not staffRow:
                raise HTTPException(status_code=404, detail="Staff member not found")

            # Hash the new PIN
            hashedPin = hash_pin(newPin)

            # Update PIN
            await conn.execute(
                'UPDATE staff SET pin = $1, "updatedAt" = $2 WHERE id = $3',
                hashedPin, datetime.now(), staffId
            )

            # Log audit event
            await logAuditEvent(
                userId=changedBy,
                action="PIN_CHANGED",
                resourceType="STAFF",
                resourceId=staffId,
                details=f"PIN changed for staff {staffId}"
            )

            logger.info(f"✅ PIN changed for staff: {staffId}")
            return {"message": "PIN changed successfully", "staffId": staffId}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Change PIN error: {e}")
        raise HTTPException(status_code=500, detail="Failed to change PIN")

@router.put("/change-password/{staffId}")
async def changeStaffPassword(
    staffId: str,
    current_user: dict = Depends(require_admin),
    newPassword: str = Query(..., description="New password"),
    changedBy: str = Query(..., description="ID of user making the change")
):
    """
    Allow staff to change their password (self-service or admin)
    """
    try:
        async with getDbConnection() as conn:
            # Check if staff member exists
            staffRow = await conn.fetchrow("SELECT * FROM staff WHERE id = $1", staffId)
            if not staffRow:
                raise HTTPException(status_code=404, detail="Staff member not found")

            # Hash the new password
            hashedPassword = hash_password(newPassword)

            # Update password
            await conn.execute(
                'UPDATE staff SET password = $1, "updatedAt" = $2 WHERE id = $3',
                hashedPassword, datetime.now(), staffId
            )

            # Log audit event
            await logAuditEvent(
                userId=changedBy,
                action="PASSWORD_CHANGED",
                resourceType="STAFF",
                resourceId=staffId,
                details=f"Password changed for staff {staffId}"
            )

            logger.info(f"✅ Password changed for staff: {staffId}")
            return {"message": "Password changed successfully", "staffId": staffId}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Change password error: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")

@router.put("/toggle-card/{staffId}")
async def toggleStaffCard(
    staffId: str,
    current_user: dict = Depends(require_admin),
    enable: bool = Query(..., description="True to enable card, False to disable"),
    changedBy: str = Query(..., description="ID of user making the change")
):
    """
    Enable or disable staff NFC card access (security management)
    """
    try:
        async with getDbConnection() as conn:
            # Check if staff member exists
            staffRow = await conn.fetchrow('SELECT * FROM staff WHERE id = $1 AND \"isActive\" = true', staffId)
            if not staffRow:
                raise HTTPException(status_code=404, detail="Active staff member not found")

            # Update card status by setting/clearing nfcCardId
            action = "enabled" if enable else "disabled"
            if enable:
                # If enabling, ensure they have a card ID (could generate or restore)
                if not staffRow['nfcCardId']:
                    # Generate a simple card ID if none exists
                    cardId = f"CARD{staffId}_{datetime.now().strftime('%Y%m%d')}"
                    await conn.execute(
                        'UPDATE staff SET "nfcCardId" = $1, "updatedAt" = $2 WHERE id = $3',
                        cardId, datetime.now(), staffId
                    )
                # Card is already enabled if nfcCardId exists
            else:
                # Disable by clearing the card ID
                await conn.execute(
                    'UPDATE staff SET "nfcCardId" = NULL, "updatedAt" = $1 WHERE id = $2',
                    datetime.now(), staffId
                )

            # Log audit event
            await logAuditEvent(
                userId=changedBy,
                action=f"CARD{action.upper()}",
                resourceType="STAFF",
                resourceId=staffId,
                details=f"NFC card access {action} for staff {staffId}"
            )

            logger.info(f"✅ Card {action} for staff: {staffId}")
            return {"message": f"Card access {action} successfully", "staffId": staffId, "cardenabled": enable}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Toggle card error: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle card access")

@router.put("/reassign-department/{staffId}")
async def reassignStaffDepartment(
    staffId: str,
    current_user: dict = Depends(require_admin),
    newDepartment: str = Query(..., description="New department/ward name"),
    changedBy: str = Query(..., description="ID of user making the change")
):
    """
    Reassign staff to different department/ward
    """
    try:
        async with getDbConnection() as conn:
            # Check if staff member exists
            staffRow = await conn.fetchrow("SELECT * FROM staff WHERE id = $1", staffId)
            if not staffRow:
                raise HTTPException(status_code=404, detail="Staff member not found")

            oldDepartment = staffRow['department']

            # Update department
            await conn.execute(
                'UPDATE staff SET department = $1, "updatedAt" = $2 WHERE id = $3',
                newDepartment, datetime.now(), staffId
            )

            # Log audit event
            await logAuditEvent(
                userId=changedBy,
                action="DEPARTMENT_REASSIGNED",
                resourceType="STAFF",
                resourceId=staffId,
                details=f"Staff reassigned from {oldDepartment} to {newDepartment}"
            )

            logger.info(f"✅ Staff {staffId} reassigned from {oldDepartment} to {newDepartment}")
            return {
                "message": "Department reassignment successful",
                "staffId": staffId,
                "oldDepartment": oldDepartment,
                "newDepartment": newDepartment
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Reassign department error: {e}")
        raise HTTPException(status_code=500, detail="Failed to reassign department")

@router.put("/soft-delete/{staffId}")
async def softDeleteStaff(
    staffId: str,
    deletedBy: str = Query(..., description="ID of user performing soft delete")
):
    """
    Soft delete staff (disable login, clear card, keep data)
    """
    try:
        async with getDbConnection() as conn:
            # Check if staff member exists
            staffRow = await conn.fetchrow("SELECT * FROM staff WHERE id = $1", staffId)
            if not staffRow:
                raise HTTPException(status_code=404, detail="Staff member not found")

            # Soft delete: disable login, clear NFC card, keep all data
            await conn.execute(
                'UPDATE staff SET "isActive" = false, "nfcCardId" = NULL, "updatedAt" = $1 WHERE id = $2',
                datetime.now(), staffId
            )

            # Log audit event
            await logAuditEvent(
                userId=deletedBy,
                action="STAFF_SOFT_DELETED",
                resourceType="STAFF",
                resourceId=staffId,
                details=f"Staff soft deleted - login disabled, card cleared, data preserved"
            )

            logger.info(f"✅ Staff soft deleted: {staffId}")
            return {
                "message": "Staff soft deleted successfully",
                "staffId": staffId,
                "note": "Login disabled, card access removed, historical data preserved"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Soft delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to soft delete staff")

# NFC Card Management Endpoints

@router.put("/issue-new-card/{staffId}")
async def issueNewNfcCard(
    staffId: str,
    cardId: str = Query(None, description="Optional custom card ID, auto-generated if not provided"),
    issuedBy: str = Query(..., description="ID of user issuing the card")
):
    """
    Issue a new NFC card to staff (replacement for lost/damaged cards)
    """
    try:
        async with getDbConnection() as conn:
            # Check if staff member exists
            staffRow = await conn.fetchrow("SELECT * FROM staff WHERE id = $1", staffId)
            if not staffRow:
                raise HTTPException(status_code=404, detail="Staff member not found")

            oldCardId = staffRow['nfcCardId']

            # Generate card ID if not provided
            if not cardId:
                from datetime import datetime
                cardId = f"CARD{staffId}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Check if card ID is already in use by another staff member
            existingCard = await conn.fetchrow("SELECT id FROM staff WHERE nfcCardId = $1 AND id != $2", cardId, staffId)
            if existingCard:
                raise HTTPException(status_code=400, detail=f"Card ID {cardId} is already assigned to staff {existingCard['id']}")

            # Issue new card
            await conn.execute(
                'UPDATE staff SET "nfcCardId" = $1, "updatedAt" = $2 WHERE id = $3',
                cardId, datetime.now(), staffId
            )

            # Log audit event
            await logAuditEvent(
                userId=issuedBy,
                action="NEW_CARDISSUED",
                resourceType="STAFF",
                resourceId=staffId,
                details=f"New NFC card issued: {cardId} (replaced: {oldCardId or 'None'})"
            )

            logger.info(f"✅ New card issued to staff {staffId}: {cardId}")
            return {
                "message": "New NFC card issued successfully",
                "staffId": staffId,
                "newCardId": cardId,
                "oldCardId": oldCardId,
                "note": "Old card is automatically deactivated"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Issue new card error: {e}")
        raise HTTPException(status_code=500, detail="Failed to issue new card")

@router.put("/replace-lost-card/{staffId}")
async def replaceLostNfcCard(
    staffId: str,
    reason: str = Query("lost", description="Reason for replacement: lost, damaged, stolen, expired"),
    replacedBy: str = Query(..., description="ID of user processing replacement")
):
    """
    Replace lost/damaged/stolen NFC card with security logging
    """
    try:
        async with getDbConnection() as conn:
            # Check if staff member exists
            staffRow = await conn.fetchrow("SELECT * FROM staff WHERE id = $1", staffId)
            if not staffRow:
                raise HTTPException(status_code=404, detail="Staff member not found")

            oldCardId = staffRow['nfcCardId']

            # Generate new secure card ID
            from datetime import datetime
            import secrets
            newCardId = f"SECURE{staffId}_{datetime.now().strftime('%Y%m%d')}_{secrets.token_hex(4).upper()}"

            # Replace card with new secure ID
            await conn.execute(
                'UPDATE staff SET "nfcCardId" = $1, "updatedAt" = $2 WHERE id = $3',
                newCardId, datetime.now(), staffId
            )

            # Log security audit event
            await logAuditEvent(
                userId=replacedBy,
                action="CARDREPLACED_SECURITY",
                resourceType="STAFF",
                resourceId=staffId,
                details=f"Card replaced due to {reason}. Old: {oldCardId or 'None'}, New: {newCardId}"
            )

            # Log old card as compromised if it existed
            if oldCardId:
                await logAuditEvent(
                    userId=replacedBy,
                    action="CARDCOMPROMISED",
                    resourceType="SECURITY",
                    resourceId=oldCardId,
                    details=f"Card {oldCardId} marked as {reason} for staff {staffId}"
                )

            logger.info(f"🔒 Security card replacement for staff {staffId}: {reason}")
            return {
                "message": f"NFC card replaced successfully due to {reason}",
                "staffId": staffId,
                "newCardId": newCardId,
                "compromisedCardId": oldCardId,
                "reason": reason,
                "securityNote": "Old card is flagged as compromised and deactivated"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Replace lost card error: {e}")
        raise HTTPException(status_code=500, detail="Failed to replace card")

@router.put("/update-card-id/{staffId}")
async def updateNfcCardId(
    staffId: str,
    newCardId: str = Query(..., description="New card ID to assign"),
    updatedBy: str = Query(..., description="ID of user making the update")
):
    """
    Update/change NFC card ID for administrative purposes
    """
    try:
        async with getDbConnection() as conn:
            # Check if staff member exists
            staffRow = await conn.fetchrow("SELECT * FROM staff WHERE id = $1", staffId)
            if not staffRow:
                raise HTTPException(status_code=404, detail="Staff member not found")

            # Validate new card ID format (basic validation)
            if len(newCardId.strip()) < 4:
                raise HTTPException(status_code=400, detail="Card ID must be at least 4 characters")

            # Check if new card ID is already in use
            existingCard = await conn.fetchrow("SELECT id FROM staff WHERE nfcCardId = $1 AND id != $2", newCardId, staffId)
            if existingCard:
                raise HTTPException(status_code=400, detail=f"Card ID {newCardId} is already assigned to staff {existingCard['id']}")

            oldCardId = staffRow['nfcCardId']

            # Update card ID
            await conn.execute(
                'UPDATE staff SET "nfcCardId" = $1, "updatedAt" = $2 WHERE id = $3',
                newCardId, datetime.now(), staffId
            )

            # Log audit event
            await logAuditEvent(
                userId=updatedBy,
                action="CARDID_UPDATED",
                resourceType="STAFF",
                resourceId=staffId,
                details=f"Card ID changed from {oldCardId or 'None'} to {newCardId}"
            )

            logger.info(f"✅ Card ID updated for staff {staffId}: {oldCardId} → {newCardId}")
            return {
                "message": "NFC card ID updated successfully",
                "staffId": staffId,
                "oldCardId": oldCardId,
                "newCardId": newCardId
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update card ID error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update card ID")

@router.get("/card-status/{staffId}")
async def getNfcCardStatus(staffId: str):
    """
    Get current NFC card status for a staff member
    """
    try:
        async with getDbConnection() as conn:
            # Get staff and card info
            staffRow = await conn.fetchrow("SELECT id, name, nfcCardId, isActive, updatedAt FROM staff WHERE id = $1", staffId)
            if not staffRow:
                raise HTTPException(status_code=404, detail="Staff member not found")

            staffDict = dict(staffRow)

            cardId = staffRow['nfcCardId']
            hasCard = bool(cardId)
            cardActive = hasCard and staffRow['isActive']

            return {
                "staffId": staffId,
                "staffname": staffDict['name'],
                "hascard": hasCard,
                "cardid": cardId,
                "cardactive": cardActive,
                "staffactive": staffRow['isActive'],
                "lastupdated": staffRow['updatedAt'],
                "status": "active" if cardActive else "inactive" if hasCard else "noCard"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get card status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get card status")

@router.get("/cards/list")
async def listAllNfcCards(
    activeOnly: bool = Query(True, description="Show only active cards"),
    department: str = Query(None, description="Filter by department")
):
    """
    List all NFC cards in the system (for admin management)
    """
    try:
        async with getDbConnection() as conn:
            query = "SELECT id, name, department, nfcCardId, isActive, updatedAt FROM staff WHERE nfcCardId IS NOT NULL"
            params = []
            paramCount = 0

            if activeOnly:
                query += " AND isActive = true"

            if department:
                paramCount += 1
                query += f" AND department = ${paramCount}"
                params.append(department)

            query += " ORDER BY department, name"

            rows = await conn.fetch(query, *params) if params else await conn.fetch(query)

            cards = []
            for row in rows:
                cards.append({
                    "staffId": row['id'],
                    "staffname": row['name'],
                    "department": row['department'],
                    "cardid": row['nfcCardId'],
                    "isactive": row['isActive'],
                    "lastupdated": row['updatedAt']
                })

            return {
                "totalCards": len(cards),
                "filters": {
                    "activeOnly": activeOnly,
                    "department": department
                },
                "cards": cards
            }

    except Exception as e:
        logger.error(f"❌ List cards error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list cards")

@router.get("/roles/list")
async def getRolesList():
    """
    Get list of available staff roles for frontend dropdown
    """
    try:
        # Standard hospital roles
        roles = [
            "Doctor",
            "Nurse",
            "Administrator",
            "Technician",
            "Provisioner"
        ]
        return {"roles": roles}
    except Exception as e:
        logger.error(f"❌ Get roles error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get roles list")

@router.get("/departments/list")
async def getDepartmentsList():
    """
    Get list of available departments for frontend dropdown
    """
    try:
        async with getDbConnection() as conn:
            # Get unique departments from existing staff
            query = "SELECT DISTINCT department FROM staff WHERE department IS NOT NULL ORDER BY department"
            rows = await conn.fetch(query)

            departments = [row['department'] for row in rows]

            # Add standard departments if not present
            standardDepartments = [
                "Emergency Medicine",
                "ICU",
                "General Ward",
                "Cardiology",
                "Administration",
                "IT Support",
                "IT"
            ]

            for dept in standardDepartments:
                if dept not in departments:
                    departments.append(dept)

            departments.sort()
            return {"departments": departments}

    except Exception as e:
        logger.error(f"❌ Get departments error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get departments list")

@router.get("/generate-id/{role}")
async def generateStaffId(role: str):
    """
    Generate next available staff ID for given role
    """
    try:
        # Role prefix mapping
        rolePrefixes = {
            "doctor": "DOC",
            "nurse": "NUR",
            "administrator": "ADM",
            "technician": "TEC",
            "provisioner": "PRV"
        }

        if role not in rolePrefixes:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

        prefix = rolePrefixes[role]

        async with getDbConnection() as conn:
            # Find highest existing ID for this role
            query = "SELECT id FROM staff WHERE id LIKE $1 ORDER BY id DESC LIMIT 1"
            pattern = f"{prefix}%"

            row = await conn.fetchrow(query, pattern)

            if row:
                # Extract number and increment
                existingId = row['id']
                numberPart = existingId.replace(prefix, '')
                try:
                    nextNumber = int(numberPart) + 1
                except ValueError:
                    nextNumber = 1
            else:
                nextNumber = 1

            # Generate new ID with zero-padding
            newId = f"{prefix}{nextNumber:04d}"

            return {"staffId": newId, "role": role}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Generate ID error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate staff ID")