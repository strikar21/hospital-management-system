# Fixed ESP32 Ingestion Endpoint for 500 Watches
# Replace the existing /ingest/vitals endpoint

from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional, Dict, Any
import asyncio
import asyncpg
import json
from datetime import datetime, timezone
from pydantic import BaseModel

router = APIRouter(prefix="/ingest")

class VitalReading(BaseModel):
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

@router.post("/vitals", status_code=201)
async def ingest_esp32_vitals(
    vital_data: VitalReading,
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
            vitals_to_store = []
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
                "next_reading": 1  # Expect next reading in 1 second
            }
            
        finally:
            await timescale_conn.close()
            
    except Exception as e:
        # Log error but don't block other watches
        print(f"ESP32 ingestion error: {e}")
        raise HTTPException(status_code=500, detail="Ingestion failed")

# Connection pooling for TimescaleDB (high performance)
timescale_pool = None

async def get_timescale_connection():
    """Get optimized TimescaleDB connection"""
    global timescale_pool
    
    if timescale_pool is None:
        timescale_pool = await asyncpg.create_pool(
            "postgresql://hospital_user:hospital_pass@timescaledb:5432/hospital_vitals",
            min_size=20,        # Pool for 500 concurrent watches
            max_size=100,
            command_timeout=5   # Fast timeout for high throughput
        )
    
    return await timescale_pool.acquire()

# Cached device token validation (Redis recommended)
device_token_cache = {}

async def validate_device_token_cached(token: str) -> Optional[Dict]:
    """Fast cached device validation"""
    
    # Check memory cache first (1-second TTL)
    if token in device_token_cache:
        cached_data, cached_time = device_token_cache[token]
        if (datetime.now().timestamp() - cached_time) < 1.0:
            return cached_data
    
    # Query database for token validation
    try:
        from app.db.database import database
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
            # Cache for 1 second to reduce DB load
            device_token_cache[token] = (device_info, datetime.now().timestamp())
            return device_info
        
        return None
        
    except Exception:
        return None

async def check_vitals_for_alerts(patient_id: str, device_id: str, vitals: Dict[str, float]):
    """
    Non-blocking alert detection
    Runs in background to not slow down ingestion
    """
    try:
        # Quick threshold checks
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
                
                # Broadcast to WebSocket clients (tablets/displays)
                await broadcast_alerts_to_tablets(patient_id, alerts)
                
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

async def broadcast_alerts_to_tablets(patient_id: str, alerts: list):
    """Send alerts to Android tablets via WebSocket"""
    # Implementation depends on your WebSocket manager
    pass

# Batch ingestion for BLE fallback (3-4 watches via tablet)
@router.post("/vitals/batch", status_code=201)
async def ingest_vitals_batch_from_tablet(
    batch_data: Dict[str, Any],
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token")
):
    """
    BLE BACKUP: Tablet forwards 3-4 watches when WiFi fails
    Much lower volume than primary WiFi ingestion
    """
    
    try:
        device_id = batch_data.get("device_id")
        patient_id = batch_data.get("patient_id") 
        readings = batch_data.get("readings", [])
        source = batch_data.get("source", "tablet_ble")
        
        if not readings:
            return {"status": "no_data", "processed": 0}
        
        timescale_conn = await get_timescale_connection()
        stored_count = 0
        
        try:
            for reading in readings:
                timestamp = datetime.fromisoformat(reading["timestamp"].replace('Z', '+00:00'))
                vitals = reading.get("vitals", {})
                
                # Insert each vital type
                for vital_type, value in vitals.items():
                    if value is not None:
                        await timescale_conn.execute("""
                            INSERT INTO vital_readings 
                            (timestamp, device_id, patient_id, vital_type, value, unit, quality_indicator, metadata)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """, timestamp, device_id, patient_id, vital_type, float(value),
                             get_unit_for_vital(vital_type), "good", 
                             json.dumps({"source": source, "via_tablet": True}))
                        stored_count += 1
            
            return {
                "status": "success", 
                "processed": stored_count,
                "source": "tablet_ble_backup"
            }
            
        finally:
            await timescale_conn.close()
            
    except Exception as e:
        print(f"Tablet batch ingestion error: {e}")
        raise HTTPException(status_code=500, detail="Batch processing failed")

def get_unit_for_vital(vital_type: str) -> str:
    """Get unit for vital sign"""
    units = {
        "heart_rate": "BPM",
        "blood_pressure_systolic": "mmHg",
        "blood_pressure_diastolic": "mmHg", 
        "temperature": "F",
        "oxygen_saturation": "%",
        "respiratory_rate": "/min"
    }
    return units.get(vital_type, "")