from pydantic import BaseModel, validator
from typing import Optional, Dict, Any, List
from datetime import datetime

class DeviceBase(BaseModel):
    deviceId: str
    name: str
    deviceType: str
    location: str
    macAddress: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None
    configuration: Optional[Dict[str, Any]] = None
    
    @validator('deviceId')
    def validate_device_id(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Device ID must be at least 3 characters long')
        return v.strip().upper()
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Device name must be at least 2 characters long')
        return v.strip()
    
    @validator('deviceType')
    def validate_device_type(cls, v):
        allowed_types = [
            'watch', 'vital_monitor', 'door_scanner', 'bed_sensor',
            'iv_pump', 'ventilator', 'ecg_monitor', 'pulse_oximeter',
            'blood_pressure_monitor', 'temperature_sensor', 'camera',
            'access_control', 'emergency_button', 'tablet', 'smartphone'
        ]
        if v not in allowed_types:
            raise ValueError(f'Device type must be one of: {", ".join(allowed_types)}')
        return v
    
    @validator('location')
    def validate_location(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Location must be specified')
        return v.strip()

class DeviceCreate(DeviceBase):
    firmwareVersion: Optional[str] = None
    provisionedBy: str
    
    @validator('provisionedBy')
    def validate_provisioned_by(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Provisioned by staff ID must be specified')
        return v.strip()

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None
    configuration: Optional[Dict[str, Any]] = None
    firmwareVersion: Optional[str] = None
    isActive: Optional[bool] = None
    status: Optional[str] = None

class DeviceResponse(DeviceBase):
    id: int
    status: str
    ipAddress: Optional[str] = None
    firmwareVersion: Optional[str] = None
    deviceToken: Optional[str] = None
    apiKey: Optional[str] = None
    lastSeen: Optional[datetime] = None
    lastHeartbeat: Optional[datetime] = None
    batteryLevel: Optional[float] = None
    signalStrength: Optional[int] = None
    isActive: bool
    createdAt: datetime
    updatedAt: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class DeviceListResponse(BaseModel):
    devices: List[DeviceResponse]
    totalCount: int
    page: int
    pageSize: int

class DeviceProvisionRequest(BaseModel):
    deviceId: str
    name: str
    deviceType: str
    location: str
    macAddress: Optional[str] = None
    firmwareVersion: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None
    initialConfig: Optional[Dict[str, Any]] = None
    
    @validator('deviceType')
    def validate_device_type(cls, v):
        allowed_types = [
            'watch', 'vital_monitor', 'door_scanner', 'bed_sensor',
            'iv_pump', 'ventilator', 'ecg_monitor', 'pulse_oximeter',
            'blood_pressure_monitor', 'temperature_sensor', 'camera',
            'access_control', 'emergency_button', 'tablet', 'smartphone'
        ]
        if v not in allowed_types:
            raise ValueError(f'Device type must be one of: {", ".join(allowed_types)}')
        return v

class DeviceStatusUpdate(BaseModel):
    status: str
    batteryLevel: Optional[float] = None
    signalStrength: Optional[int] = None
    location: Optional[str] = None
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['online', 'offline', 'maintenance', 'error', 'provisioning']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v
    
    @validator('batteryLevel')
    def validate_battery_level(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Battery level must be between 0 and 100')
        return v
    
    @validator('signalStrength')
    def validate_signal_strength(cls, v):
        if v is not None and (v < -100 or v > 0):
            raise ValueError('Signal strength must be between -100 and 0 dBm')
        return v