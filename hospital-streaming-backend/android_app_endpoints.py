# Android App Integration Endpoints
# Add these to hospital-streaming-backend/app/api/v1/mobile.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
import asyncio
from datetime import datetime, timezone
import json

router = APIRouter(prefix="/mobile")

@router.post("/devices/pair")
async def pair_device_with_patient(
    device_id: str,
    patient_id: str,
    app_session_id: str,
    location: Optional[str] = None
):
    """
    Android app calls this when watch is tapped to tablet
    - Validates device exists and is available
    - Links device to patient 
    - Returns patient data for display
    """
    
    # Check if device exists and is available
    device_query = """
        SELECT device_id, name, status, assignment_status 
        FROM devices 
        WHERE device_id = :device_id AND is_active = true
    """
    device = await database.fetch_one(device_query, {"device_id": device_id})
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device["assignment_status"] != "free":
        raise HTTPException(status_code=409, detail="Device already assigned")
    
    # Get patient data
    patient_query = """
        SELECT id, name, age, gender, diagnosis, ward, room, bed_number,
               assigned_doctor, admission_date, status
        FROM patients 
        WHERE id = :patient_id AND is_active = true
    """
    patient = await database.fetch_one(patient_query, {"patient_id": patient_id})
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Create device assignment
    assignment_id = f"ASSIGN_{int(datetime.now().timestamp() * 1000)}"
    assign_query = """
        INSERT INTO device_assignments 
        (id, device_id, patient_id, assigned_by, assignment_reason, status)
        VALUES (:id, :device_id, :patient_id, :assigned_by, :reason, 'active')
    """
    
    await database.execute(assign_query, {
        "id": assignment_id,
        "device_id": device_id,
        "patient_id": patient_id,
        "assigned_by": app_session_id,
        "reason": f"Tap-to-pair via Android app at {location or 'unknown location'}"
    })
    
    # Update device status
    await database.execute(
        "UPDATE devices SET assignment_status = 'assigned', assigned_to = :patient_id WHERE device_id = :device_id",
        {"patient_id": patient_id, "device_id": device_id}
    )
    
    # Return patient data for app display
    return {
        "success": True,
        "assignment_id": assignment_id,
        "patient": dict(patient),
        "device": dict(device),
        "streaming_config": {
            "batch_size": 5,  # Send every 5 seconds
            "batch_timeout": 10,  # Max wait 10 seconds
            "retry_count": 3,
            "endpoint": f"/mobile/vitals/batch/{patient_id}"
        }
    }

@router.post("/vitals/batch/{patient_id}")
async def receive_vitals_batch_from_app(
    patient_id: str,
    batch_data: Dict,
    app_session_id: str = None
):
    """
    Android app sends batched vital signs (every 5 seconds)
    - Receives multiple readings in one request
    - Stores in TimescaleDB 
    - Returns any alerts generated
    """
    
    device_id = batch_data.get("device_id")
    readings = batch_data.get("readings", [])
    app_info = batch_data.get("app_info", {})
    
    if not readings:
        raise HTTPException(status_code=400, detail="No readings provided")
    
    stored_count = 0
    alerts_generated = []
    
    # Connect to TimescaleDB for vital storage
    timescale_conn = await asyncpg.connect("postgresql://hospital_user:hospital_pass@timescaledb:5432/hospital_vitals")
    
    try:
        for reading in readings:
            timestamp = reading.get("timestamp")
            vitals = reading.get("vitals", {})
            quality = reading.get("quality", 0.95)
            
            # Store each vital type separately in TimescaleDB
            for vital_type, value in vitals.items():
                if value is not None:
                    await timescale_conn.execute("""
                        INSERT INTO vital_readings 
                        (timestamp, device_id, patient_id, vital_type, value, unit, quality_indicator, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """, 
                    timestamp, device_id, patient_id, vital_type, value, 
                    get_unit_for_vital(vital_type), 
                    "excellent" if quality > 0.9 else "good" if quality > 0.7 else "poor",
                    json.dumps({
                        "source": "android_app",
                        "app_version": app_info.get("version"),
                        "signal_quality": quality,
                        "batch_sequence": batch_data.get("sequence", 0)
                    })
                    )
                    stored_count += 1
                    
                    # Check for alerts
                    alert = check_vital_threshold(vital_type, value, patient_id)
                    if alert:
                        # Store alert in TimescaleDB
                        await timescale_conn.execute("""
                            INSERT INTO device_alerts_ts
                            (timestamp, device_id, patient_id, alert_type, severity, message, metadata)
                            VALUES (NOW(), $1, $2, $3, $4, $5, $6)
                        """, device_id, patient_id, alert["type"], alert["severity"], alert["message"], 
                        json.dumps(alert["metadata"]))
                        
                        alerts_generated.append(alert)
        
        # Update patient's current vitals in main database
        await update_patient_current_vitals(patient_id, readings[-1]["vitals"])
        
    finally:
        await timescale_conn.close()
    
    return {
        "success": True,
        "stored_readings": stored_count,
        "alerts": alerts_generated,
        "next_batch_in": 5  # seconds
    }

