from fastapi import APIRouter, HTTPException, Depends, Query, Request
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import logging
import time

from app.db.database import database
from app.services.audit_service import AuditService
# Create simple auth dependency for audit endpoints
async def verify_staff_access(staff_id: str = Query(..., description="Staff ID performing the action")):
    """Simple staff access verification for audit endpoints"""
    return {"id": staff_id, "role": "admin"}  # Simplified for audit logging

router = APIRouter(prefix="/audit")
logger = logging.getLogger(__name__)

class AuditLogRequest(BaseModel):
    """Pydantic model for audit log requests"""
    event_type: str = Field(..., description="Type of event (user_action, device_event, system_event, api_request)")
    event_category: str = Field(..., description="Category (esp32_watch, door_scanner, frontend, backend, database)")
    action: str = Field(..., description="Specific action performed")
    description: str = Field(..., description="Human-readable description")
    severity: str = Field(default="info", description="Event severity (info, warning, error, critical)")
    user_id: Optional[str] = Field(None, description="Staff member ID")
    patient_id: Optional[str] = Field(None, description="Patient ID if relevant")
    device_id: Optional[str] = Field(None, description="Device ID if relevant")
    session_id: Optional[str] = Field(None, description="Session identifier")
    source_ip: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    endpoint: Optional[str] = Field(None, description="API endpoint")
    http_method: Optional[str] = Field(None, description="HTTP method")
    http_status: Optional[int] = Field(None, description="HTTP status code")
    request_data: Optional[Dict[str, Any]] = Field(None, description="Request payload")
    response_data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    device_metadata: Optional[Dict[str, Any]] = Field(None, description="Device metadata")
    additional_context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    success: bool = Field(default=True, description="Operation success status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    hipaa_relevant: bool = Field(default=False, description="HIPAA relevance flag")

class ESP32AuditRequest(BaseModel):
    """Pydantic model for ESP32 watch audit events"""
    device_id: str = Field(..., description="ESP32 device ID")
    action: str = Field(..., description="Action performed")
    description: str = Field(..., description="Event description")
    patient_id: Optional[str] = Field(None, description="Patient ID")
    severity: str = Field(default="info", description="Event severity")
    battery_level: Optional[int] = Field(None, description="Battery level percentage")
    signal_strength: Optional[int] = Field(None, description="WiFi signal strength")
    vital_type: Optional[str] = Field(None, description="Type of vital sign")
    vital_value: Optional[float] = Field(None, description="Vital sign value")
    success: bool = Field(default=True, description="Operation success")
    error_message: Optional[str] = Field(None, description="Error details")

class DoorScannerAuditRequest(BaseModel):
    """Pydantic model for door scanner audit events"""
    device_id: str = Field(..., description="Door scanner device ID")
    action: str = Field(..., description="Action performed")
    description: str = Field(..., description="Event description")
    severity: str = Field(default="info", description="Event severity")
    location: Optional[str] = Field(None, description="Door location")
    movement_type: Optional[str] = Field(None, description="Movement direction (in/out)")
    person_detected: Optional[bool] = Field(None, description="Person detected flag")
    success: bool = Field(default=True, description="Operation success")
    error_message: Optional[str] = Field(None, description="Error details")

@router.post("/log", status_code=201)
async def log_audit_entry(
    audit_request: AuditLogRequest,
    request: Request,
    staff_id: str = Query("system", description="Staff ID performing the action")
):
    """Log a comprehensive audit entry to TimescaleDB"""
    
    start_time = time.time()
    
    try:
        # Extract request metadata
        source_ip = audit_request.source_ip or request.client.host
        user_agent = audit_request.user_agent or request.headers.get("user-agent")
        
        success = await AuditService.log_event(
            event_type=audit_request.event_type,
            event_category=audit_request.event_category,
            action=audit_request.action,
            description=audit_request.description,
            severity=audit_request.severity,
            user_id=audit_request.user_id or staff_id,
            patient_id=audit_request.patient_id,
            device_id=audit_request.device_id,
            session_id=audit_request.session_id,
            source_ip=source_ip,
            user_agent=user_agent,
            endpoint=audit_request.endpoint,
            http_method=audit_request.http_method,
            http_status=audit_request.http_status,
            request_data=audit_request.request_data,
            response_data=audit_request.response_data,
            device_metadata=audit_request.device_metadata,
            additional_context=audit_request.additional_context,
            execution_time_ms=audit_request.execution_time_ms,
            success=audit_request.success,
            error_message=audit_request.error_message,
            hipaa_relevant=audit_request.hipaa_relevant
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to log audit entry")
        
        return {
            "status": "audit_logged",
            "timestamp": datetime.utcnow().isoformat(),
            "execution_time_ms": execution_time
        }
        
    except Exception as e:
        logger.error(f"Failed to log audit entry: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Audit logging failed: {str(e)}")

@router.post("/esp32/log", status_code=201)
async def log_esp32_event(audit_request: ESP32AuditRequest):
    """Log ESP32 watch specific audit events"""
    
    try:
        device_metadata = {
            "battery_level": audit_request.battery_level,
            "signal_strength": audit_request.signal_strength,
            "vital_type": audit_request.vital_type,
            "vital_value": audit_request.vital_value
        }
        
        success = await AuditService.log_esp32_event(
            device_id=audit_request.device_id,
            action=audit_request.action,
            description=audit_request.description,
            patient_id=audit_request.patient_id,
            severity=audit_request.severity,
            device_metadata=device_metadata,
            success=audit_request.success,
            error_message=audit_request.error_message
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to log ESP32 audit event")
        
        return {
            "status": "esp32_audit_logged",
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": audit_request.device_id
        }
        
    except Exception as e:
        logger.error(f"Failed to log ESP32 audit event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ESP32 audit logging failed: {str(e)}")

@router.post("/door-scanner/log", status_code=201)
async def log_door_scanner_event(audit_request: DoorScannerAuditRequest):
    """Log door scanner specific audit events"""
    
    try:
        device_metadata = {
            "location": audit_request.location,
            "movement_type": audit_request.movement_type,
            "person_detected": audit_request.person_detected
        }
        
        success = await AuditService.log_door_scanner_event(
            device_id=audit_request.device_id,
            action=audit_request.action,
            description=audit_request.description,
            severity=audit_request.severity,
            device_metadata=device_metadata,
            success=audit_request.success,
            error_message=audit_request.error_message
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to log door scanner audit event")
        
        return {
            "status": "door_scanner_audit_logged",
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": audit_request.device_id
        }
        
    except Exception as e:
        logger.error(f"Failed to log door scanner audit event: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Door scanner audit logging failed: {str(e)}")

@router.get("/logs")
async def get_audit_logs(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    event_category: Optional[str] = Query(None, description="Filter by event category"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    hours_back: int = Query(24, description="Hours of history to retrieve"),
    limit: int = Query(1000, description="Maximum records to return"),
    staff_id: str = Query("admin", description="Staff ID performing the action")
):
    """Retrieve audit logs with optional filters"""
    
    try:
        # Simplified access control for audit logs
        if not user_id and staff_id != "admin":
            user_id = staff_id
        
        logs = await AuditService.get_audit_logs(
            event_type=event_type,
            event_category=event_category,
            user_id=user_id,
            patient_id=patient_id,
            device_id=device_id,
            severity=severity,
            hours_back=hours_back,
            limit=limit
        )
        
        return {
            "audit_logs": logs,
            "total_count": len(logs),
            "filters_applied": {
                "event_type": event_type,
                "event_category": event_category,
                "user_id": user_id,
                "patient_id": patient_id,
                "device_id": device_id,
                "severity": severity,
                "hours_back": hours_back,
                "limit": limit
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit logs: {str(e)}")

@router.get("/summary")
async def get_audit_summary(
    hours_back: int = Query(24, description="Hours of history to analyze"),
    staff_id: str = Query("admin", description="Staff ID performing the action")
):
    """Get audit summary statistics"""
    
    try:
        logs = await AuditService.get_audit_logs(hours_back=hours_back, limit=10000)
        
        # Calculate summary statistics
        total_events = len(logs)
        error_events = sum(1 for log in logs if not log.get("success", True))
        critical_events = sum(1 for log in logs if log.get("severity") == "critical")
        
        # Group by event category
        category_counts = {}
        severity_counts = {}
        user_activity = {}
        
        for log in logs:
            category = log.get("event_category", "unknown")
            severity = log.get("severity", "info")
            user = log.get("user_id", "system")
            
            category_counts[category] = category_counts.get(category, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            user_activity[user] = user_activity.get(user, 0) + 1
        
        return {
            "summary": {
                "total_events": total_events,
                "error_events": error_events,
                "critical_events": critical_events,
                "success_rate": round((total_events - error_events) / max(total_events, 1) * 100, 2)
            },
            "breakdown": {
                "by_category": category_counts,
                "by_severity": severity_counts,
                "by_user": dict(sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10])
            },
            "time_range": {
                "hours_back": hours_back,
                "analyzed_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to generate audit summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate audit summary: {str(e)}")