from fastapi import APIRouter, Depends, HTTPException, Request, Header
from typing import List, Optional, Dict, Any
from sqlalchemy import insert
from datetime import datetime, timezone
import asyncio
import asyncpg
import json
from pydantic import BaseModel

from app.schemas.device import (
    VitalReadingCreate, VitalReadingResponse, VitalsBatch,
    DoorScanEventCreate, DoorScanEventResponse
)
from app.models.device import VitalReading, DoorScanEvent
from app.db.database import database
from app.services.device_service import DeviceService
from app.services.websocket_manager import WebSocketManager
from app.core.security import authenticate_device_token, check_device_rate_limit, require_device_capability

router = APIRouter(prefix="/ingest")

class ESP32VitalReading(BaseModel):
    device_id: str
    patient_id: str
    heart_rate: Optional[float] = None
    blood_pressure_systolic: Optional[float] = None
    blood_pressure_diastolic: Optional[float] = None
    temperature: Optional[float] = None
    oxygen_saturation: Optional[float] = None
    respiratory_rate: Optional[float] = None
    reading_timestamp: str
    signal_quality: Optional[float] = 0.95
    battery_level: Optional[int] = None

# Connection pooling for TimescaleDB
timescale_pool = None

async def get_timescale_connection():
    """Get optimized TimescaleDB connection"""
    global timescale_pool
    
    if timescale_pool is None:
        timescale_pool = await asyncpg.create_pool(
            "postgresql://hospital_user:hospital_pass@localhost:5434/hospital_vitals",
            min_size=20,
            max_size=100,
            command_timeout=5
        )
    
    return await timescale_pool.acquire()

# Cached device token validation
device_token_cache = {}

async def validate_device_token_cached(token: str) -> Optional[Dict]:
    """Fast cached device validation"""
    
    if token in device_token_cache:
        cached_data, cached_time = device_token_cache[token]
        if (datetime.now().timestamp() - cached_time) < 1.0:
            return cached_data
    
    try:
        device_query = """
            SELECT device_id, name, device_type, capabilities, status
            FROM devices 
            WHERE device_token = :token 
            AND is_active = true 
            AND status = 'online'
        """
        device = await database.fetch_one(device_query, {"token": token})
        
        if device:
            device_info = dict(device)
            device_token_cache[token] = (device_info, datetime.now().timestamp())
            return device_info
        
        return None
        
    except Exception:
        return None

