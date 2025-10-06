"""
Staff data models
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated
from typing import Optional
from datetime import datetime

class StaffBase(BaseModel):
    """Base staff model"""
    firstName: str
    lastName: str
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
    firstName: Optional[str] = None
    lastName: Optional[str] = None
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

    @property
    def name(self) -> str:
        """Computed property for frontend compatibility - combines firstName and lastName"""
        return f"{self.firstName} {self.lastName}".strip()

    @property
    def staffId(self) -> str:
        """Return staff ID for frontend compatibility"""
        return self.id

class StaffLogin(BaseModel):
    """Staff login model - matches Pydantic v2.5.0 camelCase expectations"""
    staffId: str
    pin: Optional[str] = None
    password: Optional[str] = None
    nfcCardId: Optional[str] = None

    model_config = ConfigDict(extra='ignore')

    # Property methods to maintain lowercase access in backend code
    @property
    def staffid(self) -> str:
        return self.staffId

    @property
    def nfccardid(self) -> Optional[str]:
        return self.nfcCardId

class StaffLoginResponse(BaseModel):
    """Staff login response model"""
    id: str
    firstName: str
    lastName: str
    role: str
    department: Optional[str] = None
    lastSeen: Optional[datetime] = None
    accessToken: Optional[str] = None
    refreshToken: Optional[str] = None
    tokenType: str = "bearer"

    @property
    def name(self) -> str:
        """Computed property for frontend compatibility"""
        return f"{self.firstName} {self.lastName}".strip()

    @property
    def staffId(self) -> str:
        """Return staff ID for frontend compatibility"""
        return self.id