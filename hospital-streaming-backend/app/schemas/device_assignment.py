from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DeviceAssignmentCreate(BaseModel):
    deviceId: str = Field(..., description="Device ID to assign")
    patientId: str = Field(..., description="Patient ID to assign device to")
    assignedBy: str = Field(..., description="Staff ID who is making the assignment")
    assignmentReason: str = Field(default="patient_admission", description="Reason for assignment")

class DeviceAssignmentUpdate(BaseModel):
    unassignedBy: str = Field(..., description="Staff ID who is unassigning the device")
    unassignmentReason: str = Field(default="patient_discharge", description="Reason for unassignment")
    newDeviceId: Optional[str] = Field(None, description="New device ID if reassigning")

class DeviceReassignmentCreate(BaseModel):
    oldDeviceId: str = Field(..., description="Current device ID to replace")
    newDeviceId: str = Field(..., description="New device ID to assign")
    reassignedBy: str = Field(..., description="Staff ID performing reassignment")
    reassignmentReason: str = Field(default="device_malfunction", description="Reason for reassignment")

class DeviceAssignmentResponse(BaseModel):
    id: int
    deviceId: str
    patientId: str
    assignedBy: str
    assignmentReason: str
    assignedAt: datetime
    unassignedAt: Optional[datetime] = None
    unassignedBy: Optional[str] = None
    unassignmentReason: Optional[str] = None
    newDeviceId: Optional[str] = None
    status: str
    createdAt: datetime

    class Config:
        from_attributes = True

class FreeDeviceResponse(BaseModel):
    deviceId: str
    name: str
    deviceType: str
    location: str
    status: str
    batteryLevel: Optional[int] = None
    lastHeartbeat: Optional[datetime] = None
    createdAt: datetime

class PatientDeviceResponse(BaseModel):
    deviceId: str
    name: str
    deviceType: str
    status: str
    batteryLevel: Optional[int] = None
    assignedAt: datetime
    assignedBy: str
    assignmentReason: str

class AssignmentHistoryResponse(BaseModel):
    id: int
    deviceId: str
    patientId: str
    assignedBy: str
    assignmentReason: str
    assignedAt: datetime
    unassignedAt: Optional[datetime] = None
    unassignedBy: Optional[str] = None
    unassignmentReason: Optional[str] = None
    newDeviceId: Optional[str] = None
    status: str
    deviceName: str
    deviceType: str

class DevicePoolStatusResponse(BaseModel):
    byType: dict
    summary: dict