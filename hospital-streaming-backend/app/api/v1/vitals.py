from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import time
from app.services.vitals_service import VitalsService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/vitals")

class VitalReadingRequest(BaseModel):
    deviceId: str
    patientId: str
    vitalType: str
    value: float
    unit: Optional[str] = None
    qualityIndicator: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class DeviceAlertRequest(BaseModel):
    deviceId: str
    patientId: str
    alertType: str
    severity: str
    message: str
    metadata: Optional[Dict[str, Any]] = None

@router.post("/readings")
async def store_vital_reading(reading: VitalReadingRequest, request: Request):
    """Store a vital reading in TimescaleDB"""
    start_time = time.time()
    
    success = await VitalsService.store_vital_reading(
        device_id=reading.device_id,
        patient_id=reading.patient_id,
        vital_type=reading.vital_type,
        value=reading.value,
        unit=reading.unit,
        quality_indicator=reading.quality_indicator,
        metadata=reading.metadata
    )
    
    execution_time = int((time.time() - start_time) * 1000)
    
    # Log ESP32 vitals transmission audit event
    await AuditService.log_esp32_event(
        device_id=reading.device_id,
        action="vitals_transmission",
        description=f"ESP32 transmitted {reading.vital_type} reading: {reading.value} {reading.unit or ''}",
        patient_id=reading.patient_id,
        severity="info" if success else "error",
        device_metadata={
            "vital_type": reading.vital_type,
            "vital_value": reading.value,
            "unit": reading.unit,
            "quality_indicator": reading.quality_indicator,
            "transmission_time_ms": execution_time,
            "source_ip": request.client.host if request.client else None,
            **(reading.metadata if reading.metadata else {})
        },
        success=success,
        error_message=None if success else "Failed to store vital reading in database"
    )
    
    if success:
        return {"message": "Vital reading stored successfully", "execution_time_ms": execution_time}
    else:
        raise HTTPException(status_code=500, detail="Failed to store vital reading")

@router.get("/latest/{patient_id}")
async def get_latest_vitals(patient_id: str):
    """Get latest vital readings for a patient"""
    vitals = await VitalsService.get_latest_vitals(patient_id)
    return {"patient_id": patient_id, "vitals": vitals}

@router.get("/history/{patient_id}/{vital_type}")
async def get_vital_history(
    patient_id: str,
    vital_type: str,
    hours: int = Query(default=24, ge=1, le=168)  # 1 hour to 1 week
):
    """Get vital reading history for a patient"""
    history = await VitalsService.get_vital_history(patient_id, vital_type, hours)
    return {
        "patient_id": patient_id,
        "vital_type": vital_type,
        "hours": hours,
        "readings": history
    }

@router.get("/statistics/{patient_id}/{vital_type}")
async def get_vital_statistics(
    patient_id: str,
    vital_type: str,
    hours: int = Query(default=24, ge=1, le=168)
):
    """Get vital statistics (min, max, avg) for a patient"""
    stats = await VitalsService.get_vital_statistics(patient_id, vital_type, hours)
    
    if stats:
        return {
            "patient_id": patient_id,
            "vital_type": vital_type,
            "hours": hours,
            "statistics": stats
        }
    else:
        return {
            "patient_id": patient_id,
            "vital_type": vital_type,
            "hours": hours,
            "statistics": None,
            "message": "No data available for the specified period"
        }

@router.post("/alerts")
async def store_device_alert(alert: DeviceAlertRequest, request: Request):
    """Store a device alert in TimescaleDB"""
    start_time = time.time()
    
    success = await VitalsService.store_device_alert(
        device_id=alert.device_id,
        patient_id=alert.patient_id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        message=alert.message,
        metadata=alert.metadata
    )
    
    execution_time = int((time.time() - start_time) * 1000)
    
    # Log ESP32 device alert audit event
    await AuditService.log_esp32_event(
        device_id=alert.device_id,
        action="device_alert",
        description=f"ESP32 generated {alert.severity} alert: {alert.message}",
        patient_id=alert.patient_id,
        severity=alert.severity,
        device_metadata={
            "alert_type": alert.alert_type,
            "alert_message": alert.message,
            "processing_time_ms": execution_time,
            "source_ip": request.client.host if request.client else None,
            **(alert.metadata if alert.metadata else {})
        },
        success=success,
        error_message=None if success else "Failed to store device alert in database"
    )
    
    if success:
        return {"message": "Device alert stored successfully", "execution_time_ms": execution_time}
    else:
        raise HTTPException(status_code=500, detail="Failed to store device alert")

@router.get("/alerts")
async def get_active_alerts(patient_id: Optional[str] = Query(default=None)):
    """Get active alerts for a patient or all patients"""
    alerts = await VitalsService.get_active_alerts(patient_id)
    return {"alerts": alerts}

@router.get("/types")
async def get_vital_types():
    """Get list of supported vital types"""
    return {
        "vitalTypes": [
            {"type": "heartRate", "unit": "bpm", "normalRange": [60, 100]},
            {"type": "bloodPressureSystolic", "unit": "mmHg", "normalRange": [90, 140]},
            {"type": "bloodPressureDiastolic", "unit": "mmHg", "normalRange": [60, 90]},
            {"type": "temperature", "unit": "celsius", "normalRange": [36.1, 37.2]},
            {"type": "oxygenSaturation", "unit": "%", "normalRange": [95, 100]},
            {"type": "respiratoryRate", "unit": "breaths/min", "normalRange": [12, 20]},
            {"type": "glucose", "unit": "mg/dL", "normalRange": [70, 140]},
            {"type": "bloodPressureMean", "unit": "mmHg", "normalRange": [70, 105]}
        ]
    }

@router.get("/timeseries/{patient_id}")
async def get_patient_vital_timeseries(
    patient_id: str,
    hours_back: int = Query(default=24, description="Hours of data to retrieve"),
    vital_type: Optional[str] = Query(default=None, description="Filter by specific vital type")
):
    """Get time-series vital data from TimescaleDB for charts"""
    try:
        from datetime import datetime, timedelta, timezone
        import asyncpg
        from app.core.config import settings
        
        # Connect to TimescaleDB
        conn = await asyncpg.connect(settings.TIMESCALE_URL)
        
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours_back)
            
            # Build query with optional vital type filter
            base_query = """
                SELECT 
                    timestamp,
                    "deviceId",
                    "patientId",
                    "vitalType",
                    value,
                    unit,
                    "qualityIndicator",
                    metadata
                FROM vital_readings
                WHERE "patientId" = $1 
                AND timestamp >= $2 
                AND timestamp <= $3
            """
            
            if vital_type:
                query = base_query + " AND \"vitalType\" = $4 ORDER BY timestamp ASC"
                rows = await conn.fetch(query, patient_id, start_time, end_time, vital_type)
            else:
                query = base_query + " ORDER BY timestamp ASC"
                rows = await conn.fetch(query, patient_id, start_time, end_time)
            
            # Convert to JSON-serializable format
            results = []
            for row in rows:
                results.append({
                    "timestamp": row["timestamp"].isoformat(),
                    "deviceId": row["deviceId"],
                    "patientId": row["patientId"],
                    "vitalType": row["vitalType"],
                    "value": float(row["value"]),
                    "unit": row["unit"],
                    "qualityIndicator": row["qualityIndicator"],
                    "metadata": row["metadata"]
                })
            
            return results
            
        finally:
            await conn.close()
            
    except Exception as e:
        print(f"Error fetching vital timeseries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch vital data: {str(e)}")