def get_unit_for_vital(vital_type: str) -> str:
    """Get appropriate unit for vital sign type"""
    units = {
        "heart_rate": "BPM",
        "blood_pressure_systolic": "mmHg", 
        "blood_pressure_diastolic": "mmHg",
        "temperature": "F",
        "oxygen_saturation": "%",
        "respiratory_rate": "/min",
        "ecg": "mV",
        "eeg": "μV"
    }
    return units.get(vital_type, "")

def check_vital_threshold(vital_type: str, value: float, patient_id: str) -> Optional[Dict]:
    """Check if vital sign exceeds threshold and generate alert"""
    
    thresholds = {
        "heart_rate": {"warning": 100, "critical": 120},
        "blood_pressure_systolic": {"warning": 140, "critical": 160},
        "temperature": {"warning": 100.4, "critical": 102.0},
        "oxygen_saturation": {"warning": 95, "critical": 90, "operator": "lt"},
        "respiratory_rate": {"warning": 24, "critical": 30}
    }
    
    if vital_type not in thresholds:
        return None
        
    config = thresholds[vital_type]
    operator = config.get("operator", "gt")
    
    severity = None
    if operator == "gt":
        if value >= config["critical"]:
            severity = "critical"
        elif value >= config["warning"]:
            severity = "warning"
    else:  # less than (for oxygen sat)
        if value <= config["critical"]:
            severity = "critical" 
        elif value <= config["warning"]:
            severity = "warning"
    
    if severity:
        return {
            "type": f"{vital_type}_{severity}",
            "severity": severity,
            "message": f"{vital_type.replace('_', ' ').title()}: {value} - {severity.title()} threshold exceeded",
            "metadata": {
                "vital_type": vital_type,
                "value": value,
                "threshold": config[severity],
                "patient_id": patient_id,
                "auto_generated": True,
                "requires_attention": severity == "critical"
            }
        }
    
    return None

@router.post("/devices/unpair/{device_id}")
async def unpair_device(device_id: str, reason: str = "Manual unpair"):
    """
    Unpair device from patient when tablet session ends
    """
    
    # Update assignment status
    await database.execute("""
        UPDATE device_assignments 
        SET status = 'completed', unassigned_at = NOW(), unassign_reason = :reason
        WHERE device_id = :device_id AND status = 'active'
    """, {"device_id": device_id, "reason": reason})
    
    # Free up device
    await database.execute("""
        UPDATE devices 
        SET assignment_status = 'free', assigned_to = NULL 
        WHERE device_id = :device_id
    """, {"device_id": device_id})
    
    return {"success": True, "message": f"Device {device_id} unpaired successfully"}

@router.get("/devices/nearby")
async def discover_nearby_devices(location: Optional[str] = None):
    """
    Return list of available devices for BLE scanning
    Used by Android app to know which devices to look for
    """
    
    query = """
        SELECT device_id, name, device_type, location, battery_level, last_heartbeat
        FROM devices 
        WHERE assignment_status = 'free' 
        AND status = 'online' 
        AND is_active = true
    """
    
    if location:
        query += " AND location = :location"
        devices = await database.fetch_all(query, {"location": location})
    else:
        devices = await database.fetch_all(query)
    
    return {
        "available_devices": [dict(device) for device in devices],
        "scan_config": {
            "scan_duration": 10,  # seconds
            "service_uuid": "6E400001-B5A3-F393-E0A9-E50E24DCCA9E",  # Nordic UART
            "timeout": 30
        }
    }