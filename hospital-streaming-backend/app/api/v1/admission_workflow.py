from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import uuid

from app.db.database import database

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models for admission workflow
from pydantic import BaseModel

class AdmissionRecommendationCreate(BaseModel):
    patient_name: str
    age: int
    gender: str
    diagnosis: str
    priority: str = "routine"  # urgent, routine, elective
    recommended_ward: Optional[str] = None
    recommended_department: str
    estimated_length_of_stay: Optional[int] = None
    special_requirements: Optional[str] = None
    insurance_type: Optional[str] = None
    emergency_contact: Optional[str] = None
    allergies: Optional[str] = None
    weight: Optional[float] = None
    created_by: Optional[str] = None  # Doctor's staff ID

class AdmissionProcessing(BaseModel):
    recommendation_id: str
    assigned_ward: str
    assigned_room: str
    assigned_bed: str
    assigned_device: Optional[str] = None
    processing_notes: Optional[str] = None

class BedAvailability(BaseModel):
    ward_id: str
    ward_name: str
    room_id: str
    room_number: str
    bed_id: str
    bed_number: str
    bed_type: str
    equipment: Dict[str, Any]

# Doctor endpoints - Create admission recommendations
@router.post("/recommendations")
async def create_admission_recommendation(
    recommendation: AdmissionRecommendationCreate,
    current_user_id: str = "DOC001"  # TODO: Get from auth
):
    """Doctor creates admission recommendation"""
    try:
        logger.info(f"Creating recommendation with created_by: {recommendation.created_by}")
        recommendation_id = f"ADM_REC_{uuid.uuid4().hex[:8].upper()}"
        
        query = """
            INSERT INTO admission_recommendations 
            (id, patient_name, age, gender, diagnosis, priority, recommended_ward, 
             recommended_department, estimated_length_of_stay, special_requirements,
             insurance_type, emergency_contact, allergies, weight, created_by, status)
            VALUES (:id, :patient_name, :age, :gender, :diagnosis, :priority, 
                    :recommended_ward, :recommended_department, :estimated_length_of_stay,
                    :special_requirements, :insurance_type, :emergency_contact, 
                    :allergies, :weight, :created_by, 'pending')
            RETURNING id
        """
        
        result = await database.fetch_one(query, {
            "id": recommendation_id,
            "patient_name": recommendation.patient_name,
            "age": recommendation.age,
            "gender": recommendation.gender,
            "diagnosis": recommendation.diagnosis,
            "priority": recommendation.priority,
            "recommended_ward": recommendation.recommended_ward,
            "recommended_department": recommendation.recommended_department,
            "estimated_length_of_stay": recommendation.estimated_length_of_stay,
            "special_requirements": recommendation.special_requirements,
            "insurance_type": recommendation.insurance_type,
            "emergency_contact": recommendation.emergency_contact,
            "allergies": recommendation.allergies,
            "weight": recommendation.weight,
            "created_by": recommendation.created_by or current_user_id
        })
        
        return {
            "success": True,
            "recommendation_id": recommendation_id,
            "message": "Admission recommendation created successfully",
            "status": "pending_nurse_processing"
        }
        
    except Exception as e:
        logger.error(f"Error creating admission recommendation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create admission recommendation")

@router.get("/recommendations")
async def get_admission_recommendations(
    status: str = "pending",
    department: Optional[str] = None
):
    """Get admission recommendations (for nurses to process)"""
    try:
        where_conditions = ["status = :status"]
        params = {"status": status}
        
        if department:
            where_conditions.append("recommended_department = :department")
            params["department"] = department
        
        query = f"""
            SELECT ar.*, s.name as doctor_name, s.role as doctor_role
            FROM admission_recommendations ar
            LEFT JOIN staff s ON ar.created_by = s.staff_id
            WHERE {' AND '.join(where_conditions)}
            ORDER BY 
                CASE ar.priority 
                    WHEN 'urgent' THEN 1 
                    WHEN 'routine' THEN 2 
                    WHEN 'elective' THEN 3 
                END,
                ar.created_at ASC
        """
        
        recommendations = await database.fetch_all(query, params)
        
        return {
            "recommendations": [dict(rec) for rec in recommendations],
            "total_count": len(recommendations)
        }
        
    except Exception as e:
        logger.error(f"Error fetching admission recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recommendations")

# Nurse endpoints - Process admissions
@router.get("/available-beds")
async def get_available_beds(ward_type: Optional[str] = None):
    """Get available beds for admission"""
    try:
        where_conditions = ["b.status = 'available'", "b.is_active = true"]
        params = {}
        
        if ward_type:
            where_conditions.append("w.ward_type = :ward_type")
            params["ward_type"] = ward_type
        
        query = f"""
            SELECT 
                w.id as ward_id, w.name as ward_name, w.ward_type,
                r.id as room_id, r.room_number, r.room_type,
                b.id as bed_id, b.bed_number, b.bed_type, b.equipment
            FROM hospital_beds b
            JOIN hospital_rooms r ON b.room_id = r.id
            JOIN hospital_wards w ON r.ward_id = w.id
            WHERE {' AND '.join(where_conditions)}
            ORDER BY w.name, r.room_number, b.bed_number
        """
        
        beds = await database.fetch_all(query, params)
        
        return {
            "available_beds": [dict(bed) for bed in beds],
            "total_available": len(beds)
        }
        
    except Exception as e:
        logger.error(f"Error fetching available beds: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch available beds")

@router.get("/available-devices")
async def get_available_devices(device_type: str = "watch"):
    """Get available devices for assignment"""
    try:
        query = """
            SELECT id, device_id, device_name, device_type, model, battery_level, location
            FROM device_inventory
            WHERE status = 'available' AND device_type = :device_type AND is_active = true
            ORDER BY battery_level DESC, device_name
        """
        
        devices = await database.fetch_all(query, {"device_type": device_type})
        
        return {
            "available_devices": [dict(device) for device in devices],
            "total_available": len(devices)
        }
        
    except Exception as e:
        logger.error(f"Error fetching available devices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch available devices")

