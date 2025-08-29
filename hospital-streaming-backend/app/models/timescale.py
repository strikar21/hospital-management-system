from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from app.db.database import TimescaleBase

class VitalReading(TimescaleBase):
    """TimescaleDB model for vital readings (time-series data)"""
    __tablename__ = "vital_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(50), nullable=False, index=True)
    patient_id = Column(String(50), nullable=False, index=True)
    vital_type = Column(String(50), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(20))
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    quality_indicator = Column(String(20))
    device_metadata = Column("metadata", JSON)

class DeviceAlertTS(TimescaleBase):
    """TimescaleDB model for device alerts (time-series data)"""
    __tablename__ = "device_alerts_ts"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(50), nullable=False, index=True)
    patient_id = Column(String(50))
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, index=True)
    message = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True))
    acknowledged = Column(Boolean, default=False)
    device_metadata = Column("metadata", JSON)

class DeviceStatusLog(TimescaleBase):
    """TimescaleDB model for device status logs (time-series data)"""
    __tablename__ = "device_status_log"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    battery_level = Column(Integer)
    signal_strength = Column(Integer)
    device_metadata = Column("metadata", JSON)

class AuditLog(TimescaleBase):
    """TimescaleDB model for comprehensive audit logging (time-series data)"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Event Classification
    event_type = Column(String(50), nullable=False, index=True)  # user_action, device_event, system_event, api_request
    event_category = Column(String(50), nullable=False, index=True)  # esp32_watch, door_scanner, frontend, backend, database
    action = Column(String(100), nullable=False, index=True)  # login, vitals_transmission, movement_detected, patient_viewed
    severity = Column(String(20), nullable=False, index=True)  # info, warning, error, critical
    
    # Entity Information
    user_id = Column(String(50), index=True)  # Staff member performing action
    patient_id = Column(String(50), index=True)  # Patient affected (if applicable)
    device_id = Column(String(50), index=True)  # Device involved (ESP32/door scanner)
    session_id = Column(String(100), index=True)  # Session/connection identifier
    
    # Event Details
    description = Column(Text, nullable=False)  # Human-readable event description
    source_ip = Column(String(45))  # IPv4/IPv6 address
    user_agent = Column(String(500))  # Browser/device user agent
    endpoint = Column(String(200))  # API endpoint called
    http_method = Column(String(10))  # GET, POST, PUT, DELETE
    http_status = Column(Integer)  # HTTP response status code
    
    # Data and Context
    request_data = Column(JSON)  # Request payload (sanitized)
    response_data = Column(JSON)  # Response data (sanitized)
    device_metadata = Column(JSON)  # Device-specific information
    additional_context = Column(JSON)  # Additional contextual data
    
    # Performance and Monitoring
    execution_time_ms = Column(Integer)  # Operation execution time
    success = Column(Boolean, nullable=False, default=True)  # Operation success status
    error_message = Column(Text)  # Error details if failed
    
    # Compliance and Security
    data_classification = Column(String(20))  # public, internal, confidential, restricted
    retention_policy = Column(String(50))  # Retention period identifier
    hipaa_relevant = Column(Boolean, default=False)  # HIPAA compliance flag