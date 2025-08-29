from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel
import asyncpg
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
    """Generate comprehensive 2-page discharge summary"""
    try:
        # Verify patient is discharged
        patient = await database.fetch_one("""
            SELECT * FROM patients 
            WHERE id = :patient_id AND discharge_status = 'discharged'
        """, {"patient_id": patient_id})
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found or not discharged")
        
        # Get vital signs summary from TimescaleDB
        try:
            timescale_conn = await asyncpg.connect("postgresql://hospital_user:hospital_pass@localhost:5434/hospital_vitals")
            vital_summary = await timescale_conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_readings,
                    AVG(CASE WHEN vital_type = 'heart_rate' THEN value END) as avg_hr,
                    MAX(CASE WHEN vital_type = 'heart_rate' THEN value END) as max_hr,
                    MIN(CASE WHEN vital_type = 'heart_rate' THEN value END) as min_hr,
                    AVG(CASE WHEN vital_type = 'temperature' THEN value END) as avg_temp,
                    MAX(CASE WHEN vital_type = 'temperature' THEN value END) as max_temp,
                    MIN(CASE WHEN vital_type = 'temperature' THEN value END) as min_temp,
                    AVG(CASE WHEN vital_type = 'spo2' THEN value END) as avg_spo2,
                    MIN(CASE WHEN vital_type = 'spo2' THEN value END) as min_spo2,
                    AVG(CASE WHEN vital_type = 'bp_systolic' THEN value END) as avg_bp_sys,
                    AVG(CASE WHEN vital_type = 'bp_diastolic' THEN value END) as avg_bp_dia
                FROM vital_readings 
                WHERE patient_id = $1
            """, patient_id)
            await timescale_conn.close()
        except Exception as e:
            vital_summary = None
            print(f"Could not fetch vitals summary: {e}")
        
        # Get medications from patient data
        current_meds = patient.get('current_vitals', {}).get('medications', [])
        
        # Calculate length of stay
        admission_date = datetime.fromisoformat(patient['admission_date'].replace('Z', '+00:00')) if patient['admission_date'] else datetime.utcnow()
        discharge_date = patient.get('final_discharge_date') or datetime.utcnow()
        if isinstance(discharge_date, str):
            discharge_date = datetime.fromisoformat(discharge_date.replace('Z', '+00:00'))
        length_of_stay = (discharge_date - admission_date).days
        
        # Create comprehensive discharge summary
        summary = {
            "patient_id": patient_id,
            "admission_date": admission_date.date() if hasattr(admission_date, 'date') else admission_date,
            "discharge_date": discharge_date.date() if hasattr(discharge_date, 'date') else discharge_date,
            "length_of_stay": max(length_of_stay, 1),
            "primary_diagnosis": summary_data.primary_diagnosis,
            "secondary_diagnoses": summary_data.secondary_diagnoses,
            "procedures_performed": summary_data.procedures_performed,
            "medications_on_admission": current_meds,
            "medications_on_discharge": current_meds,
            "medications_to_continue": summary_data.medications_to_continue,
            "vital_signs_summary": dict(vital_summary) if vital_summary else {},
            "lab_results_summary": {},  # Could be expanded to include actual lab results
            "therapy_sessions": {},  # Could be expanded to include therapy records
            "follow_up_instructions": summary_data.follow_up_instructions,
            "next_appointment_date": summary_data.next_appointment_date,
            "next_appointment_with": summary_data.next_appointment_with,
            "discharge_condition": summary_data.discharge_condition,
            "discharge_disposition": summary_data.discharge_disposition,
            "generated_by": summary_data.generated_by,
            "generated_at": datetime.utcnow()
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
            "admission_date": summary['admission_date'].isoformat() if hasattr(summary['admission_date'], 'isoformat') else str(summary['admission_date']),
            "discharge_date": summary['discharge_date'].isoformat() if hasattr(summary['discharge_date'], 'isoformat') else str(summary['discharge_date']), 
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
            "next_appointment_date": summary['next_appointment_date'] if summary['next_appointment_date'] else None,
            "next_appointment_with": summary['next_appointment_with'],
            "discharge_condition": summary['discharge_condition'],
            "discharge_disposition": summary['discharge_disposition'],
            "generated_by": summary['generated_by'],
            "generated_at": summary['generated_at'].isoformat() if hasattr(summary['generated_at'], 'isoformat') else str(summary['generated_at'])
        })
        
        # Mark summary as generated
        await database.execute("""
            UPDATE patients SET discharge_summary_generated = true WHERE id = :patient_id
        """, {"patient_id": patient_id})
        
        return {
            "success": True,
            "message": "Discharge summary generated successfully",
            "summary": summary
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate discharge summary: {str(e)}")

@router.get("/print/{patient_id}")
async def get_printable_discharge_summary(patient_id: str):
    """Get formatted 2-page discharge summary for printing"""
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
        
        # Format for 2-page printable summary
        formatted_summary = {
            "header": {
                "hospital_name": "City General Hospital",
                "document_title": "DISCHARGE SUMMARY",
                "generated_date": summary['generated_at'].strftime("%Y-%m-%d %H:%M"),
                "page_count": "2 pages"
            },
            "patient_info": {
                "name": patient['name'],
                "patient_id": patient['id'],
                "age": patient['age'],
                "gender": patient['gender'],
                "admission_date": summary['admission_date'].strftime("%Y-%m-%d"),
                "discharge_date": summary['discharge_date'].strftime("%Y-%m-%d"),
                "length_of_stay": f"{summary['length_of_stay']} days",
                "ward": patient['ward'],
                "room": patient['room'],
                "bed": patient['bed_number']
            },
            "clinical_summary": {
                "primary_diagnosis": summary['primary_diagnosis'],
                "secondary_diagnoses": summary['secondary_diagnoses'],
                "procedures_performed": summary['procedures_performed'],
                "discharge_condition": summary['discharge_condition'],
                "discharge_disposition": summary['discharge_disposition']
            },
            "vital_signs_summary": json.loads(summary['vital_signs_summary']) if summary['vital_signs_summary'] else {},
            "medications": {
                "on_admission": json.loads(summary['medications_on_admission']) if summary['medications_on_admission'] else [],
                "on_discharge": json.loads(summary['medications_on_discharge']) if summary['medications_on_discharge'] else [],
                "to_continue": json.loads(summary['medications_to_continue']) if summary['medications_to_continue'] else {}
            },
            "instructions": {
                "follow_up": summary['follow_up_instructions'],
                "next_appointment": {
                    "date": summary['next_appointment_date'],
                    "with": summary['next_appointment_with']
                }
            },
            "signatures": {
                "generated_by": summary['generated_by'],
                "generated_at": summary['generated_at'].strftime("%Y-%m-%d %H:%M"),
                "approved_by": summary['approved_by'] if summary.get('approved_by') else "Pending",
                "approved_at": summary['approved_at'].strftime("%Y-%m-%d %H:%M") if summary.get('approved_at') else "Pending"
            }
        }
        
        return {
            "success": True,
            "patient_id": patient_id,
            "printable_summary": formatted_summary,
            "print_ready": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get printable summary: {str(e)}")

@router.get("/list")
async def list_discharge_summaries():
    """List all discharge summaries"""
    try:
        summaries = await database.fetch_all("""
            SELECT ds.patient_id, p.name as patient_name, ds.discharge_date, 
                   ds.primary_diagnosis, ds.generated_by, ds.generated_at
            FROM discharge_summaries ds
            JOIN patients p ON ds.patient_id = p.id
            ORDER BY ds.generated_at DESC
        """)
        
        return {
            "summaries": [dict(summary) for summary in summaries],
            "total_count": len(summaries)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list summaries: {str(e)}")