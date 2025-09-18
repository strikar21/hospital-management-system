"""
Staff data models
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class StaffBase(BaseModel):
    """Base staff model"""
    name: str
    role: str
    email: Optional[str] = None
    phoneNumber: Optional[str] = None
    department: Optional[str] = None

class StaffCreate(StaffBase):
    """Staff creation model"""
    pin: Optional[str] = None
    password: Optional[str] = None
    nfcCardId: Optional[str] = None

class StaffUpdate(BaseModel):
    """Staff update model"""
    name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phoneNumber: Optional[str] = None
    department: Optional[str] = None
    pin: Optional[str] = None
    password: Optional[str] = None
    isActive: Optional[bool] = None
    nfcCardId: Optional[str] = None

class StaffDB(StaffBase):
    """Complete staff model for database operations (includes sensitive fields)"""
    id: str
    isActive: bool = True
    lastSeen: Optional[datetime] = None
    nfcCardId: Optional[str] = None
    pin: Optional[str] = None
    password: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    
    class Config:
        from_attributes = True

class Staff(StaffBase):
    """Staff model for API responses (excludes sensitive fields)"""
    id: str
    isActive: bool = True
    lastSeen: Optional[datetime] = None
    nfcCardId: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class StaffLogin(BaseModel):
    """Staff login model"""
    staffId: str
    pin: Optional[str] = None
    password: Optional[str] = None
    nfcCardId: Optional[str] = None

class StaffLoginResponse(BaseModel):
    """Staff login response model"""
    id: str
    name: str
    role: str
    department: Optional[str] = None
    lastSeen: Optional[datetime] = None
    accessToken: Optional[str] = None