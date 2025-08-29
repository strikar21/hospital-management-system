from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class StaffCreate(BaseModel):
    """Schema for creating new staff - staff_id is optional and auto-generated if not provided"""
    staff_id: Optional[str] = Field(None, description="Auto-generated if not provided")
    name: str = Field(..., min_length=2, description="Staff member's full name")
    role: str = Field(..., description="Staff member's role/position")
    department: str = Field(..., description="Department the staff member belongs to")
    nfc_id: Optional[str] = Field(None, description="NFC card ID")
    phone: Optional[str] = Field(None, description="Contact phone number")
    email: Optional[str] = Field(None, description="Contact email address")
    password: Optional[str] = Field(None, description="Login password")
    
    @validator('staff_id', pre=True, always=True)
    def validate_staff_id(cls, v):
        """Allow None/empty for auto-generation, validate non-empty values"""
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if len(v) == 0:
                return None
            if len(v) < 3:
                raise ValueError('Staff ID must be at least 3 characters long')
            return v.upper()
        return None
    
    @validator('name', pre=True)
    def validate_name(cls, v):
        if not v or len(str(v).strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return str(v).strip()
    
    @validator('role', pre=True)
    def validate_role(cls, v):
        if not v or len(str(v).strip()) < 2:
            raise ValueError('Role must be specified')
        return str(v).strip()
    
    @validator('department', pre=True)
    def validate_department(cls, v):
        if not v or len(str(v).strip()) < 2:
            raise ValueError('Department must be specified')
        return str(v).strip()

class StaffBase(BaseModel):
    """Base schema for staff data"""
    name: str
    role: str
    department: str
    nfc_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class StaffUpdate(BaseModel):
    """Schema for updating staff information"""
    name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    nfc_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None

class StaffResponse(BaseModel):
    """Schema for staff responses - using camelCase to match database and frontend"""
    id: str
    staffId: str
    name: str
    role: str
    department: str
    nfcId: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    isActive: bool
    createdAt: datetime
    updatedAt: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class StaffCreationResponse(StaffResponse):
    """Schema for staff creation responses - includes temporary auth credentials"""
    temp_pin: Optional[str] = Field(default=None, description="Temporary PIN for first login (PIN roles only)")
    temp_password: Optional[str] = Field(default=None, description="Temporary password for first login (password roles only)")
    
    class Config:
        from_attributes = True
        extra = "allow"

class StaffLogin(BaseModel):
    """Schema for staff login"""
    staff_id: str
    password: Optional[str] = None
    pin: Optional[str] = None
    nfc_id: Optional[str] = None

class StaffListResponse(BaseModel):
    """Schema for staff list responses"""
    staff: list[StaffResponse]
    total: int
    page: int
    size: int
    
    class Config:
        from_attributes = True

class PasswordChange(BaseModel):
    """Schema for password change requests"""
    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=6, description="New password (minimum 6 characters)")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 6:
            raise ValueError('New password must be at least 6 characters long')
        return v