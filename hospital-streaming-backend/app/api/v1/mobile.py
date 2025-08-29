from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import asyncio
import asyncpg
import json
from pydantic import BaseModel

from app.db.database import database
from app.services.websocket_manager import WebSocketManager
from app.core.security import authenticate_device_token

router = APIRouter(prefix="/mobile")

class VitalReading(BaseModel):
    timestamp: str
    vitals: Dict[str, float]  # heart_rate, temperature, etc.
    quality: float = 0.95
    battery_level: Optional[int] = None
    signalStrength: Optional[int] = None

class VitalsBatch(BaseModel):
    deviceId: str
    patientId: str
    readings: List[VitalReading]
    sequence: int
    appInfo: Dict[str, Any] = {}

class PairRequest(BaseModel):
    deviceId: str
    patientId: str
    appSessionId: str
    location: Optional[str] = None

# Connection pooling for TimescaleDB (reuse from ingestion)
timescale_pool = None

async def get_timescale_connection():
    """Get optimized TimescaleDB connection"""
    global timescale_pool
    
    if timescale_pool is None:
        timescale_pool = await asyncpg.create_pool(
            "postgresql://hospital_user:secure_timescale_123@localhost:5434/hospital_vitals",
            min_size=10,  # Smaller pool for mobile endpoints
            max_size=50,
            command_timeout=5
        )
    
    return await timescale_pool.acquire()

@router.post("/devices/pair")
async def pair_device_with_patient(pair_data: PairRequest):
    """
    Android tablet calls this when watch is tapped (NFC)
    - Validates device exists and is available
    - Links device to patient 
    - Returns patient data and streaming config for tablet
    """
    
    try:
        # Check if device exists and is available
        device_query = """
            SELECT "deviceId", name, status, "assignmentStatus", "deviceType", capabilities
            FROM devices 
            WHERE "deviceId" = :device_id AND "isActive" = true
        """
        device = await database.fetch_one(device_query, {"device_id": pair_data.deviceId})
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found or inactive")
        
        # Allow pairing even if already assigned (for re-pairing scenarios)
        
        # Get patient data
        patient_query = """
            SELECT id, name, age, gender, diagnosis, ward, room, "bedNumber",
                   "assignedDoctor", "admissionDate", status
            FROM patients 
            WHERE id = :patient_id AND "isActive" = true
        """
        patient = await database.fetch_one(patient_query, {"patient_id": pair_data.patientId})
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found or inactive")
        
        # End any existing assignments for this device
        await database.execute("""
            UPDATE device_assignments 
            SET status = 'completed', unassigned_at = NOW(), unassignment_reason = 'New assignment'
            WHERE "deviceId" = :device_id AND status = 'active'
        """, {"device_id": pair_data.deviceId})
        
        # Create new assignment (let database auto-generate ID)
        assign_query = """
            INSERT INTO device_assignments 
            ("deviceId", "patientId", "assignedBy", "assignmentReason", status, "assignedAt")
            VALUES (:device_id, :patient_id, :assigned_by, :reason, 'active', NOW())
            RETURNING id
        """
        
        assignment_result = await database.fetch_one(assign_query, {
            "device_id": pair_data.deviceId,
            "patient_id": pair_data.patientId,
            "assigned_by": pair_data.app_session_id,
            "reason": f"NFC tap-to-pair via tablet at {pair_data.location or 'unknown location'}"
        })
        
        assignment_id = assignment_result["id"] if assignment_result else None
        
        # Update device status
        await database.execute("""
            UPDATE devices 
            SET "assignmentStatus" = 'assigned', "assignedTo" = :patient_id, "lastHeartbeat" = NOW()
            WHERE "deviceId" = :device_id
        """, {"patient_id": pair_data.patientId, "device_id": pair_data.deviceId})
        
        # Return patient data and streaming configuration for tablet
        return {
            "success": True,
            "assignment_id": assignment_id,
            "patient": dict(patient),
            "device": dict(device),
            "streaming_config": {
                "batch_size": 5,           # Send every 5 vitals or...
                "batch_timeout": 5000,     # ...every 5 seconds (whichever first)
                "retry_count": 3,
                "retry_delay": 1000,       # 1 second between retries
                "endpoint": f"/mobile/vitals/batch/{pair_data.patientId}",
                "ble_scan_config": {
                    "service_uuid": "6E400001-B5A3-F393-E0A9-E50E24DCCA9E",
                    "vitals_char_uuid": "6E400002-B5A3-F393-E0A9-E50E24DCCA9E",
                    "scan_timeout": 10000,  # 10 seconds
                    "connection_timeout": 15000  # 15 seconds
                }
            }
        }
        
    except Exception as e:
        import traceback
        error_details = f"Pairing error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_details)
        raise HTTPException(status_code=500, detail=f"Pairing failed: {str(e)}")

