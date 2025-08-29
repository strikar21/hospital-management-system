from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from datetime import datetime, timedelta
from passlib.context import CryptContext

from app.schemas.patient import StaffLogin, StaffLoginResponse, StaffResponse
from app.models.staff import Staff
from app.db.database import database
from app.core.security import DeviceAuthenticator, StaffAuthenticator

router = APIRouter(prefix="/auth")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/login", response_model=StaffLoginResponse)
async def staff_login(credentials: StaffLogin):
    """Staff login with credentials - matches frontend expectations"""
    
    # For now, accept universal password for compatibility
    universal_password = "hospital123"
    
    # Try database authentication first, fallback to mock data if DB unavailable
    staff = None
    try:
        # Query staff by staff_id
        query = select(Staff).where(
            Staff.staffId == credentials.staffId,
            Staff.isActive == True
        )
        staff = await database.fetch_one(query)
    except Exception as e:
        # Database not available, use mock data for development
        if credentials.staffId and credentials.password == universal_password:
            # Create mock staff data
            mock_staff = {
                "id": credentials.staffId,
                "staffId": credentials.staffId,
                "firstName": "Test",
                "lastName": "User", 
                "role": "doctor",
                "email": f"{credentials.staff_id}@hospital.com",
                "phone": "555-0000",
                "department": "General",
                "specialization": "General Medicine",
                "shift": "day",
                "isActive": True,
                "nfcId": "dev-nfc-001"
            }
            staff = mock_staff
    
    if not staff:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password (accept universal password or hashed password)
    if credentials.password != universal_password:
        if staff.passwordHash:
            if not pwd_context.verify(credentials.password, staff.passwordHash):
                raise HTTPException(status_code=401, detail="Invalid credentials")
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Handle both dict (mock) and object (database) formats
    if isinstance(staff, dict):
        staffId = staff.get("staffId")
        userId = staff.get("id")
        name = f"{staff.get('firstName', '')} {staff.get('lastName', '')}".strip()
        role = staff.get("role")
        department = staff.get("department")
    else:
        staffId = staff.staffId
        userId = staff.id
        name = staff.name
        role = staff.role
        department = staff.department
    
    # Generate JWT token for session
    accessToken = DeviceAuthenticator.create_device_jwt(
        deviceId=f"staff_{staffId}",
        deviceType="staff_session"
    )
    
    return StaffLoginResponse(
        userId=userId,
        name=name,
        role=role,
        department=department,
        accessToken=accessToken
    )

@router.post("/nfc")
async def nfc_login(nfc_data: dict):
    """NFC-based authentication with JWT token - matches frontend expectations"""
    
    nfcId = nfc_data.get("nfcId")
    if not nfcId:
        raise HTTPException(status_code=400, detail="NFC ID required")
    
    # Query staff by NFC ID
    query = select(Staff).where(
        Staff.nfcId == nfcId,
        Staff.isActive == True
    )
    staff = await database.fetch_one(query)
    
    if not staff:
        raise HTTPException(status_code=401, detail="Invalid NFC ID")
    
    # Generate JWT access token
    accessToken = StaffAuthenticator.create_staff_access_token({
        "id": staff.id,
        "staffId": staff.staffId,
        "name": staff.name,
        "role": staff.role,
        "department": staff.department
    })
    
    return {
        "userId": staff.id,
        "staffId": staff.staffId,
        "name": staff.name,
        "role": staff.role,
        "department": staff.department,
        "accessToken": accessToken,
        "tokenType": "bearer"
    }

@router.get("/validate-token")
async def validate_token(token: str):
    """Validate staff session token"""
    
    try:
        payload = DeviceAuthenticator.verify_device_jwt(token)
        
        if payload.get("type") != "staffSession":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        # Extract staff ID from deviceId
        deviceId = payload.get("deviceId", "")
        if not deviceId.startswith("staff_"):
            raise HTTPException(status_code=401, detail="Invalid token")
        
        staffId = deviceId.replace("staff_", "")
        
        # Get staff details
        query = select(Staff).where(
            Staff.staffId == staffId,
            Staff.isActive == True
        )
        staff = await database.fetch_one(query)
        
        if not staff:
            raise HTTPException(status_code=401, detail="Staff not found")
        
        return StaffResponse.from_orm(staff)
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/demo-credentials")
async def get_demo_credentials():
    """Get demo credentials for testing - matches frontend expectations"""
    
    demo_creds = [
        { 'staffId': 'ADMIN001', 'role': 'Hospital Administrator', 'name': 'Mr. Ramesh Choudhary', 'nfc': 'NFC_ADMIN001' },
        { 'staffId': 'ADMIN002', 'role': 'Hospital Administrator', 'name': 'Ms. Priya Singh', 'nfc': 'NFC_ADMIN002' },
        { 'staffId': 'ADMIN003', 'role': 'Hospital Administrator', 'name': 'Dr. Suresh Kumar', 'nfc': 'NFC_ADMIN003' },
        { 'staffId': 'DOC001', 'role': 'Doctor', 'name': 'Dr. Sarah Johnson', 'nfc': 'NFC001' },
        { 'staffId': 'NUR001', 'role': 'Nurse', 'name': 'Nurse Amy Chen', 'nfc': 'NFC002' },
        { 'staffId': 'ADM001', 'role': 'Admin', 'name': 'Admin Mike Wilson', 'nfc': 'NFC003' },
        { 'staffId': 'TEC001', 'role': 'Technician', 'name': 'Tech Lisa Brown', 'nfc': 'NFC004' },
        { 'staffId': 'DOC002', 'role': 'Doctor', 'name': 'Dr. Michael Brown', 'nfc': 'NFC005' },
        { 'staffId': 'DOC003', 'role': 'Doctor', 'name': 'Dr. Emily Davis', 'nfc': 'NFC006' },
        { 'staffId': 'DOC004', 'role': 'Doctor', 'name': 'Dr. Lisa Park', 'nfc': 'NFC007' },
        { 'staffId': 'DOC005', 'role': 'Doctor', 'name': 'Dr. James Wilson', 'nfc': 'NFC008' },
        { 'staffId': 'DOC006', 'role': 'Doctor', 'name': 'Dr. Amanda Foster', 'nfc': 'NFC009' },
        { 'staffId': 'DOC007', 'role': 'Doctor', 'name': 'Dr. Kevin Zhang', 'nfc': 'NFC010' },
        { 'staffId': 'DOC008', 'role': 'Doctor', 'name': 'Dr. Rachel Green', 'nfc': 'NFC011' },
        { 'staffId': 'NUR002', 'role': 'Nurse', 'name': 'Nurse John Miller', 'nfc': 'NFC012' }
    ]
    
    return {"credentials": demo_creds, "universalPassword": "hospital123"}