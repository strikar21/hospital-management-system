#!/usr/bin/env python3
"""
Test the complete discharge workflow
Usage: python test_discharge_workflow.py
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8001/api/v1"

def test_discharge_workflow():
    """Test the complete 3-step discharge workflow"""
    patient_id = "P25082350"  # Use existing patient
    
    print("=== TESTING DISCHARGE WORKFLOW ===")
    print(f"Patient ID: {patient_id}")
    print()
    
    # Step 1: Doctor requests discharge
    print("STEP 1: Doctor requesting discharge...")
    doctor_request = {
        "patient_id": patient_id,
        "discharge_reason": "Patient recovered fully from pneumonia",
        "discharge_notes": "Vital signs stable, patient ambulatory, ready for home care",
        "requested_by": "DOC001"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/discharge-workflow/doctor-request", 
                               json=doctor_request)
        if response.status_code == 200:
            print("✓ Doctor request successful")
            print(f"  Message: {response.json()['message']}")
            print(f"  Next step: {response.json()['next_step']}")
        else:
            print(f"✗ Doctor request failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Doctor request error: {e}")
    
    print()
    
    # Step 2: Admin approval
    print("STEP 2: Admin approving discharge...")
    admin_approval = {
        "patient_id": patient_id,
        "approval_notes": "Insurance clearance obtained, billing completed, discharge approved",
        "approved_by": "ADM001"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/discharge-workflow/admin-approval", 
                               json=admin_approval)
        if response.status_code == 200:
            print("✓ Admin approval successful")
            print(f"  Message: {response.json()['message']}")
            print(f"  Next step: {response.json()['next_step']}")
        else:
            print(f"✗ Admin approval failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Admin approval error: {e}")
    
    print()
    
    # Step 3: Nurse discharge
    print("STEP 3: Nurse completing discharge...")
    nurse_discharge = {
        "patient_id": patient_id,
        "discharged_by": "NURSE001",
        "final_notes": "Patient education completed, medications reconciled, discharge instructions given"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/discharge-workflow/nurse-discharge", 
                               json=nurse_discharge)
        if response.status_code == 200:
            print("✓ Nurse discharge successful")
            print(f"  Message: {response.json()['message']}")
            print(f"  Next step: {response.json()['next_step']}")
        else:
            print(f"✗ Nurse discharge failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Nurse discharge error: {e}")
    
    print()
    
    # Step 4: Generate discharge summary
    print("STEP 4: Generating discharge summary...")
    summary_data = {
        "patient_id": patient_id,
        "primary_diagnosis": "Community Acquired Pneumonia",
        "secondary_diagnoses": ["Hypertension", "Type 2 Diabetes"],
        "procedures_performed": ["Chest X-ray", "Blood culture", "IV antibiotic therapy"],
        "medications_to_continue": {
            "Lisinopril": "10mg daily for hypertension",
            "Metformin": "500mg twice daily for diabetes",
            "Amoxicillin": "500mg three times daily for 7 days (complete course)"
        },
        "follow_up_instructions": "1. Complete antibiotic course\\n2. Monitor blood pressure daily\\n3. Return if fever, shortness of breath, or chest pain\\n4. Follow up with primary care physician in 1 week",
        "next_appointment_date": "2025-09-02",
        "next_appointment_with": "Dr. Smith (Primary Care)",
        "discharge_condition": "Good - stable and improved",
        "discharge_disposition": "Home with family",
        "generated_by": "DOC001"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/discharge-summary/generate/{patient_id}", 
                               json=summary_data)
        if response.status_code == 200:
            print("✓ Discharge summary generated successfully")
            summary = response.json()['summary']
            print(f"  Length of stay: {summary['length_of_stay']} days")
            print(f"  Primary diagnosis: {summary['primary_diagnosis']}")
            print(f"  Medications to continue: {len(summary['medications_to_continue'])} items")
        else:
            print(f"✗ Summary generation failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Summary generation error: {e}")
    
    print()
    
    # Step 5: Get printable summary
    print("STEP 5: Getting printable discharge summary...")
    try:
        response = requests.get(f"{BASE_URL}/discharge-summary/print/{patient_id}")
        if response.status_code == 200:
            print("✓ Printable summary retrieved")
            summary = response.json()['printable_summary']
            print(f"  Patient: {summary['patient_info']['name']}")
            print(f"  Stay: {summary['patient_info']['length_of_stay']}")
            print(f"  Condition: {summary['clinical_summary']['discharge_condition']}")
            print(f"  Follow-up: {summary['instructions']['next_appointment']['date']}")
        else:
            print(f"✗ Printable summary failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Printable summary error: {e}")
    
    print()
    print("=== WORKFLOW TEST COMPLETE ===")

if __name__ == "__main__":
    test_discharge_workflow()
