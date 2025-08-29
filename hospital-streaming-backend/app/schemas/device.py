from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class DeviceType(str, Enum):
    WATCH = "watch"
    DOOR_SCANNER = "door_scanner"
    VITAL_MONITOR = "vital_monitor"
    ECG_MACHINE = "ecg_machine"
    INFUSION_PUMP = "infusion_pump"
    TABLET = "tablet"
    SENSOR = "sensor"

class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"

class AssignmentStatus(str, Enum):
    FREE = "free"
    ASSIGNED = "assigned"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"

# Device Registration and Management
class DeviceCreate(BaseModel):
    deviceId: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Human-readable device name")
    deviceType: DeviceType
    location: Optional[str] = None
    macAddress: Optional[str] = None
    ipAddress: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None
    configuration: Optional[Dict[str, Any]] = None
    firmwareVersion: Optional[str] = None

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    status: Optional[DeviceStatus] = None
    capabilities: Optional[Dict[str, Any]] = None
    configuration: Optional[Dict[str, Any]] = None
    firmwareVersion: Optional[str] = None

class DeviceResponse(BaseModel):
    id: int
    deviceId: str
    name: str
    deviceType: str
    status: str
    location: Optional[str]
    macAddress: Optional[str]
    ipAddress: Optional[str]
    capabilities: Optional[Dict[str, Any]]
    configuration: Optional[Dict[str, Any]]
    firmwareVersion: Optional[str]
    lastSeen: Optional[datetime]
    lastHeartbeat: Optional[datetime]
    batteryLevel: Optional[float]
    signalStrength: Optional[int]
    assignmentStatus: Optional[str] = "free"
    assignedTo: Optional[str]
    assignedAt: Optional[datetime]
    createdAt: datetime
    updatedAt: Optional[datetime]
    isActive: bool

    class Config:
        from_attributes = True

# Vital Signs Data
class VitalReadingCreate(BaseModel):
    deviceId: str
    patientId: Optional[str] = None
    heartRate: Optional[int] = None
    bloodPressureSystolic: Optional[int] = None
    bloodPressureDiastolic: Optional[int] = None
    temperature: Optional[float] = None
    oxygenSaturation: Optional[float] = None
    respiratoryRate: Optional[int] = None
    ecgData: Optional[Dict[str, Any]] = None
    eegData: Optional[Dict[str, Any]] = None
    movementData: Optional[Dict[str, Any]] = None
    locationData: Optional[Dict[str, Any]] = None
    rawData: Optional[Dict[str, Any]] = None
    signalQuality: Optional[float] = None
    readingTimestamp: datetime

class VitalReadingResponse(BaseModel):
    id: int
    deviceId: str
    patientId: Optional[str]
    heartRate: Optional[int]
    bloodPressureSystolic: Optional[int]
    bloodPressureDiastolic: Optional[int]
    temperature: Optional[float]
    oxygenSaturation: Optional[float]
    respiratoryRate: Optional[int]
    ecgData: Optional[Dict[str, Any]]
    eegData: Optional[Dict[str, Any]]
    movementData: Optional[Dict[str, Any]]
    locationData: Optional[Dict[str, Any]]
    signalQuality: Optional[float]
    isValid: bool
    readingTimestamp: datetime
    receivedTimestamp: datetime

    class Config:
        from_attributes = True

# Door Scanner Events
class DoorScanEventCreate(BaseModel):
    deviceId: str
    cardId: Optional[str] = None
    userId: Optional[str] = None
    accessGranted: bool
    doorLocation: str
    scanTimestamp: datetime
    eventData: Optional[Dict[str, Any]] = None

class DoorScanEventResponse(BaseModel):
    id: int
    deviceId: str
    cardId: Optional[str]
    userId: Optional[str]
    accessGranted: bool
    doorLocation: str
    scanTimestamp: datetime
    receivedTimestamp: datetime
    eventData: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True

# Device Alerts
class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class DeviceAlertCreate(BaseModel):
    deviceId: str
    alertType: str
    severity: AlertSeverity
    message: str
    alertData: Optional[Dict[str, Any]] = None

class DeviceAlertResponse(BaseModel):
    id: int
    deviceId: str
    alertType: str
    severity: str
    message: str
    isActive: bool
    isAcknowledged: bool
    acknowledgedBy: Optional[str]
    acknowledgedAt: Optional[datetime]
    createdAt: datetime
    resolvedAt: Optional[datetime]
    alertData: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True

# Device Health and Status
class DeviceHealth(BaseModel):
    deviceId: str
    status: DeviceStatus
    batteryLevel: Optional[float] = None
    signalStrength: Optional[int] = None
    lastHeartbeat: datetime
    systemInfo: Optional[Dict[str, Any]] = None

# Streaming Data Models
class StreamingVitalData(BaseModel):
    deviceId: str
    patientId: Optional[str]
    timestamp: datetime
    vitals: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class StreamingAlertData(BaseModel):
    alertId: int
    deviceId: str
    patientId: Optional[str]
    alertType: str
    severity: str
    message: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

# Batch Data Processing
class VitalsBatch(BaseModel):
    deviceId: str
    readings: List[VitalReadingCreate]

class DeviceListResponse(BaseModel):
    devices: List[DeviceResponse]
    totalCount: int
    page: int
    pageSize: int