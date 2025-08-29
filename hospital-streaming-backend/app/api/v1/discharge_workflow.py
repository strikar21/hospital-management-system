from fastapi import APIRouter, HTTPException
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel
import json

from app.db.database import database

router = APIRouter(prefix="/discharge-workflow")

class DischargeRequest(BaseModel):
    patient_id: str
    discharge_reason: str
    discharge_notes: Optional[str] = None
    requested_by: str  # staff_id

class AdminApproval(BaseModel):
    patient_id: str
    approval_notes: Optional[str] = None
    approved_by: str  # staff_id

class NurseDischarge(BaseModel):
    patient_id: str
    discharged_by: str  # staff_id
    final_notes: Optional[str] = None

class DischargeSummaryData(BaseModel):
    primary_diagnosis: str
    secondary_diagnoses: List[str] = []
    procedures_performed: List[str] = []
    medications_to_continue: dict = {}
    follow_up_instructions: str = ""
    next_appointment_date: Optional[str] = None
    next_appointment_with: Optional[str] = None
    discharge_condition: str = "stable"

@router.post("/doctor-request")
async def doctor_request_discharge(request: DischargeRequest):
    """Step 1: Doctor requests discharge"""
    try:
        # Check if patient exists and is active
        patient = await database.fetch_one(
            "SELECT id, name, status FROM patients WHERE id = :patient_id AND is_active = true",
            {"patient_id": request.patient_id}
        )
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found or already discharged")
        
        # Update patient discharge status
        await database.execute("""
            UPDATE patients 
            SET discharge_status = 'requested',
                discharge_request_date = :request_date,
                discharge_requested_by = :requested_by,
                discharge_reason = :reason,
                discharge_notes = :notes
            WHERE id = :patient_id
        """, {
            "patient_id": request.patient_id,
            "request_date": datetime.utcnow(),
            "requested_by": request.requested_by,
            "reason": request.discharge_reason,
            "notes": request.discharge_notes
        })
        
        # Log approval stage
        await database.execute("""
            INSERT INTO discharge_approvals (patient_id, approval_stage, staff_id, staff_role, notes, status)
            VALUES (:patient_id, 'doctor_request', :staff_id, 'Doctor', :notes, 'approved')
        """, {
            "patient_id": request.patient_id,
            "staff_id": request.requested_by,
            "notes": request.discharge_notes
        })
        
        return {
            "success": True,
            "message": f"Discharge request submitted for {patient['name']}",
            "patient_id": request.patient_id,
            "next_step": "Waiting for admin approval",
            "status": "requested"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to request discharge: {str(e)}")

@router.post("/admin-approval")
async def admin_approve_discharge(approval: AdminApproval):
    """Step 2: Admin approves discharge"""
    try:
        # Check if patient has pending discharge request
        patient = await database.fetch_one(
            "SELECT id, name, discharge_status FROM patients WHERE id = :patient_id AND discharge_status = 'requested'",
            {"patient_id": approval.patient_id}
        )
        
        if not patient:
            raise HTTPException(status_code=404, detail="No pending discharge request found for this patient")
        
        # Update patient status to admin approved
        await database.execute("""
            UPDATE patients 
            SET discharge_status = 'admin_approved',
                admin_approval_date = :approval_date,
                admin_approved_by = :approved_by,
                admin_approval_notes = :notes
            WHERE id = :patient_id
        """, {
            "patient_id": approval.patient_id,
            "approval_date": datetime.utcnow(),
            "approved_by": approval.approved_by,
            "notes": approval.approval_notes
        })
        
        # Log approval stage
        await database.execute("""
            INSERT INTO discharge_approvals (patient_id, approval_stage, staff_id, staff_role, notes, status)
            VALUES (:patient_id, 'admin_approval', :staff_id, 'Administrator', :notes, 'approved')
        """, {
            "patient_id": approval.patient_id,
            "staff_id": approval.approved_by,
            "notes": approval.approval_notes
        })
        
        return {
            "success": True,
            "message": f"Discharge approved by admin for {patient['name']}",
            "patient_id": approval.patient_id,
            "next_step": "Ready for nurse to complete discharge",
            "status": "admin_approved"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve discharge: {str(e)}")

@router.post("/nurse-discharge")
async def nurse_complete_discharge(discharge: NurseDischarge):
    """Step 3: Nurse completes final discharge"""
    try:
        # Check if patient has admin approval
        patient = await database.fetch_one(
            "SELECT * FROM patients WHERE id = :patient_id AND discharge_status = 'admin_approved'",
            {"patient_id": discharge.patient_id}
        )
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found or not approved for discharge")
        
        # Final discharge - set patient inactive
        await database.execute("""
            UPDATE patients 
            SET discharge_status = 'discharged',
                is_active = false,
                final_discharge_date = :discharge_date,
                discharged_by = :discharged_by,
                status = 'discharged'
            WHERE id = :patient_id
        """, {
            "patient_id": discharge.patient_id,
            "discharge_date": datetime.utcnow(),
            "discharged_by": discharge.discharged_by
        })
        
        # Log final discharge
        await database.execute("""
            INSERT INTO discharge_approvals (patient_id, approval_stage, staff_id, staff_role, notes, status)
            VALUES (:patient_id, 'nurse_discharge', :staff_id, 'Nurse', :notes, 'completed')
        """, {
            "patient_id": discharge.patient_id,
            "staff_id": discharge.discharged_by,
            "notes": discharge.final_notes
        })
        
        # Free up bed and resources
        await database.execute("""
            UPDATE hospital_beds 
            SET status = 'available', patient_id = NULL
            WHERE patient_id = :patient_id
        """, {"patient_id": discharge.patient_id})
        
        return {
            "success": True,
            "message": f"Patient {patient['name']} successfully discharged by nurse",
            "patient_id": discharge.patient_id,
            "discharge_date": datetime.utcnow().isoformat(),
            "next_step": "Generate discharge summary",
            "status": "discharged"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete discharge: {str(e)}")

@router.get("/pending-requests")
async def get_pending_discharge_requests():
    """Get all pending discharge requests for admin review"""
    try:
        requests = await database.fetch_all("""
            SELECT p.id, p.name, p.ward, p.room, p.bed_number, p.discharge_reason, 
                   p.discharge_request_date, p.discharge_requested_by, p.discharge_status
            FROM patients p
            WHERE p.discharge_status IN ('requested', 'admin_approved')
            ORDER BY p.discharge_request_date ASC
        """)
        
        return {
            "pending_requests": [dict(req) for req in requests],
            "total_pending": len(requests)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pending requests: {str(e)}")

@router.get("/workflow-status/{patient_id}")
async def get_discharge_workflow_status(patient_id: str):
    """Get current discharge workflow status for a patient"""
    try:
        # Get patient discharge info
        patient = await database.fetch_one("""
            SELECT id, name, discharge_status, discharge_request_date, 
                   admin_approval_date, final_discharge_date,
                   discharge_requested_by, admin_approved_by, discharged_by
            FROM patients WHERE id = :patient_id
        """, {"patient_id": patient_id})
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Get approval history
        approvals = await database.fetch_all("""
            SELECT approval_stage, staff_id, staff_role, approval_date, notes, status
            FROM discharge_approvals 
            WHERE patient_id = :patient_id
            ORDER BY approval_date ASC
        """, {"patient_id": patient_id})
        
        return {
            "patient_info": dict(patient),
            "workflow_stage": patient['discharge_status'] or 'active',
            "approval_history": [dict(approval) for approval in approvals],
            "next_actions": {
                "active": "Doctor can request discharge",
                "requested": "Waiting for admin approval", 
                "admin_approved": "Ready for nurse discharge",
                "discharged": "Complete - can generate summary"
            }.get(patient['discharge_status'], "Unknown status")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {str(e)}")