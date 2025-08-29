from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.db.database import database

router = APIRouter(prefix="/discharge")

class PatientDischarge(BaseModel):
    staff_id: str
    discharge_date: str
    discharge_reason: str = "medical_discharge"
    discharge_notes: Optional[str] = None

@router.post("/patients/{patient_id}")
async def discharge_patient(patient_id: str, discharge_data: PatientDischarge):
    """Discharge a patient - removes from active list, frees bed, unassigns devices"""
    
    try:
        # Start transaction to ensure data consistency
        async with database.transaction():
            # Verify patient exists and is active
            patient_query = """
                SELECT id, name, bed_number, ward, room FROM patients 
                WHERE id = :patient_id AND is_active = true
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
                    discharged_by = :staff_id,
                    status = 'discharged'
                WHERE id = :patient_id
            """
            await database.execute(discharge_query, {
                "patient_id": patient_id,
                "discharge_date": discharge_data.discharge_date,
                "discharge_reason": discharge_data.discharge_reason,
                "discharge_notes": discharge_data.discharge_notes,
                "staff_id": discharge_data.staff_id
            })
            
            # Free up the bed
            bed_update_query = """
                UPDATE hospital_beds 
                SET occupancy_status = 'available', assigned_patient = NULL
                WHERE assigned_patient = :patient_id
            """
            await database.execute(bed_update_query, {"patient_id": patient_id})
            
            # Unassign devices
            device_update_query = """
                UPDATE devices 
                SET assignment_status = 'free', assigned_to = NULL
                WHERE assigned_to = :patient_id
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discharge patient: {str(e)}")

@router.get("/test")
async def test_discharge_router():
    """Test endpoint to verify discharge router is working"""
    return {"message": "Discharge router is working", "timestamp": datetime.utcnow().isoformat()}