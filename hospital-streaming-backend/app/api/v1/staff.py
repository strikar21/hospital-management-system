from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional, List
from datetime import datetime
from app.services.staff_service import StaffService
from app.schemas.staff import (
    StaffCreate, StaffUpdate, StaffResponse, StaffCreationResponse, StaffLogin, StaffListResponse, PasswordChange
)
from app.core.security import StaffAuthenticator, authenticate_staff_token
import urllib.parse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/staff")

# IMPORTANT: Specific routes MUST come before generic routes with path parameters
# This ensures that /generate-id/role doesn't get caught by /{staff_id}

@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify router registration"""
    logger.info("Staff test endpoint called")
    return {"message": "Test endpoint working", "status": "success"}

@router.get("/debug/{test_id}")
async def debug_endpoint(test_id: str):
    """Debug endpoint to test parameter routing"""
    logger.info(f"Debug endpoint called with test_id: {test_id}")
    
    # Test database connectivity
    from app.db.database import database
    try:
        result = await database.fetch_one('SELECT 1 as test')
        db_status = f"DB Connected: {result['test']}"
    except Exception as e:
        db_status = f"DB Error: {e}"
    
    return {"message": f"Debug endpoint working with ID: {test_id}", "db_status": db_status, "status": "success"}

@router.get("/generate-id/{role}")
async def generate_staff_id_preview(role: str):
    """Generate next available staff ID for a given role (preview only)"""
    try:
        # URL decode the role
        role = urllib.parse.unquote(role)
        
        next_id = await StaffService.generate_staff_id(role)
        role_code = StaffService.ROLE_CODES.get(role, role.replace(" ", "")[:3].upper())
        
        return {
            "next_staff_id": next_id,
            "role_code": role_code,
            "role": role,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating staff ID: {str(e)}"
        )

@router.get("/test-staff/{test_id}")
async def test_staff_route(test_id: str):
    """Test route to verify routing works"""
    return {"message": f"Test staff route called with {test_id}", "status": "success"}

@router.get("/roles/list")
async def get_roles():
    """Get list of available roles"""
    return {
        "roles": [
            # Medical Staff - Simple
            "Doctor", "Consultant", "Resident", "Intern",
            
            # Nursing Staff - Simple
            "Nurse", "Staff Nurse", "Nursing Assistant",
            
            # Technical Staff - Simple
            "Technician", "Lab Technician", "Radiology Technician", "IT Technician",
            
            # Administrative Staff - Simple
            "Admin", "Administrator", "Receptionist",
            
            # Support Staff - Simple
            "Pharmacist", "Physiotherapist", "Security", "Maintenance",
            
            # Provisioning Staff
            "Provisioner"
        ]
    }

@router.get("/departments/list")
async def get_departments():
    """Get list of available departments"""
    return {
        "departments": [
            "Cardiology", "Neurology", "Orthopedics", "Gynecology", "General Surgery",
            "Pediatrics", "Pulmonology", "Dermatology", "Gastroenterology", "Endocrinology",
            "Emergency Medicine", "Psychiatry", "Internal Medicine", "Oncology", "Radiology",
            "Laboratory", "Pharmacy", "Physiotherapy", "Nursing", "Administration"
        ]
    }

@router.post("/", response_model=StaffCreationResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(staff_data: StaffCreate):
    """Create a new staff member"""
    try:
        staff = await StaffService.create_staff(staff_data)
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create staff member"
            )
        return staff
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/", response_model=StaffListResponse)
async def get_staff(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Items per page"),
    department: Optional[str] = Query(None, description="Filter by department"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """Get staff list with optional filtering"""
    result = await StaffService.list_staff(
        page=page,
        page_size=size,
        department=department,
        role=role,
        is_active=is_active
    )
    return StaffListResponse(**result)

@router.get("/nfc/{nfc_id}", response_model=StaffResponse)
async def get_staff_by_nfc(nfc_id: str):
    """Get staff member by NFC ID"""
    staff = await StaffService.get_staff_by_nfc(nfc_id)
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    return staff

@router.post("/login")
async def staff_login(login_data: StaffLogin):
    """Staff login endpoint - supports password, PIN, or NFC authentication"""
    try:
        staff = await StaffService.authenticate_staff(
            login_data.staff_id, 
            login_data.password, 
            login_data.pin,
            login_data.nfc_id
        )
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Include auth type info in response
        auth_type = "nfc" if login_data.nfc_id else ("password" if login_data.password else "pin")
        requires_password = StaffService.requires_password(staff.role)
        requires_pin = StaffService.requires_pin(staff.role)
        
        # Generate JWT access token
        access_token = StaffAuthenticator.create_staff_access_token({
            "id": staff.id,
            "staff_id": staff.staff_id,
            "name": staff.name,
            "role": staff.role,
            "department": staff.department
        })
        
        return {
            "message": "Login successful", 
            "staff": staff,
            "access_token": access_token,
            "token_type": "bearer",
            "auth_type": auth_type,
            "role_auth_info": {
                "requires_password": requires_password,
                "requires_pin": requires_pin
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# IMPORTANT: Put specific /{staff_id}/... routes BEFORE generic /{staff_id} routes
@router.put("/{staff_id}/change-password")
async def change_password(staff_id: str, password_data: PasswordChange):
    """Change staff member password"""
    try:
        success = await StaffService.change_password(
            staff_id, 
            password_data.current_password, 
            password_data.new_password
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid current password or staff member not found"
            )
        return {"message": "Password changed successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# IMPORTANT: Put generic /{staff_id} routes LAST to avoid catching specific routes
@router.get("/{staff_id}")
async def get_staff_by_id(staff_id: str):
    """Get staff member by staff ID"""
    
    # Simple test - just return the staff_id
    return {"message": f"Staff ID received: {staff_id}", "status": "success"}
    
    # For other staff, try the service
    staff = await StaffService.get_staff_by_id(staff_id)
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    return staff

@router.put("/{staff_id}", response_model=StaffResponse)
async def update_staff(staff_id: str, staff_data: StaffUpdate):
    """Update staff member"""
    try:
        staff = await StaffService.update_staff(staff_id, staff_data)
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff member not found"
            )
        return staff
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{staff_id}")
async def deactivate_staff(staff_id: str):
    """Deactivate staff member (soft delete)"""
    try:
        success = await StaffService.deactivate_staff(staff_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff member not found"
            )
        return {"message": "Staff member deactivated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )