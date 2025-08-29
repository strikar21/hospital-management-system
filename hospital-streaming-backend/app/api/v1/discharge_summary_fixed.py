from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel
import json

from app.db.database import database

router = APIRouter(prefix="/discharge-summary")

class DischargeSummaryRequest(BaseModel):
    patient_id: str
    primary_diagnosis: str
    secondary_diagnoses: List[str] = []
    procedures_performed: List[str] = []
    medications_to_continue: Dict[str, Any] = {}
    follow_up_instructions: str = ""
    next_appointment_date: Optional[str] = None
    next_appointment_with: Optional[str] = None
    discharge_condition: str = "stable"
    discharge_disposition: str = "home"
    generated_by: str

@router.post("/generate/{patient_id}")
async def generate_discharge_summary(patient_id: str, summary_data: DischargeSummaryRequest):
    """Generate comprehensive discharge summary for patient"""
    try:
        # Verify patient is discharged
        patient = await database.fetch_one("""
            SELECT * FROM patients 
            WHERE id = :patient_id AND discharge_status = 'discharged'
        """, {"patient_id": patient_id})
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found or not discharged")
        
        # Calculate length of stay
        try:
            if patient.get('admission_date'):
                admission_date = datetime.fromisoformat(patient['admission_date'].replace('Z', '+00:00'))
            else:
                admission_date = datetime.utcnow()
                
            discharge_date = datetime.utcnow()
            length_of_stay = max((discharge_date - admission_date).days, 1)
        except Exception as e:
            print(f"Date calculation error: {e}")
            length_of_stay = 1
        
        # Create comprehensive discharge summary
        summary = {
            "patient_id": patient_id,
            "admission_date": admission_date.date().isoformat(),
            "discharge_date": discharge_date.date().isoformat(),
            "length_of_stay": length_of_stay,
            "primary_diagnosis": summary_data.primary_diagnosis,
            "secondary_diagnoses": summary_data.secondary_diagnoses,
            "procedures_performed": summary_data.procedures_performed,
            "medications_on_admission": [],
            "medications_on_discharge": [],
            "medications_to_continue": summary_data.medications_to_continue,
            "vital_signs_summary": {},
            "lab_results_summary": {},
            "therapy_sessions": {},
            "follow_up_instructions": summary_data.follow_up_instructions,
            "next_appointment_date": summary_data.next_appointment_date,
            "next_appointment_with": summary_data.next_appointment_with,
            "discharge_condition": summary_data.discharge_condition,
            "discharge_disposition": summary_data.discharge_disposition,
            "generated_by": summary_data.generated_by,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Store in database
        await database.execute("""
            INSERT INTO discharge_summaries (
                patient_id, admission_date, discharge_date, length_of_stay,
                primary_diagnosis, secondary_diagnoses, procedures_performed,
                medications_on_admission, medications_on_discharge, medications_to_continue,
                vital_signs_summary, lab_results_summary, therapy_sessions,
                follow_up_instructions, next_appointment_date, next_appointment_with,
                discharge_condition, discharge_disposition, generated_by, generated_at
            ) VALUES (
                :patient_id, :admission_date, :discharge_date, :length_of_stay,
                :primary_diagnosis, :secondary_diagnoses, :procedures_performed,
                :medications_on_admission, :medications_on_discharge, :medications_to_continue,
                :vital_signs_summary, :lab_results_summary, :therapy_sessions,
                :follow_up_instructions, :next_appointment_date, :next_appointment_with,
                :discharge_condition, :discharge_disposition, :generated_by, :generated_at
            )
        """, {
            "patient_id": patient_id,
            "admission_date": summary['admission_date'],
            "discharge_date": summary['discharge_date'], 
            "length_of_stay": summary['length_of_stay'],
            "primary_diagnosis": summary['primary_diagnosis'],
            "secondary_diagnoses": summary['secondary_diagnoses'],
            "procedures_performed": summary['procedures_performed'],
            "medications_on_admission": json.dumps(summary['medications_on_admission']),
            "medications_on_discharge": json.dumps(summary['medications_on_discharge']),
            "medications_to_continue": json.dumps(summary['medications_to_continue']),
            "vital_signs_summary": json.dumps(summary['vital_signs_summary']),
            "lab_results_summary": json.dumps(summary['lab_results_summary']),
            "therapy_sessions": json.dumps(summary['therapy_sessions']),
            "follow_up_instructions": summary['follow_up_instructions'],
            "next_appointment_date": summary['next_appointment_date'],
            "next_appointment_with": summary['next_appointment_with'],
            "discharge_condition": summary['discharge_condition'],
            "discharge_disposition": summary['discharge_disposition'],
            "generated_by": summary['generated_by'],
            "generated_at": summary['generated_at']
        })
        
        # Mark summary as generated
        await database.execute("""
            UPDATE patients SET discharge_summary_generated = true WHERE id = :patient_id
        """, {"patient_id": patient_id})
        
        return {
            "success": True,
            "message": "Discharge summary generated successfully - patient can collect it",
            "summary": summary
        }
        
    except Exception as e:
        import traceback
        print(f"Full error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate discharge summary: {str(e)}")

@router.get("/print/{patient_id}")
async def get_printable_discharge_summary(patient_id: str):
    """Get formatted discharge summary for patient printing"""
    try:
        # Get discharge summary
        summary = await database.fetch_one("""
            SELECT * FROM discharge_summaries WHERE patient_id = :patient_id
            ORDER BY generated_at DESC LIMIT 1
        """, {"patient_id": patient_id})
        
        if not summary:
            raise HTTPException(status_code=404, detail="No discharge summary found for this patient")
        
        # Get patient details
        patient = await database.fetch_one("""
            SELECT * FROM patients WHERE id = :patient_id
        """, {"patient_id": patient_id})
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Format for patient printout
        printable_summary = {
            "patient_info": {
                "name": patient.get('name', 'N/A'),
                "patient_id": patient_id,
                "admission_date": str(summary['admission_date']),
                "discharge_date": str(summary['discharge_date']),
                "length_of_stay": f"{summary['length_of_stay']} days"
            },
            "clinical_summary": {
                "primary_diagnosis": summary['primary_diagnosis'],
                "secondary_diagnoses": summary['secondary_diagnoses'],
                "procedures_performed": summary['procedures_performed'],
                "discharge_condition": summary['discharge_condition'],
                "discharge_disposition": summary['discharge_disposition']
            },
            "medications": {
                "to_continue": json.loads(summary['medications_to_continue']) if summary['medications_to_continue'] else {}
            },
            "instructions": {
                "follow_up": summary['follow_up_instructions'],
                "next_appointment": {
                    "date": summary['next_appointment_date'],
                    "with": summary['next_appointment_with']
                }
            },
            "generated_info": {
                "generated_by": summary['generated_by'],
                "generated_at": str(summary['generated_at'])
            }
        }
        
        return {
            "success": True,
            "message": "Printable discharge summary ready for patient",
            "printable_summary": printable_summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get printable summary: {str(e)}")