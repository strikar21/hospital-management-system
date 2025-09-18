"""
Device data models
"""

from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, Dict, Any
from datetime import datetime

class DeviceBase(BaseModel):
    """Base device model"""
    deviceType: str
    serialNumber: str
    macAddress: Optional[str] = None
    firmwareVersion: Optional[str] = None
    location: Optional[str] = None

class DeviceCreate(BaseModel):
    """Device creation model"""
    deviceType: str
    serialNumber: str
    macAddress: Optional[str] = None
    firmwareVersion: Optional[str] = None
    location: Optional[str] = None

class DeviceUpdate(BaseModel):
    """Device update model"""
    deviceType: Optional[str] = None
    serialNumber: Optional[str] = None
    macAddress: Optional[str] = None
    firmwareVersion: Optional[str] = None
    batteryLevel: Optional[int] = None
    status: Optional[str] = None
    location: Optional[str] = None
    assignedPatientId: Optional[str] = None
    calibrationDate: Optional[datetime] = None
    nextMaintenanceDate: Optional[datetime] = None

class Device(BaseModel):
    """Complete device model"""
    id: str
    deviceType: str
    serialNumber: str
    macAddress: Optional[str] = None
    firmwareVersion: Optional[str] = None
    location: Optional[str] = None
    batteryLevel: Optional[int] = None
    status: str = "available"
    lastSeen: Optional[datetime] = None
    assignedPatientId: Optional[str] = None
    calibrationDate: Optional[datetime] = None
    nextMaintenanceDate: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime
    
    @model_validator(mode='before')
    @classmethod
    def transform_db_fields(cls, data: Any) -> Any:
        print(f"Device model validator called with: {data}")
        if isinstance(data, dict):
            # Map database field names to model field names
            field_mapping = {
                'devicetype': 'deviceType',
                'serialnumber': 'serialNumber',
                'macaddress': 'macAddress',
                'firmwareversion': 'firmwareVersion',
                'batterylevel': 'batteryLevel',
                'lastseen': 'lastSeen',
                'assignedpatientid': 'assignedPatientId',
                'calibrationdate': 'calibrationDate',
                'nextmaintenancedate': 'nextMaintenanceDate',
                'createdat': 'createdAt',
                'updatedat': 'updatedAt'
            }
            
            # Create new dict with transformed keys
            transformed = {}
            for db_key, value in data.items():
                model_key = field_mapping.get(db_key, db_key)
                transformed[model_key] = value
            
            print(f"Device transformed: {transformed}")
            return transformed
        return data
    
    model_config = ConfigDict(
        from_attributes=True
    )

class DeviceAssignmentBase(BaseModel):
    """Base device assignment model"""
    patientId: str
    deviceId: str
    notes: Optional[str] = None

class DeviceAssignmentCreate(BaseModel):
    """Device assignment creation model"""
    patientId: str
    deviceId: str
    assignedBy: str
    notes: Optional[str] = None

class DeviceAssignment(BaseModel):
    """Complete device assignment model"""
    id: int
    patientId: str
    deviceId: str
    assignedBy: str
    assignedAt: datetime
    unassignedAt: Optional[datetime] = None
    status: str = "active"
    notes: Optional[str] = None
    
    @model_validator(mode='before')
    @classmethod
    def transform_db_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Map database field names to model field names
            field_mapping = {
                'patientid': 'patientId',
                'deviceid': 'deviceId',
                'assignedby': 'assignedBy',
                'assignedat': 'assignedAt',
                'unassignedat': 'unassignedAt'
            }
            
            # Create new dict with transformed keys
            transformed = {}
            for db_key, value in data.items():
                model_key = field_mapping.get(db_key, db_key)
                transformed[model_key] = value
            
            return transformed
        return data
    
    model_config = ConfigDict(
        from_attributes=True
    )