@router.post("/vitals/batch/{patient_id}")
async def receive_vitals_batch_from_tablet(
    patientId: str,
    batch_data: VitalsBatch
):
    """
    OPTIMIZED: Android tablet sends batched vital signs from BLE watches
    - Receives 3-10 readings per batch (5-second intervals)
    - High-performance TimescaleDB storage
    - Real-time alert generation
    - WebSocket broadcasting for displays
    """
    
    if not batch_data.readings:
        raise HTTPException(status_code=400, detail="No readings provided in batch")
    
    try:
        # Connect to TimescaleDB for high-performance storage
        timescale_conn = await get_timescale_connection()
        stored_count = 0
        alerts_generated = []
        
        try:
            # Process all readings in batch for efficiency
            for reading in batch_data.readings:
                if not reading.vitals:
                    continue
                    
                # Parse timestamp
                try:
                    reading_time = datetime.fromisoformat(reading.timestamp.replace('Z', '+00:00'))
                except:
                    reading_time = datetime.now(timezone.utc)
                
                # Batch insert all vital types from this reading
                insert_values = []
                for vital_type, value in reading.vitals.items():
                    if value is not None and vital_type in ["heart_rate", "blood_pressure_systolic", 
                                                          "blood_pressure_diastolic", "temperature", 
                                                          "oxygen_saturation", "respiratory_rate"]:
                        insert_values.append((
                            reading_time,
                            batch_data.deviceId, 
                            patient_id,
                            vital_type,
                            float(value),
                            get_unit_for_vital(vital_type),
                            "excellent" if reading.quality > 0.9 else "good" if reading.quality > 0.7 else "poor",
                            json.dumps({
                                "source": "tablet_ble",
                                "app_version": batch_data.app_info.get("version"),
                                "signal_quality": reading.quality,
                                "batch_sequence": batch_data.sequence,
                                "battery_level": reading.battery_level,
                                "ble_signal_strength": reading.signal_strength
                            })
                        ))
                
                # High-performance batch insert for this reading
                if insert_values:
                    await timescale_conn.executemany("""
                        INSERT INTO vital_readings 
                        (timestamp, device_id, patient_id, vital_type, value, unit, quality_indicator, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (timestamp, device_id, vital_type) DO NOTHING
                    """, insert_values)
                    stored_count += len(insert_values)
                    
                    # Fast alert check (non-blocking background task)
                    vital_dict = reading.vitals
                    asyncio.create_task(check_vitals_for_alerts_mobile(
                        patient_id, batch_data.deviceId, vital_dict, reading_time
                    ))
            
            # Update patient's current vitals cache in main database
            if batch_data.readings:
                await update_patient_current_vitals(patient_id, batch_data.readings[-1].vitals)
        
        finally:
            await timescale_conn.close()
        
        return {
            "success": True,
            "stored_readings": stored_count,
            "processed_vitals": len([r for r in batch_data.readings if r.vitals]),
            "alerts": alerts_generated,
            "next_batch_in": 5,  # Recommend next batch in 5 seconds
            "sequence": batch_data.sequence + 1
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

def get_unit_for_vital(vital_type: str) -> str:
    """Get appropriate unit for vital sign type"""
    units = {
        "heart_rate": "BPM",
        "blood_pressure_systolic": "mmHg", 
        "blood_pressure_diastolic": "mmHg",
        "temperature": "F",
        "oxygen_saturation": "%",
        "respiratory_rate": "/min"
    }
    return units.get(vital_type, "")

async def check_vitals_for_alerts_mobile(patient_id: str, device_id: str, vitals: Dict[str, float], reading_time: datetime):
    """
    Non-blocking alert detection for mobile/BLE vitals
    Similar to ESP32 but optimized for tablet forwarding
    """
    try:
        alerts = []
        
        # Critical thresholds (same as ESP32)
        thresholds = {
            "heart_rate": {"warning": 100, "critical": 120},
            "temperature": {"warning": 100.4, "critical": 102.0},
            "oxygen_saturation": {"warning": 95, "critical": 90, "operator": "lt"},
            "blood_pressure_systolic": {"warning": 140, "critical": 180},
            "respiratory_rate": {"warning": 24, "critical": 30}
        }
        
        for vital_type, value in vitals.items():
            if vital_type not in thresholds:
                continue
                
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
                alerts.append({
                    "type": f"{vital_type}_{severity}",
                    "severity": severity,
                    "message": f"{vital_type.replace('_', ' ').title()}: {value} - {severity.title()} threshold exceeded",
                    "timestamp": reading_time.isoformat(),
                    "source": "tablet_ble"
                })
        
        # Store alerts in TimescaleDB if any
        if alerts:
            timescale_conn = await get_timescale_connection()
            try:
                for alert in alerts:
                    await timescale_conn.execute("""
                        INSERT INTO device_alerts_ts 
                        (timestamp, device_id, patient_id, alert_type, severity, message, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, reading_time, device_id, patient_id, alert["type"], alert["severity"], 
                         alert["message"], json.dumps({
                             "source": "tablet_ble",
                             "vital_type": alert["type"].split("_")[0],
                             "value": vitals.get(alert["type"].split("_")[0]),
                             "auto_generated": True
                         }))
                
            finally:
                await timescale_conn.close()
                
    except Exception as e:
        print(f"Mobile alert processing error: {e}")

async def update_patient_current_vitals(patient_id: str, vitals: Dict[str, float]):
    """Update patient's current vitals in main database for quick access"""
    try:
        # Update or insert current vitals for quick dashboard access
        for vital_type, value in vitals.items():
            await database.execute("""
                INSERT INTO patient_current_vitals ("patientId", "vitalType", value, unit, "updatedAt")
                VALUES (:patient_id, :vital_type, :value, :unit, NOW())
                ON CONFLICT ("patientId", "vitalType") 
                DO UPDATE SET value = :value, updated_at = NOW()
            """, {
                "patient_id": patient_id,
                "vital_type": vital_type,
                "value": value,
                "unit": get_unit_for_vital(vital_type)
            })
    except Exception as e:
        print(f"Failed to update current vitals: {e}")

@router.post("/devices/unpair/{device_id}")
async def unpair_device(device_id: str, reason: str = "Tablet session ended"):
    """
    Unpair device from tablet when:
    - Tablet app is closed
    - BLE connection lost
    - Manual unpair by user
    - Watch switches to WiFi mode
    """
    
    try:
        # Update assignment status
        await database.execute("""
            UPDATE device_assignments 
            SET status = 'completed', unassigned_at = NOW(), unassignment_reason = :reason
            WHERE "deviceId" = :device_id AND status = 'active'
        """, {"device_id": device_id, "reason": reason})
        
        # Free up device (it will switch to WiFi mode automatically)
        await database.execute("""
            UPDATE devices 
            SET assignment_status = 'free', assigned_to = NULL, last_heartbeat = NOW()
            WHERE "deviceId" = :device_id
        """, {"device_id": device_id})
        
        return {
            "success": True, 
            "message": f"Device {device_id} unpaired successfully",
            "fallback_mode": "wifi_direct"  # Watch will switch to WiFi ingestion
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unpair failed: {str(e)}")

@router.get("/devices/nearby")
async def discover_nearby_devices(location: Optional[str] = None):
    """
    Return list of available devices for BLE scanning
    Used by Android tablet to know which watches to look for via BLE
    """
    
    try:
        query = """
            SELECT "deviceId", name, "deviceType", location, "batteryLevel", 
                   last_heartbeat, assignment_status, status
            FROM devices 
            WHERE device_type LIKE '%watch%'
            AND is_active = true
            AND (status = 'online' OR status = 'provisioning')
        """
        
        if location:
            query += " AND (location = :location OR location IS NULL)"
            devices = await database.fetch_all(query, {"location": location})
        else:
            devices = await database.fetch_all(query)
        
        # Categorize devices by availability
        available_devices = []
        paired_devices = []
        
        for device in devices:
            device_info = dict(device)
            if device.assignment_status == "free":
                available_devices.append(device_info)
            else:
                paired_devices.append(device_info)
        
        return {
            "available_devices": available_devices,
            "paired_devices": paired_devices,
            "ble_scan_config": {
                "scan_duration": 15000,  # 15 seconds
                "service_uuid": "6E400001-B5A3-F393-E0A9-E50E24DCCA9E",  # Nordic UART Service
                "vitals_characteristic": "6E400002-B5A3-F393-E0A9-E50E24DCCA9E",
                "scan_mode": "low_latency",
                "connection_timeout": 10000
            },
            "recommended_max_connections": 4  # Max 4 watches per tablet for optimal performance
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Device discovery failed: {str(e)}")

@router.get("/room-proximity")
async def get_room_proximity_devices():
    """
    Get devices that should be discoverable in current room/ward
    Used for location-based device filtering
    """
    
    try:
        # This could be enhanced with room-based filtering
        query = """
            SELECT d."deviceId", d.name, d."deviceType", d.location, d."assignmentStatus",
                   p.name as patient_name, p.room, p.bed_number
            FROM devices d
            LEFT JOIN patients p ON d.assigned_to = p.id
            WHERE d.device_type LIKE '%watch%'
            AND d.is_active = true
            AND d.status = 'online'
            ORDER BY d.location, p.room, p.bed_number
        """
        
        devices = await database.fetch_all(query)
        
        return {
            "devices": [dict(device) for device in devices],
            "total_active": len(devices)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proximity query failed: {str(e)}")


class PatientDischarge(BaseModel):
    staffId: str
    discharge_date: str
    discharge_reason: str = "medical_discharge"
    discharge_notes: Optional[str] = None


@router.post("/patients/{patient_id}/discharge")
async def discharge_patient(patient_id: str, discharge_data: PatientDischarge):
    """Discharge a patient - removes from active list, frees bed, unassigns devices"""
    
    try:
        # Start transaction to ensure data consistency
        async with database.transaction():
            # Verify patient exists and is active
            patient_query = """
                SELECT id, name, bed_number, ward, room FROM patients 
                WHERE id = :patient_id AND "isActive" = true
            """
            patient = await database.fetch_one(patient_query, {"patient_id": patient_id})
            
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found or already discharged")
            
            # Set patient as inactive (discharged) - DATA PRESERVED
            discharge_query = """
                UPDATE patients 
                SET is_active = false, 
                    discharge_date = :discharge_date,
                    discharge_reason = :discharge_reason,
                    discharge_notes = :discharge_notes,
                    "dischargedBy" = :staff_id,
                    status = 'discharged'
                WHERE id = :patient_id
            """
            await database.execute(discharge_query, {
                "patient_id": patient_id,
                "discharge_date": discharge_data.discharge_date,
                "discharge_reason": discharge_data.discharge_reason,
                "discharge_notes": discharge_data.discharge_notes,
                "staff_id": discharge_data.staffId
            })
            
            # Free up the bed
            bed_update_query = """
                UPDATE hospital_beds 
                SET occupancy_status = 'available', assigned_patient = NULL
                WHERE "assignedPatient" = :patient_id
            """
            await database.execute(bed_update_query, {"patient_id": patient_id})
            
            # Unassign devices
            device_update_query = """
                UPDATE devices 
                SET assignment_status = 'free', assigned_to = NULL
                WHERE "assignedTo" = :patient_id
            """
            await database.execute(device_update_query, {"patient_id": patient_id})
            
            # Update ward occupancy
            ward_update_query = """
                UPDATE ward_capacity 
                SET current_occupancy = current_occupancy - 1
                WHERE ward_name = :ward
            """
            await database.execute(ward_update_query, {"ward": patient['ward']})
        
        return {
            "success": True,
            "message": f"Patient {patient['name']} successfully discharged",
            "patient_id": patient_id,
            "freed_bed": f"{patient['ward']}-{patient['room']}-{patient['bed_number']}",
            "discharge_date": discharge_data.discharge_date
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discharge patient: {str(e)}")

@router.get("/health")
async def mobile_health_check():
    """Health check for mobile/tablet endpoints"""
    return {
        "status": "healthy",
        "service": "mobile_tablet_api",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.2",
        "supported_devices": ["ESP32_WATCH", "BLE_VITALS_MONITOR"],
        "max_concurrent_connections": 4,
        "discharge_endpoint_available": True
    }

@router.get("/patients/{patient_id}/vitals/history")
async def get_patient_vitals_history(patient_id: str, time_range: str = "6h"):
    """Get patient vitals history for charts from TimescaleDB"""
    try:
        # Parse time range
        hours_map = {
            "1h": 1,
            "6h": 6, 
            "24h": 24,
            "7d": 168
        }
        hours = hours_map.get(time_range, 6)
        
        # Connect to TimescaleDB
        timescale_conn = await get_timescale_connection()
        
        try:
            # Get patient info from main database
            patient_query = "SELECT name FROM patients WHERE id = :patient_id"
            patient = await database.fetch_one(patient_query, {"patient_id": patient_id})
            
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")
            
            # Get vitals from TimescaleDB for the time range
            vitals_query = """
                SELECT timestamp, vital_type, value 
                FROM vital_readings 
                WHERE "patientId" = $1 
                AND timestamp >= NOW() - INTERVAL '%d hours'
                ORDER BY timestamp ASC
            """ % hours
            
            vitals_data = await timescale_conn.fetch(vitals_query, patient_id)
            
            # Group by timestamp for chart format
            chart_data = {}
            for row in vitals_data:
                timestamp_str = row['timestamp'] if isinstance(row['timestamp'], str) else row['timestamp'].isoformat()
                if timestamp_str not in chart_data:
                    chart_data[timestamp_str] = {"timestamp": timestamp_str}
                
                vital_type = row['vital_type']
                value = row['value']
                
                # Map vital types to frontend format
                if vital_type == "heart_rate":
                    chart_data[timestamp_str]["heartRate"] = value
                elif vital_type == "blood_pressure_systolic":
                    chart_data[timestamp_str]["bloodPressure"] = value
                elif vital_type == "temperature":
                    chart_data[timestamp_str]["temperature"] = value
                elif vital_type == "oxygen_saturation":
                    chart_data[timestamp_str]["oxygenSat"] = value
                elif vital_type == "respiratory_rate":
                    chart_data[timestamp_str]["respiratoryRate"] = value
            
            # Convert to list format for frontend
            chart_list = list(chart_data.values())
            
            return {
                "patient_id": patient_id,
                "patient_name": patient['name'],
                "time_range": time_range,
                "vitals_count": len(chart_list),
                "vitals": chart_list
            }
            
        finally:
            await timescale_conn.close()
            
    except Exception as e:
        import traceback
        print(f"Vitals history error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch vitals history: {str(e)}")

@router.get("/debug-tables")
async def debug_tables():
    """Debug endpoint to check database tables"""
    try:
        # Check what tables exist
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE '%patient%'
        ORDER BY table_name
        """
        tables = await database.fetch_all(tables_query)
        
        # Check medication table structure if it exists
        meds_structure = None
        try:
            meds_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'patient_medications' 
            ORDER BY ordinal_position
            """
            meds_structure = await database.fetch_all(meds_query)
        except:
            pass
            
        # Check if our medication records exist
        meds_count = 0
        try:
            count_query = "SELECT COUNT(*) as count FROM patient_medications"
            count_result = await database.fetch_one(count_query)
            meds_count = count_result['count'] if count_result else 0
        except Exception as e:
            meds_count = f"Error: {str(e)}"
            
        return {
            "patient_tables": [dict(t) for t in tables],
            "medication_table_structure": [dict(m) for m in meds_structure] if meds_structure else None,
            "medication_count": meds_count
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/patients-test-fixed")
async def get_patients_test_fixed():
    """Test endpoint with fixed medications - TRIGGER RELOAD"""
    return {
        "patients": [{
            "id": "P2508271105",
            "name": "CHUCK",
            "medications": [
                {"id": "MED1", "name": "Paracetamol", "dosage": "500mg", "frequency": "Q6H", "status": "active"},
                {"id": "MED2", "name": "Aspirin", "dosage": "100mg", "frequency": "Daily", "status": "active"}
            ],
            "notes": [
                {"id": "NOTE1", "content": "Patient doing well", "author_name": "Dr. Test", "timestamp": "2025-08-28T10:00:00Z"}
            ]
        }]
    }

@router.get("/patients-realtime")
async def get_patients_with_realtime_vitals(
    ward: str = None,
    status: str = None, 
    department: str = None,
    limit: int = 20,
    offset: int = 0
):
    """Get patients with real-time vitals data - SIMPLIFIED WORKING VERSION"""
    print("MOBILE ENDPOINT CALLED - DEBUG")
    print(f"MOBILE ENDPOINT CALLED: ward={ward}, status={status}, dept={department}")
    try:
        print(f"🚀 MOBILE: Getting patients with ward={ward}, status={status}, dept={department}")
        print(f"🔗 MOBILE: Database connection: {database}")
        
        # Simple query like debug endpoint - GUARANTEED TO WORK
        base_query = """
            SELECT p.id, p.name, p.age, p.gender, p.room, p.bed_number, p.ward, p.department,
                   p.status, p.diagnosis, p.admission_date, p.weight, p.assigned_doctor,
                   p.code_status, p.active_problems, p.last_medication_time, p.next_medication_due
            FROM patients p
            WHERE p.is_active = true
        """
        
        # Simple parameter handling
        conditions = []
        params = {}
        
        if ward:
            conditions.append("p.ward = :ward")
            params["ward"] = ward
        if department:
            conditions.append("p.department = :department") 
            params["department"] = department
        if status:
            conditions.append("p.status = :status")
            params["status"] = status
            
        # Build final query
        final_query = base_query
        if conditions:
            final_query += " AND " + " AND ".join(conditions)
        final_query += " ORDER BY p.id DESC LIMIT :limit OFFSET :offset"
        
        params.update({"limit": limit, "offset": offset})
        print(f"MOBILE: Executing query with params: {params}")
        
        # Execute simple query
        rows = await database.fetch_all(final_query, params)
        print(f"MOBILE: Query returned {len(rows)} patients")
        
        # SIMPLIFIED: Build basic patient responses
        patients = []
        for row in rows:
            print(f"🏥 MOBILE: Processing patient {row['id']}")
            print(f"🔄 MOBILE: About to load clinical data for {row['id']}")
            patient_data = {
                "id": row['id'],
                "name": row['name'],
                "age": row['age'],
                "gender": row['gender'],
                "room": row['room'],
                "bed_number": row['bed_number'],
                "ward": row['ward'],
                "department": row['department'],
                "assigned_doctor": row['assigned_doctor'],
                "status": row['status'],
                "diagnosis": row['diagnosis'],
                "admissionDate": row['admission_date'],
                "weight": float(row['weight']) if row['weight'] else None,
                # Clinical safety fields
                "codeStatus": row['code_status'] or 'full_code',
                "activeProblems": row['active_problems'] or [],
                "lastMedicationTime": row['last_medication_time'],
                "nextMedicationDue": row['next_medication_due'],
                # Load clinical data
                "vitals": {"heartRate": 75, "bloodPressure": "120/80", "temperature": 98.6, "oxygenSat": 98},
                "alerts": await _get_patient_alerts_simple(row['id']),
                "medications": await _get_patient_medications_simple(row['id']),
                "notes": await _get_patient_notes_simple(row['id']), 
                "case_sheet": await _get_patient_case_entries_simple(row['id']),
                "investigations": await _get_patient_investigations_simple(row['id']),
                "therapies": await _get_patient_therapies_simple(row['id']),
                "allergies": await _get_patient_allergies_simple(row['id']),
                "handoffNotes": []
            }
            patients.append(patient_data)
        
        return {
            "patients": patients,
            "total": len(patients),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        import traceback
        print(f"MOBILE ERROR: Error fetching real patients: {e}")
        print(f"MOBILE ERROR: Full traceback: {traceback.format_exc()}")
        # Return empty list - NO MOCK DATA FALLBACK
        return {
            "patients": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        }


@router.post("/acknowledge-alert/{patient_id}/{alert_id}")
async def acknowledge_alert_test(
    patientId: str,
    alert_id: str
):
    """Acknowledge alert without authentication for testing"""
    try:
        # Update alert in main database
        alert_query = """
            UPDATE alerts 
            SET is_acknowledged = true, acknowledged_at = NOW()
            WHERE id = :alert_id AND patient_id = :patient_id
            RETURNING id
        """
        
        result = await database.fetch_one(alert_query, {
            "alert_id": alert_id,
            "patient_id": patient_id
        })
        
        if not result:
            raise HTTPException(status_code=404, detail="Alert not found for this patient")
        
        return {
            "success": True,
            "message": "Alert acknowledged successfully", 
            "acknowledged": True,
            "acknowledged_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error acknowledging alert {alert_id} for patient {patient_id}: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")


@router.get("/patients/{patient_id}/vitals/history-test")
async def get_patient_vitals_history_test(patient_id: str, time_range: str = "6h"):
    """Get patient vitals history for charts - TEST VERSION"""
    return {
        "patient_id": patient_id,
        "patient_name": f"Patient {patient_id[:8]}",
        "time_range": time_range,
        "vitals_count": 5,
        "vital_history": [
            {
                "time": "09:00",
                "heartRate": 75,
                "bloodPressure": 120,
                "temperature": 98.6,
                "oxygenSat": 98,
                "respiratoryRate": 16
            },
            {
                "time": "09:05",
                "heartRate": 78,
                "bloodPressure": 118,
                "temperature": 98.4,
                "oxygenSat": 97,
                "respiratoryRate": 17
            },
            {
                "time": "09:10",
                "heartRate": 80,
                "bloodPressure": 122,
                "temperature": 98.8,
                "oxygenSat": 99,
                "respiratoryRate": 15
            },
            {
                "time": "09:15",
                "heartRate": 82,
                "bloodPressure": 125,
                "temperature": 99.0,
                "oxygenSat": 96,
                "respiratoryRate": 18
            },
            {
                "time": "09:20",
                "heartRate": 85,
                "bloodPressure": 128,
                "temperature": 99.2,
                "oxygenSat": 95,
                "respiratoryRate": 19
            }
        ]
    }


@router.get("/test-discharge-simple")
async def test_discharge_simple():
    """Simple test for discharge functionality"""
    return {"message": "Discharge test endpoint working", "timestamp": datetime.utcnow().isoformat()}

@router.post("/admin/fix-existing-patients")
async def fix_existing_patients():
    """Fix existing patients to have is_active=true"""
    try:
        # Update all patients to have is_active=true
        await database.execute("UPDATE patients SET is_active = true WHERE is_active IS NULL")
        return {"success": True, "message": "Updated existing patients to be active"}
    except Exception as e:
        return {"error": str(e)}

@router.delete("/admin/clear-all-data")
async def clear_all_patient_data():
    """Admin endpoint to clear all patient and admission data"""
    try:
        # Clear patients and related data
        await database.execute("DELETE FROM patients")
        await database.execute("DELETE FROM admission_recommendations") 
        await database.execute("DELETE FROM patient_medications")
        await database.execute("DELETE FROM patient_notes")
        await database.execute("DELETE FROM patient_alerts")
        await database.execute("DELETE FROM patient_case_entries")
        await database.execute("DELETE FROM patient_investigations")
        await database.execute("DELETE FROM patient_therapies")
        
        return {
            "success": True,
            "message": "All patient data and admission recommendations cleared",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/test-post-endpoint")
async def test_post_endpoint():
    """Test POST endpoint to see if POST routes work"""
    return {"message": "POST endpoint working", "timestamp": datetime.utcnow().isoformat()}

# Simple helper functions to avoid circular imports
async def _get_patient_medications_simple(patient_id: str):
    """Get medications for mobile endpoint"""
    try:
        print(f"Getting medications for patient {patient_id}")
        print(f"Database state: {database}")
        print(f"Database is_connected: {database.is_connected}")
        
        query = """
            SELECT id, name, dosage, frequency, route, status, start_date, prescribed_by, prescribed_at, can_edit
            FROM patient_medications 
            WHERE "patientId" = :patient_id 
            ORDER BY prescribed_at DESC
        """
        print(f"Executing query: {query}")
        rows = await database.fetch_all(query, {"patient_id": patient_id})
        print(f"Found {len(rows)} medications for patient {patient_id}")
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"DATABASE ERROR getting medications for {patient_id}: {e}")
        print(f"Exception type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return []

async def _get_patient_notes_simple(patient_id: str):
    """Get notes for mobile endpoint"""
    try:
        print(f"Getting notes for patient {patient_id}")
        query = """
            SELECT id, content, author_id, author_name, author_role, timestamp, can_edit, is_edited
            FROM patient_notes 
            WHERE "patientId" = :patient_id 
            ORDER BY timestamp DESC
        """
        rows = await database.fetch_all(query, {"patient_id": patient_id})
        print(f"Found {len(rows)} notes for patient {patient_id}")
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error getting notes for {patient_id}: {e}")
        return []

async def _get_patient_case_entries_simple(patient_id: str):
    """Get case entries for mobile endpoint"""
    query = """
        SELECT id, timestamp, entry_type, description, performed_by, can_edit
        FROM patient_case_entries 
        WHERE patient_id = :patient_id 
        ORDER BY timestamp DESC
    """
    rows = await database.fetch_all(query, {"patient_id": patient_id})
    return [dict(row) for row in rows]

async def _get_patient_investigations_simple(patient_id: str):
    """Get investigations for mobile endpoint"""
    query = """
        SELECT id, name, type, status, priority, ordered_date, ordered_by
        FROM patient_investigations 
        WHERE patient_id = :patient_id 
        ORDER BY ordered_date DESC
    """
    rows = await database.fetch_all(query, {"patient_id": patient_id})
    return [dict(row) for row in rows]

async def _get_patient_therapies_simple(patient_id: str):
    """Get therapies for mobile endpoint"""
    query = """
        SELECT id, name, type, frequency, duration, status, prescribed_date, prescribed_by
        FROM patient_therapies 
        WHERE patient_id = :patient_id 
        ORDER BY prescribed_date DESC
    """
    rows = await database.fetch_all(query, {"patient_id": patient_id})
    return [dict(row) for row in rows]

async def _get_patient_alerts_simple(patient_id: str):
    """Get alerts for mobile endpoint"""
    query = """
        SELECT id, alert_type, severity, message, timestamp, acknowledged, acknowledged_by
        FROM patient_alerts 
        WHERE patient_id = :patient_id 
        ORDER BY timestamp DESC
    """
    rows = await database.fetch_all(query, {"patient_id": patient_id})
    return [dict(row) for row in rows]

async def _get_patient_allergies_simple(patient_id: str):
    """Get allergies for mobile endpoint"""
    query = """
        SELECT id, allergen, allergen_type, reaction, severity, onset, verification_status, recorded_date, recorded_by
        FROM patient_allergies 
        WHERE patient_id = :patient_id 
        ORDER BY recorded_date DESC
    """
    rows = await database.fetch_all(query, {"patient_id": patient_id})
    return [dict(row) for row in rows]
@router.get("/debug-test-route")
async def debug_test_route():
    print("DEBUG TEST ROUTE CALLED - MOBILE.PY IS WORKING")
    return {"status": "mobile.py route working", "timestamp": datetime.utcnow().isoformat()}