@router.post("/process-admission")
async def process_admission(
    processing: AdmissionProcessing,
    current_nurse_id: str = "NURSE001"  # TODO: Get from auth
):
    """Nurse processes admission recommendation and admits patient"""
    try:
        # Start transaction
        async with database.transaction():
            # Get recommendation details
            rec_query = """
                SELECT * FROM admission_recommendations 
                WHERE id = :recommendation_id AND status = 'pending'
            """
            recommendation = await database.fetch_one(rec_query, {
                "recommendation_id": processing.recommendation_id
            })
            
            if not recommendation:
                raise HTTPException(status_code=404, detail="Recommendation not found or already processed")
            
            # Get doctor name from the recommendation creator
            doctor_name = "Dr. Unknown"  # Default fallback
            logger.info(f"Looking up doctor for created_by: {recommendation['created_by']}")
            if recommendation["created_by"]:
                doctor_query = """SELECT name FROM staff WHERE staff_id = :staff_id"""
                doctor = await database.fetch_one(doctor_query, {"staff_id": recommendation["created_by"]})
                logger.info(f"Doctor query result: {doctor}")
                if doctor:
                    doctor_name = doctor["name"]
                    logger.info(f"Doctor name resolved to: {doctor_name}")
            else:
                logger.info("No created_by field in recommendation")
            
            # Generate patient ID
            patient_id = f"P{datetime.now().strftime('%y%m%d%H%M')}"
            
            # Create patient record
            patient_query = """
                INSERT INTO patients 
                (id, name, age, gender, ward, room, bed_number, department, 
                 assigned_doctor, diagnosis, admission_date, weight, status, is_active)
                VALUES (:id, :name, :age, :gender, :ward, :room, :bed_number, 
                        :department, :assigned_doctor, :diagnosis, :admission_date, 
                        :weight, 'stable', true)
                RETURNING id
            """
            
            # Get bed details for room/ward info
            bed_query = """
                SELECT b.bed_number, r.room_number, w.name as ward_name
                FROM hospital_beds b
                JOIN hospital_rooms r ON b.room_id = r.id  
                JOIN hospital_wards w ON r.ward_id = w.id
                WHERE b.id = :bed_id
            """
            bed_info = await database.fetch_one(bed_query, {"bed_id": processing.assigned_bed})
            
            await database.execute(patient_query, {
                "id": patient_id,
                "name": recommendation["patient_name"],
                "age": recommendation["age"],
                "gender": recommendation["gender"],
                "ward": bed_info["ward_name"],
                "room": bed_info["room_number"],
                "bed_number": bed_info["bed_number"],
                "department": recommendation["recommended_department"],
                "assigned_doctor": doctor_name,  # From recommendation creator
                "diagnosis": recommendation["diagnosis"],
                "admission_date": datetime.now().date().isoformat(),
                "weight": recommendation["weight"]
            })
            
            # Update bed status
            await database.execute("""
                UPDATE hospital_beds 
                SET status = 'occupied', patient_id = :patient_id, assigned_at = NOW()
                WHERE id = :bed_id
            """, {"patient_id": patient_id, "bed_id": processing.assigned_bed})
            
            # Assign device if provided
            if processing.assigned_device:
                await database.execute("""
                    UPDATE device_inventory
                    SET status = 'assigned', assigned_to = :patient_id, 
                        assigned_at = NOW(), assigned_by = :nurse_id
                    WHERE id = :device_id
                """, {
                    "patient_id": patient_id,
                    "device_id": processing.assigned_device,
                    "nurse_id": current_nurse_id
                })
            
            # Update recommendation status
            await database.execute("""
                UPDATE admission_recommendations
                SET status = 'admitted', processed_by = :nurse_id, processed_at = NOW(),
                    notes = :notes
                WHERE id = :recommendation_id
            """, {
                "recommendation_id": processing.recommendation_id,
                "nurse_id": current_nurse_id,
                "notes": processing.processing_notes
            })
            
            # Update ward occupancy
            await database.execute("""
                UPDATE hospital_wards 
                SET occupied_beds = occupied_beds + 1,
                    capacity_percentage = (occupied_beds + 1) * 100.0 / total_beds
                WHERE id = :ward_id
            """, {"ward_id": processing.assigned_ward})
        
        return {
            "success": True,
            "patient_id": patient_id,
            "message": "Patient successfully admitted",
            "assigned_bed": bed_info["bed_number"],
            "assigned_ward": bed_info["ward_name"],
            "assigned_device": processing.assigned_device
        }
        
    except Exception as e:
        logger.error(f"Error processing admission: {e}")
        raise HTTPException(status_code=500, detail="Failed to process admission")

# Analytics endpoints
@router.get("/dashboard-stats")
async def get_admission_dashboard_stats():
    """Get admission workflow statistics"""
    try:
        stats = {}
        
        # Pending recommendations
        pending_count = await database.fetch_val("""
            SELECT COUNT(*) FROM admission_recommendations WHERE status = 'pending'
        """)
        
        # Urgent recommendations
        urgent_count = await database.fetch_val("""
            SELECT COUNT(*) FROM admission_recommendations 
            WHERE status = 'pending' AND priority = 'urgent'
        """)
        
        # Available beds by type
        bed_availability = await database.fetch_all("""
            SELECT w.ward_type, COUNT(*) as available_beds
            FROM hospital_beds b
            JOIN hospital_rooms r ON b.room_id = r.id
            JOIN hospital_wards w ON r.ward_id = w.id
            WHERE b.status = 'available' AND b.is_active = true
            GROUP BY w.ward_type
        """)
        
        # Available devices
        device_availability = await database.fetch_all("""
            SELECT device_type, COUNT(*) as available_count
            FROM device_inventory
            WHERE status = 'available' AND is_active = true
            GROUP BY device_type
        """)
        
        return {
            "pending_recommendations": pending_count,
            "urgent_recommendations": urgent_count,
            "bed_availability": [dict(row) for row in bed_availability],
            "device_availability": [dict(row) for row in device_availability]
        }
        
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard statistics")

# NFC Device Assignment Endpoints

class AssignmentSession(BaseModel):
    recommendation_id: str
    assigned_bed: str

@router.post("/start-assignment-session")
async def start_assignment_session(
    session_data: AssignmentSession,
    current_nurse_id: str = "NURSE001"  # TODO: Get from auth
):
    """Start an active assignment session for NFC device assignment"""
    try:
        # Get recommendation details
        rec_query = """
            SELECT patient_name FROM admission_recommendations 
            WHERE id = :recommendation_id AND status = 'pending'
        """
        recommendation = await database.fetch_one(rec_query, {
            "recommendation_id": session_data.recommendation_id
        })
        
        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        
        session_id = f"ASSIGN_SESSION_{uuid.uuid4().hex[:8].upper()}"
        
        # Clear any existing sessions for this nurse
        await database.execute("""
            UPDATE active_assignment_sessions 
            SET is_active = false 
            WHERE nurse_id = :nurse_id AND is_active = true
        """, {"nurse_id": current_nurse_id})
        
        # Create new session
        await database.execute("""
            INSERT INTO active_assignment_sessions 
            (id, nurse_id, patient_name, recommendation_id, assigned_bed, expires_at)
            VALUES (:id, :nurse_id, :patient_name, :recommendation_id, :assigned_bed, 
                    NOW() + INTERVAL '10 minutes')
        """, {
            "id": session_id,
            "nurse_id": current_nurse_id,
            "patient_name": recommendation["patient_name"],
            "recommendation_id": session_data.recommendation_id,
            "assigned_bed": session_data.assigned_bed
        })
        
        return {
            "success": True,
            "session_id": session_id,
            "message": f"Assignment session started for {recommendation['patient_name']}. Tap NFC-enabled device to assign.",
            "expires_in_minutes": 10
        }
        
    except Exception as e:
        logger.error(f"Error starting assignment session: {e}")
        raise HTTPException(status_code=500, detail="Failed to start assignment session")

@router.post("/nfc-device-assign/{nfc_id}")
async def assign_device_by_nfc(
    nfc_id: str,
    current_nurse_id: str = "NURSE001"  # TODO: Get from auth
):
    """Assign device to patient via NFC tap"""
    try:
        # Get active assignment session
        session_query = """
            SELECT * FROM active_assignment_sessions 
            WHERE nurse_id = :nurse_id AND is_active = true AND expires_at > NOW()
            ORDER BY session_started DESC LIMIT 1
        """
        session = await database.fetch_one(session_query, {"nurse_id": current_nurse_id})
        
        if not session:
            raise HTTPException(status_code=400, detail="No active assignment session. Please start admission process first.")
        
        # Get device by NFC ID
        device_query = """
            SELECT * FROM device_inventory 
            WHERE nfc_id = :nfc_id AND status = 'available' AND is_active = true
        """
        device = await database.fetch_one(device_query, {"nfc_id": nfc_id})
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found or not available for assignment")
        
        # Start transaction to complete admission with NFC device
        async with database.transaction():
            # Get recommendation details
            rec_query = """
                SELECT * FROM admission_recommendations 
                WHERE id = :recommendation_id AND status = 'pending'
            """
            recommendation = await database.fetch_one(rec_query, {
                "recommendation_id": session["recommendation_id"]
            })
            
            if not recommendation:
                raise HTTPException(status_code=404, detail="Recommendation not found or already processed")
            
            # Get doctor name from the recommendation creator
            doctor_name = "Dr. Unknown"  # Default fallback
            logger.info(f"Looking up doctor for created_by: {recommendation['created_by']}")
            if recommendation["created_by"]:
                doctor_query = """SELECT name FROM staff WHERE staff_id = :staff_id"""
                doctor = await database.fetch_one(doctor_query, {"staff_id": recommendation["created_by"]})
                logger.info(f"Doctor query result: {doctor}")
                if doctor:
                    doctor_name = doctor["name"]
                    logger.info(f"Doctor name resolved to: {doctor_name}")
            else:
                logger.info("No created_by field in recommendation")
            
            # Generate patient ID
            patient_id = f"P{datetime.now().strftime('%y%m%d%H%M')}"
            
            # Create patient record
            patient_query = """
                INSERT INTO patients 
                (id, name, age, gender, ward, room, bed_number, department, 
                 assigned_doctor, diagnosis, admission_date, weight, status, is_active)
                VALUES (:id, :name, :age, :gender, :ward, :room, :bed_number, 
                        :department, :assigned_doctor, :diagnosis, :admission_date, 
                        :weight, 'stable', true)
                RETURNING id
            """
            
            # Get bed details
            bed_query = """
                SELECT b.bed_number, r.room_number, w.name as ward_name, w.id as ward_id, r.id as room_id
                FROM hospital_beds b
                JOIN hospital_rooms r ON b.room_id = r.id  
                JOIN hospital_wards w ON r.ward_id = w.id
                WHERE b.id = :bed_id
            """
            bed_info = await database.fetch_one(bed_query, {"bed_id": session["assigned_bed"]})
            
            await database.execute(patient_query, {
                "id": patient_id,
                "name": recommendation["patient_name"],
                "age": recommendation["age"],
                "gender": recommendation["gender"],
                "ward": bed_info["ward_name"],
                "room": bed_info["room_number"],
                "bed_number": bed_info["bed_number"],
                "department": recommendation["recommended_department"],
                "assigned_doctor": doctor_name,  
                "diagnosis": recommendation["diagnosis"],
                "admission_date": datetime.now().date().isoformat(),
                "weight": recommendation["weight"]
            })
            
            # Update bed status
            await database.execute("""
                UPDATE hospital_beds 
                SET status = 'occupied', patient_id = :patient_id, assigned_at = NOW()
                WHERE id = :bed_id
            """, {"patient_id": patient_id, "bed_id": session["assigned_bed"]})
            
            # Assign NFC device
            await database.execute("""
                UPDATE device_inventory
                SET status = 'assigned', assigned_to = :patient_id, 
                    assigned_at = NOW(), assigned_by = :nurse_id,
                    location = :location
                WHERE nfc_id = :nfc_id
            """, {
                "patient_id": patient_id,
                "nfc_id": nfc_id,
                "nurse_id": current_nurse_id,
                "location": f"{bed_info['ward_name']}-{bed_info['room_number']}"
            })
            
            # Update recommendation status
            await database.execute("""
                UPDATE admission_recommendations
                SET status = 'admitted', processed_by = :nurse_id, processed_at = NOW(),
                    notes = :notes
                WHERE id = :recommendation_id
            """, {
                "recommendation_id": session["recommendation_id"],
                "nurse_id": current_nurse_id,
                "notes": f"Admission completed via NFC assignment. Device {device['device_name']} assigned via NFC tap."
            })
            
            # Update ward occupancy
            await database.execute("""
                UPDATE hospital_wards 
                SET occupied_beds = occupied_beds + 1,
                    capacity_percentage = (occupied_beds + 1) * 100.0 / total_beds
                WHERE id = :ward_id
            """, {"ward_id": bed_info["ward_id"]})
            
            # Deactivate assignment session
            await database.execute("""
                UPDATE active_assignment_sessions 
                SET is_active = false 
                WHERE id = :session_id
            """, {"session_id": session["id"]})
        
        return {
            "success": True,
            "patient_id": patient_id,
            "device_assigned": device["device_name"],
            "device_id": device["device_id"],
            "nfc_id": nfc_id,
            "assigned_bed": bed_info["bed_number"],
            "assigned_ward": bed_info["ward_name"],
            "message": f"✅ NFC Assignment Complete! {device['device_name']} assigned to {recommendation['patient_name']} in bed {bed_info['bed_number']}"
        }
        
    except Exception as e:
        logger.error(f"Error assigning device by NFC: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign device via NFC")

@router.get("/active-assignment-session")
async def get_active_assignment_session(
    current_nurse_id: str = "NURSE001"  # TODO: Get from auth
):
    """Get current active assignment session for nurse"""
    try:
        session_query = """
            SELECT * FROM active_assignment_sessions 
            WHERE nurse_id = :nurse_id AND is_active = true AND expires_at > NOW()
            ORDER BY session_started DESC LIMIT 1
        """
        session = await database.fetch_one(session_query, {"nurse_id": current_nurse_id})
        
        if not session:
            return {"active_session": None}
        
        return {
            "active_session": {
                "session_id": session["id"],
                "patient_name": session["patient_name"],
                "assigned_bed": session["assigned_bed"],
                "started_at": session["session_started"],
                "expires_at": session["expires_at"],
                "status": "waiting_for_nfc_tap"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting active session: {e}")
        raise HTTPException(status_code=500, detail="Failed to get active session")