@router.post("/vitals", status_code=201)
async def ingest_esp32_vitals(
    vital_data: ESP32VitalReading,
    x_device_token: str = Header(..., alias="X-Device-Token")
):
    """
    HIGH-THROUGHPUT ESP32 WiFi Ingestion
    Handles 500 watches × 1Hz = 500 requests/second
    """
    
    try:
        # Quick device token validation (cached for performance)
        device_info = await validate_device_token_cached(x_device_token)
        if not device_info:
            raise HTTPException(status_code=401, detail="Invalid device token")
        
        # Validate device matches token
        if device_info["device_id"] != vital_data.device_id:
            raise HTTPException(status_code=403, detail="Device ID mismatch")
        
        # Connect directly to TimescaleDB (bypassed main DB for performance)
        timescale_conn = await get_timescale_connection()
        
        try:
            # Insert all vital types in one transaction for speed
            reading_time = datetime.fromisoformat(vital_data.reading_timestamp.replace('Z', '+00:00'))
            
            # Map vitals to database format
            vital_mappings = [
                ("heart_rate", vital_data.heart_rate, "BPM"),
                ("blood_pressure_systolic", vital_data.blood_pressure_systolic, "mmHg"),
                ("blood_pressure_diastolic", vital_data.blood_pressure_diastolic, "mmHg"), 
                ("temperature", vital_data.temperature, "F"),
                ("oxygen_saturation", vital_data.oxygen_saturation, "%"),
                ("respiratory_rate", vital_data.respiratory_rate, "/min")
            ]
            
            # Batch insert for performance
            insert_values = []
            for vital_type, value, unit in vital_mappings:
                if value is not None:
                    insert_values.append((
                        reading_time,
                        vital_data.device_id, 
                        vital_data.patient_id,
                        vital_type,
                        float(value),
                        unit,
                        "excellent" if vital_data.signal_quality > 0.9 else "good",
                        json.dumps({
                            "source": "esp32_wifi",
                            "signal_quality": vital_data.signal_quality,
                            "battery_level": vital_data.battery_level
                        })
                    ))
            
            if insert_values:
                # High-performance batch insert
                await timescale_conn.executemany("""
                    INSERT INTO vital_readings 
                    (timestamp, device_id, patient_id, vital_type, value, unit, quality_indicator, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, insert_values)
                
                # Fast alert check (non-blocking)
                asyncio.create_task(check_vitals_for_alerts(
                    vital_data.patient_id, 
                    vital_data.device_id,
                    dict((vt, val) for vt, val, _ in vital_mappings if val is not None)
                ))
            
            return {
                "status": "success",
                "stored_vitals": len(insert_values),
                "patient_id": vital_data.patient_id,
                "next_reading": 1
            }
            
        finally:
            await timescale_conn.close()
            
    except Exception as e:
        import traceback
        error_details = f"ESP32 ingestion error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_details)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

async def check_vitals_for_alerts(patient_id: str, device_id: str, vitals: Dict[str, float]):
    """
    Non-blocking alert detection
    Runs in background to not slow down ingestion
    """
    try:
        alerts = []
        
        # Heart rate thresholds
        if "heart_rate" in vitals:
            hr = vitals["heart_rate"]
            if hr > 120:
                alerts.append(create_alert("heart_rate", hr, "critical", "Tachycardia"))
            elif hr > 100:
                alerts.append(create_alert("heart_rate", hr, "warning", "Elevated HR"))
        
        # Temperature thresholds  
        if "temperature" in vitals:
            temp = vitals["temperature"]
            if temp > 102.0:
                alerts.append(create_alert("temperature", temp, "critical", "High fever"))
            elif temp > 100.4:
                alerts.append(create_alert("temperature", temp, "warning", "Fever"))
        
        # Oxygen saturation thresholds
        if "oxygen_saturation" in vitals:
            o2 = vitals["oxygen_saturation"]
            if o2 < 90:
                alerts.append(create_alert("oxygen_saturation", o2, "critical", "Hypoxemia"))
            elif o2 < 95:
                alerts.append(create_alert("oxygen_saturation", o2, "warning", "Low O2"))
        
        # Store alerts in TimescaleDB if any
        if alerts:
            timescale_conn = await get_timescale_connection()
            try:
                for alert in alerts:
                    await timescale_conn.execute("""
                        INSERT INTO device_alerts_ts 
                        (timestamp, device_id, patient_id, alert_type, severity, message, metadata)
                        VALUES (NOW(), $1, $2, $3, $4, $5, $6)
                    """, device_id, patient_id, alert["type"], alert["severity"], 
                         alert["message"], json.dumps(alert["metadata"]))
                
            finally:
                await timescale_conn.close()
                
    except Exception as e:
        print(f"Alert processing error: {e}")

def create_alert(vital_type: str, value: float, severity: str, description: str):
    """Create alert object"""
    return {
        "type": f"{vital_type}_{severity}",
        "severity": severity,
        "message": f"{description}: {vital_type.replace('_', ' ').title()} {value}",
        "metadata": {
            "vital_type": vital_type,
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "requires_attention": severity == "critical"
        }
    }

@router.post("/vitals/batch", status_code=201)
async def ingest_vitals_batch(
    batch_data: VitalsBatch,
    request: Request,
    device_info: Dict[str, Any] = Depends(check_device_rate_limit)
):
    """Ingest multiple vital readings in batch"""
    
    websocket_manager: WebSocketManager = request.app.state.websocket_manager
    
    try:
        processed_readings = []
        
        for vital_data in batch_data.readings:
            # Validate device_id matches batch
            if vital_data.device_id != batch_data.device_id:
                continue
            
            vital_dict = vital_data.dict()
            vital_dict["received_timestamp"] = datetime.utcnow()
            vital_dict["is_valid"] = True
            
            query = insert(VitalReading).values(**vital_dict)
            vital_id = await database.execute(query)
            
            processed_readings.append(vital_id)
            
            # Broadcast each reading
            streaming_data = {
                "id": vital_id,
                "device_id": vital_data.device_id,
                "patient_id": vital_data.patient_id,
                "vitals": {
                    "heart_rate": vital_data.heart_rate,
                    "blood_pressure_systolic": vital_data.blood_pressure_systolic,
                    "blood_pressure_diastolic": vital_data.blood_pressure_diastolic,
                    "temperature": vital_data.temperature,
                    "oxygen_saturation": vital_data.oxygen_saturation,
                    "respiratory_rate": vital_data.respiratory_rate
                },
                "reading_timestamp": vital_data.reading_timestamp.isoformat(),
                "signal_quality": vital_data.signal_quality
            }
            
            await websocket_manager.broadcast_vitals_data(streaming_data)
        
        return {
            "status": "batch_processed",
            "device_id": batch_data.device_id,
            "processed_count": len(processed_readings),
            "total_submitted": len(batch_data.readings),
            "reading_ids": processed_readings
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process batch: {str(e)}")

@router.post("/door-scan", response_model=DoorScanEventResponse, status_code=201)
async def ingest_door_scan_event(
    scan_data: DoorScanEventCreate,
    request: Request,
    device_info: Dict[str, Any] = Depends(require_device_capability("access_control"))
):
    """Ingest door scanner event"""
    
    websocket_manager: WebSocketManager = request.app.state.websocket_manager
    
    try:
        # Store scan event
        scan_dict = scan_data.dict()
        scan_dict["received_timestamp"] = datetime.utcnow()
        
        query = insert(DoorScanEvent).values(**scan_dict)
        event_id = await database.execute(query)
        
        # Fetch the created record
        from sqlalchemy import select
        fetch_query = select(DoorScanEvent).where(DoorScanEvent.id == event_id)
        event_record = await database.fetch_one(fetch_query)
        
        # Broadcast door event
        door_event_data = {
            "id": event_id,
            "device_id": scan_data.device_id,
            "card_id": scan_data.card_id,
            "user_id": scan_data.user_id,
            "access_granted": scan_data.access_granted,
            "door_location": scan_data.door_location,
            "scan_timestamp": scan_data.scan_timestamp.isoformat(),
            "event_data": scan_data.event_data
        }
        
        await websocket_manager.broadcast_door_event(door_event_data)
        
        return DoorScanEventResponse.from_orm(event_record)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process door scan: {str(e)}")

@router.post("/raw-data")
async def ingest_raw_sensor_data(
    device_id: str,
    sensor_type: str,
    data: Dict[str, Any],
    timestamp: Optional[datetime] = None,
    request: Request = None,
    device_info: Dict[str, Any] = Depends(authenticate_device_token)
):
    """Ingest raw sensor data for processing"""
    
    if not timestamp:
        timestamp = datetime.utcnow()
    
    # TODO: Process raw data based on sensor_type
    # This could trigger data processing pipelines
    
    # For now, just acknowledge receipt
    return {
        "status": "raw_data_received",
        "device_id": device_id,
        "sensor_type": sensor_type,
        "timestamp": timestamp.isoformat(),
        "data_size": len(str(data))
    }

@router.get("/health")
async def ingestion_health():
    """Health check for ingestion service"""
    return {
        "status": "healthy",
        "service": "data_ingestion",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }