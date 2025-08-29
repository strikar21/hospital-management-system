"""
Door Scanner API - Handles door scanner events and audit logging
Receives movement detection, health checks, and offline events from door scanners
"""
from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import time

from app.services.audit_service import AuditService

router = APIRouter(prefix="/door-scanner")

class MovementDetectionRequest(BaseModel):
    """Pydantic model for door scanner movement detection events"""
    device_id: str = Field(..., description="Door scanner device ID")
    location: str = Field(..., description="Door location/room identifier")
    movement_type: str = Field(..., description="Movement direction (entry/exit)")
    person_detected: bool = Field(..., description="Whether person was detected")
    confidence_score: Optional[float] = Field(None, description="Detection confidence (0-1)")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")
    sensor_data: Optional[Dict[str, Any]] = Field(None, description="Raw sensor data")

class HealthCheckRequest(BaseModel):
    """Pydantic model for door scanner health check events"""
    device_id: str = Field(..., description="Door scanner device ID")
    location: str = Field(..., description="Door location/room identifier")
    status: str = Field(..., description="Device status (online/offline/error)")
    battery_level: Optional[int] = Field(None, description="Battery level percentage")
    signal_strength: Optional[int] = Field(None, description="WiFi/network signal strength")
    last_movement_detection: Optional[datetime] = Field(None, description="Last movement detection time")
    uptime_seconds: Optional[int] = Field(None, description="Device uptime in seconds")
    error_message: Optional[str] = Field(None, description="Error details if status is error")

class DoorScannerOfflineRequest(BaseModel):
    """Pydantic model for door scanner offline events"""
    device_id: str = Field(..., description="Door scanner device ID")
    location: str = Field(..., description="Door location/room identifier")
    offline_duration_seconds: int = Field(..., description="Duration offline in seconds")
    last_seen: datetime = Field(..., description="Last communication timestamp")
    reason: Optional[str] = Field(None, description="Reason for going offline")

@router.post("/movement", status_code=201)
async def log_movement_detection(movement: MovementDetectionRequest, request: Request):
    """Log door scanner movement detection event"""
    
    try:
        severity = "info" if movement.person_detected else "warning"
        description = f"Door scanner at {movement.location} detected {movement.movement_type}"
        if movement.person_detected:
            description += f" with confidence {movement.confidence_score:.2f}" if movement.confidence_score else ""
        else:
            description += " but no person was detected"
        
        device_metadata = {
            "location": movement.location,
            "movement_type": movement.movement_type,
            "person_detected": movement.person_detected,
            "confidence_score": movement.confidence_score,
            "detection_timestamp": movement.timestamp.isoformat() if movement.timestamp else None,
            "source_ip": request.client.host if request.client else None,
            "sensor_data": movement.sensor_data
        }
        
        success = await AuditService.log_door_scanner_event(
            device_id=movement.device_id,
            action="movement_detected",
            description=description,
            severity=severity,
            device_metadata=device_metadata,
            success=True
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to log movement detection event")
        
        return {
            "status": "movement_logged",
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": movement.device_id,
            "location": movement.location,
            "movement_type": movement.movement_type,
            "person_detected": movement.person_detected
        }
        
    except Exception as e:
        await AuditService.log_door_scanner_event(
            device_id=movement.device_id,
            action="movement_detection_error",
            description=f"Failed to process movement detection from {movement.location}: {str(e)}",
            severity="error",
            device_metadata={"location": movement.location, "error": str(e)},
            success=False,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to process movement detection: {str(e)}")

@router.post("/health-check", status_code=201)
async def log_health_check(health: HealthCheckRequest, request: Request):
    """Log door scanner health check event"""
    
    try:
        severity_map = {
            "online": "info",
            "offline": "critical",
            "error": "error",
            "warning": "warning"
        }
        severity = severity_map.get(health.status.lower(), "info")
        
        description = f"Door scanner at {health.location} reported status: {health.status}"
        if health.battery_level is not None:
            description += f", battery: {health.battery_level}%"
        if health.uptime_seconds is not None:
            uptime_hours = health.uptime_seconds / 3600
            description += f", uptime: {uptime_hours:.1f}h"
        
        device_metadata = {
            "location": health.location,
            "device_status": health.status,
            "battery_level": health.battery_level,
            "signal_strength": health.signal_strength,
            "last_movement_detection": health.last_movement_detection.isoformat() if health.last_movement_detection else None,
            "uptime_seconds": health.uptime_seconds,
            "source_ip": request.client.host if request.client else None,
            "error_details": health.error_message
        }
        
        success = await AuditService.log_door_scanner_event(
            device_id=health.device_id,
            action="health_check",
            description=description,
            severity=severity,
            device_metadata=device_metadata,
            success=True,
            error_message=health.error_message
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to log health check event")
        
        return {
            "status": "health_check_logged",
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": health.device_id,
            "location": health.location,
            "device_status": health.status,
            "severity": severity
        }
        
    except Exception as e:
        await AuditService.log_door_scanner_event(
            device_id=health.device_id,
            action="health_check_error",
            description=f"Failed to process health check from {health.location}: {str(e)}",
            severity="error",
            device_metadata={"location": health.location, "error": str(e)},
            success=False,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to process health check: {str(e)}")

@router.post("/offline", status_code=201)
async def log_offline_event(offline: DoorScannerOfflineRequest, request: Request):
    """Log door scanner offline event"""
    
    try:
        offline_hours = offline.offline_duration_seconds / 3600
        description = f"Door scanner at {offline.location} went offline for {offline_hours:.1f} hours"
        if offline.reason:
            description += f" (Reason: {offline.reason})"
        
        # Determine severity based on offline duration
        if offline.offline_duration_seconds > 3600:  # > 1 hour
            severity = "critical"
        elif offline.offline_duration_seconds > 900:  # > 15 minutes
            severity = "error"
        elif offline.offline_duration_seconds > 300:  # > 5 minutes
            severity = "warning"
        else:
            severity = "info"
        
        device_metadata = {
            "location": offline.location,
            "offline_duration_seconds": offline.offline_duration_seconds,
            "offline_duration_hours": offline_hours,
            "last_seen": offline.last_seen.isoformat(),
            "offline_reason": offline.reason,
            "source_ip": request.client.host if request.client else None
        }
        
        success = await AuditService.log_door_scanner_event(
            device_id=offline.device_id,
            action="device_offline",
            description=description,
            severity=severity,
            device_metadata=device_metadata,
            success=True
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to log offline event")
        
        return {
            "status": "offline_event_logged",
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": offline.device_id,
            "location": offline.location,
            "offline_duration_hours": offline_hours,
            "severity": severity
        }
        
    except Exception as e:
        await AuditService.log_door_scanner_event(
            device_id=offline.device_id,
            action="offline_event_error",
            description=f"Failed to process offline event from {offline.location}: {str(e)}",
            severity="error",
            device_metadata={"location": offline.location, "error": str(e)},
            success=False,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to process offline event: {str(e)}")

@router.get("/status")
async def get_door_scanner_status():
    """Get status of all door scanner devices"""
    
    try:
        # Get recent audit logs for door scanners to determine current status
        recent_logs = await AuditService.get_audit_logs(
            event_category="door_scanner",
            hours_back=24,
            limit=1000
        )
        
        # Group by device_id and get latest status for each
        device_status = {}
        for log in recent_logs:
            device_id = log.get("device_id")
            if device_id:
                if device_id not in device_status or log["timestamp"] > device_status[device_id]["last_seen"]:
                    device_metadata = log.get("device_metadata", {}) if isinstance(log.get("device_metadata"), dict) else {}
                    device_status[device_id] = {
                        "device_id": device_id,
                        "location": device_metadata.get("location", "Unknown"),
                        "last_action": log.get("action"),
                        "last_seen": log["timestamp"],
                        "status": device_metadata.get("device_status", "unknown"),
                        "battery_level": device_metadata.get("battery_level"),
                        "signal_strength": device_metadata.get("signal_strength"),
                        "severity": log.get("severity", "info")
                    }
        
        return {
            "door_scanners": list(device_status.values()),
            "total_devices": len(device_status),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get door scanner status: {str(e)}")

@router.get("/events")
async def get_door_scanner_events(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    location: Optional[str] = Query(None, description="Filter by location"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    hours_back: int = Query(24, description="Hours of history to retrieve"),
    limit: int = Query(100, description="Maximum records to return")
):
    """Get door scanner events history"""
    
    try:
        logs = await AuditService.get_audit_logs(
            event_category="door_scanner",
            device_id=device_id,
            hours_back=hours_back,
            limit=limit
        )
        
        # Filter by location and action if specified
        filtered_logs = []
        for log in logs:
            device_metadata = log.get("device_metadata", {}) if isinstance(log.get("device_metadata"), dict) else {}
            
            # Apply location filter
            if location and device_metadata.get("location") != location:
                continue
            
            # Apply action filter
            if action and log.get("action") != action:
                continue
            
            # Add location to main log data for easier access
            log["location"] = device_metadata.get("location", "Unknown")
            filtered_logs.append(log)
        
        return {
            "events": filtered_logs,
            "total_count": len(filtered_logs),
            "filters_applied": {
                "device_id": device_id,
                "location": location,
                "action": action,
                "hours_back": hours_back,
                "limit": limit
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get door scanner events: {str(e)}")