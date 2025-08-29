from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum

Base = declarative_base()

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

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    deviceId = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    deviceType = Column(String, nullable=False)  # DeviceType enum
    status = Column(String, default=DeviceStatus.OFFLINE)
    location = Column(String)  # Room, ward, etc.
    macAddress = Column(String, unique=True)
    ipAddress = Column(String)
    
    # Configuration and capabilities
    capabilities = Column(JSON)  # What data this device can provide
    configuration = Column(JSON)  # Device-specific settings
    firmwareVersion = Column(String)
    
    # Authentication
    deviceToken = Column(String, unique=True)  # For device authentication
    apiKey = Column(String, unique=True)
    
    # Status tracking
    lastSeen = Column(DateTime(timezone=True), server_default=func.now())
    lastHeartbeat = Column(DateTime(timezone=True))
    batteryLevel = Column(Float)  # For battery-powered devices
    signalStrength = Column(Integer)  # WiFi/cellular signal
    
    # Assignment status
    assignmentStatus = Column(String, default="free")  # "free", "assigned", "maintenance", "retired"
    assignedTo = Column(String)  # Patient ID or staff ID
    assignedAt = Column(DateTime(timezone=True))
    
    # Metadata
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
    isActive = Column(Boolean, default=True)
    
    # Relationships
    vitals_data = relationship("VitalReading", back_populates="device")
    alerts = relationship("DeviceAlert", back_populates="device")

class VitalReading(Base):
    __tablename__ = "vital_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    deviceId = Column(String, ForeignKey("devices.deviceId"), nullable=False)
    patientId = Column(String, index=True)  # Optional, some devices may not be patient-specific
    
    # Vital signs data
    heartRate = Column(Integer)
    bloodPressureSystolic = Column(Integer)
    bloodPressureDiastolic = Column(Integer)
    temperature = Column(Float)
    oxygenSaturation = Column(Float)
    respiratoryRate = Column(Integer)
    
    # Extended vitals
    ecgData = Column(JSON)  # ECG waveform data
    eegData = Column(JSON)  # EEG data if applicable
    movementData = Column(JSON)  # Accelerometer data from watches
    locationData = Column(JSON)  # GPS/indoor positioning
    
    # Raw sensor data
    rawData = Column(JSON)  # Original data from device
    processedData = Column(JSON)  # Processed/filtered data
    
    # Quality indicators
    signalQuality = Column(Float)  # 0-100 quality score
    isValid = Column(Boolean, default=True)
    
    # Timestamps
    readingTimestamp = Column(DateTime(timezone=True), nullable=False)
    receivedTimestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    device = relationship("Device", back_populates="vitals_data")

class DoorScanEvent(Base):
    __tablename__ = "door_scan_events"
    
    id = Column(Integer, primary_key=True, index=True)
    deviceId = Column(String, ForeignKey("devices.deviceId"), nullable=False)
    
    # Scan data
    cardId = Column(String)  # RFID/NFC card ID
    userId = Column(String)  # Staff member ID if known
    accessGranted = Column(Boolean)
    doorLocation = Column(String)  # Which door/room
    
    # Event details
    scanTimestamp = Column(DateTime(timezone=True), nullable=False)
    receivedTimestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional data
    eventData = Column(JSON)  # Any additional scan data

class DeviceAlert(Base):
    __tablename__ = "device_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    deviceId = Column(String, ForeignKey("devices.deviceId"), nullable=False)
    
    # Alert details
    alertType = Column(String, nullable=False)  # "battery_low", "offline", "error", etc.
    severity = Column(String, nullable=False)    # "low", "medium", "high", "critical"
    message = Column(String, nullable=False)
    
    # Status
    isActive = Column(Boolean, default=True)
    isAcknowledged = Column(Boolean, default=False)
    acknowledgedBy = Column(String)
    acknowledgedAt = Column(DateTime(timezone=True))
    
    # Timestamps
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    resolvedAt = Column(DateTime(timezone=True))
    
    # Additional data
    alertData = Column(JSON)  # Context-specific alert information
    
    # Relationships
    device = relationship("Device", back_populates="alerts")