#!/usr/bin/env python3
"""
Script to add comprehensive medical records with unique data for each patient
"""

import asyncio
import asyncpg
from datetime import datetime, date, timedelta
import uuid
from app.core.config import settings

async def clear_existing_records():
    """Clear existing medical records to start fresh"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        # Clear existing records
        await conn.execute("DELETE FROM patientnotes")
        await conn.execute("DELETE FROM medications")
        await conn.execute("DELETE FROM investigations")
        await conn.execute("DELETE FROM therapy")
        await conn.execute("DELETE FROM therapysessions")

        print("Cleared existing medical records")

    finally:
        await conn.close()

async def add_comprehensive_medical_records():
    """Add comprehensive, unique medical records for each patient"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        # Get all patients
        patients = await conn.fetch("""
            SELECT id, "firstName", "lastName", "attendingPhysician", "nurseInCharge"
            FROM patients
            ORDER BY "createdAt"
        """)

        print(f"Found {len(patients)} patients to update")

        for i, patient in enumerate(patients):
            patient_id = patient['id']
            patient_name = f"{patient['firstName']} {patient['lastName']}"
            attending_doc = patient['attendingPhysician']
            nurse = patient['nurseInCharge']

            print(f"Adding records for {patient_name}")

            # Create unique patient notes based on patient condition
            if i == 0:  # Robert Anderson - Cardiac/Diabetes
                notes_data = [
                    {
                        "patientId": patient_id,
                        "content": f"Admitted {patient_name} with chest pain and elevated blood glucose. EKG shows no acute changes. Blood pressure elevated at 150/95.",
                        "authorId": attending_doc,
                        "authorName": "Dr. Sarah Johnson" if attending_doc == "DOC0001" else "Dr. Michael Chen",
                        "authorRole": "Doctor"
                    },
                    {
                        "patientId": patient_id,
                        "content": f"Patient's vitals stabilized overnight. Blood glucose trending down with current insulin regimen. Patient ambulating without assistance.",
                        "authorId": nurse,
                        "authorName": "Emily Rodriguez" if nurse == "NUR0001" else "James Wilson",
                        "authorRole": "Nurse"
                    },
                    {
                        "patientId": patient_id,
                        "content": f"Cardiology consult completed. Recommending stress test as outpatient. Continue current cardiac medications. Patient education on diet provided.",
                        "authorId": "DOC0002",
                        "authorName": "Dr. Michael Chen",
                        "authorRole": "Doctor"
                    }
                ]

                # Medications for Robert Anderson
                medications_data = [
                    {
                        "patientId": patient_id,
                        "name": "Metformin",
                        "dosage": "500mg",
                        "frequency": "Twice daily",
                        "route": "Oral",
                        "status": "active",
                        "prescribedBy": attending_doc
                    },
                    {
                        "patientId": patient_id,
                        "name": "Lisinopril",
                        "dosage": "10mg",
                        "frequency": "Once daily",
                        "route": "Oral",
                        "status": "active",
                        "prescribedBy": attending_doc
                    },
                    {
                        "patientId": patient_id,
                        "name": "Atorvastatin",
                        "dosage": "20mg",
                        "frequency": "Once daily at bedtime",
                        "route": "Oral",
                        "status": "active",
                        "prescribedBy": attending_doc
                    }
                ]

                # Investigations for Robert
                investigations_data = [
                    {
                        "patientId": patient_id,
                        "type": "Laboratory",
                        "name": "HbA1c",
                        "status": "completed",
                        "results": "8.2% (elevated)",
                        "performedBy": "LAB001"
                    },
                    {
                        "patientId": patient_id,
                        "type": "Cardiology",
                        "name": "Echocardiogram",
                        "status": "scheduled",
                        "priority": "routine",
                        "scheduledAt": datetime.now() + timedelta(days=1)
                    }
                ]

            elif i == 1:  # William Johnson - COPD/CHF
                notes_data = [
                    {
                        "patientId": patient_id,
                        "content": f"Patient {patient_name} admitted with acute exacerbation of COPD. Increased shortness of breath and productive cough. Chest X-ray shows hyperinflation.",
                        "authorId": attending_doc,
                        "authorName": "Dr. Sarah Johnson" if attending_doc == "DOC0001" else "Dr. Michael Chen",
                        "authorRole": "Doctor"
                    },
                    {
                        "patientId": patient_id,
                        "content": f"Nebulizer treatments administered q4h. Patient's oxygen saturation improved from 88% to 94% on 2L nasal cannula. Less dyspnea noted.",
                        "authorId": nurse,
                        "authorName": "Emily Rodriguez" if nurse == "NUR0001" else "James Wilson",
                        "authorRole": "Nurse"
                    },
                    {
                        "patientId": patient_id,
                        "content": f"Pulmonary function tests ordered. Continue bronchodilators and steroids. Patient education on inhaler technique reinforced.",
                        "authorId": attending_doc,
                        "authorName": "Dr. Sarah Johnson" if attending_doc == "DOC0001" else "Dr. Michael Chen",
                        "authorRole": "Doctor"
                    }
                ]

                medications_data = [
                    {
                        "patientId": patient_id,
                        "name": "Albuterol",
                        "dosage": "2.5mg/3ml",
                        "frequency": "Every 4 hours",
                        "route": "Nebulizer",
                        "status": "active",
                        "prescribedBy": attending_doc
                    },
                    {
                        "patientId": patient_id,
                        "name": "Prednisone",
                        "dosage": "40mg",
                        "frequency": "Once daily",
                        "route": "Oral",
                        "status": "active",
                        "prescribedBy": attending_doc
                    }
                ]

                investigations_data = [
                    {
                        "patientId": patient_id,
                        "type": "Pulmonary",
                        "name": "Chest X-Ray",
                        "status": "completed",
                        "results": "Hyperinflated lungs, no acute infiltrates",
                        "performedBy": "RAD001"
                    }
                ]

                # Add therapy for COPD patient
                therapy_data = [
                    {
                        "patientId": patient_id,
                        "type": "Respiratory Therapy",
                        "description": "Pulmonary rehabilitation and breathing exercises",
                        "frequency": "Daily",
                        "status": "active",
                        "performedBy": "TEC0001"
                    }
                ]

            elif i == 2:  # Jennifer Lee - Anxiety/Migraine
                notes_data = [
                    {
                        "patientId": patient_id,
                        "content": f"{patient_name} presented with severe migraine headache and anxiety attack. Patient reports increased stress at work. Vital signs stable.",
                        "authorId": attending_doc,
                        "authorName": "Dr. Sarah Johnson" if attending_doc == "DOC0001" else "Dr. Michael Chen",
                        "authorRole": "Doctor"
                    },
                    {
                        "patientId": patient_id,
                        "content": f"Administered IV fluids and anti-emetics. Patient resting comfortably in darkened room. Anxiety level decreased from 8/10 to 4/10.",
                        "authorId": nurse,
                        "authorName": "Emily Rodriguez" if nurse == "NUR0001" else "James Wilson",
                        "authorRole": "Nurse"
                    }
                ]

                medications_data = [
                    {
                        "patientId": patient_id,
                        "name": "Sumatriptan",
                        "dosage": "50mg",
                        "frequency": "As needed for migraine",
                        "route": "Oral",
                        "status": "active",
                        "prescribedBy": attending_doc
                    },
                    {
                        "patientId": patient_id,
                        "name": "Sertraline",
                        "dosage": "50mg",
                        "frequency": "Once daily",
                        "route": "Oral",
                        "status": "active",
                        "prescribedBy": attending_doc
                    }
                ]

                investigations_data = [
                    {
                        "patientId": patient_id,
                        "type": "Neurology",
                        "name": "MRI Brain",
                        "status": "scheduled",
                        "priority": "routine",
                        "scheduledAt": datetime.now() + timedelta(days=3)
                    }
                ]

                therapy_data = [
                    {
                        "patientId": patient_id,
                        "type": "Behavioral Therapy",
                        "description": "Cognitive behavioral therapy for anxiety management",
                        "frequency": "Weekly",
                        "status": "active",
                        "performedBy": "PSY001"
                    }
                ]

            else:  # Thomas Brown - Cancer/Arthritis
                notes_data = [
                    {
                        "patientId": patient_id,
                        "content": f"Regular follow-up for {patient_name}. Cancer remains in remission. Kidney function stable. Complains of increased joint pain in knees and hips.",
                        "authorId": attending_doc,
                        "authorName": "Dr. Sarah Johnson" if attending_doc == "DOC0001" else "Dr. Michael Chen",
                        "authorRole": "Doctor"
                    },
                    {
                        "patientId": patient_id,
                        "content": f"Patient ambulating slowly due to arthritis pain. Applied heat pads to affected joints. Patient reports some improvement in comfort level.",
                        "authorId": nurse,
                        "authorName": "Emily Rodriguez" if nurse == "NUR0001" else "James Wilson",
                        "authorRole": "Nurse"
                    }
                ]

                medications_data = [
                    {
                        "patientId": patient_id,
                        "name": "Acetaminophen",
                        "dosage": "1000mg",
                        "frequency": "Three times daily",
                        "route": "Oral",
                        "status": "active",
                        "prescribedBy": attending_doc
                    },
                    {
                        "patientId": patient_id,
                        "name": "Calcium Carbonate",
                        "dosage": "500mg",
                        "frequency": "Twice daily",
                        "route": "Oral",
                        "status": "active",
                        "prescribedBy": attending_doc
                    }
                ]

                investigations_data = [
                    {
                        "patientId": patient_id,
                        "type": "Laboratory",
                        "name": "PSA Level",
                        "status": "completed",
                        "results": "2.1 ng/mL (normal)",
                        "performedBy": "LAB001"
                    },
                    {
                        "patientId": patient_id,
                        "type": "Laboratory",
                        "name": "Creatinine",
                        "status": "completed",
                        "results": "1.8 mg/dL (elevated)",
                        "performedBy": "LAB001"
                    }
                ]

                therapy_data = [
                    {
                        "patientId": patient_id,
                        "type": "Physical Therapy",
                        "description": "Range of motion exercises for arthritis management",
                        "frequency": "Three times weekly",
                        "status": "active",
                        "performedBy": "PT001"
                    }
                ]

            # Insert notes
            for note in notes_data:
                await conn.execute("""
                    INSERT INTO patientnotes (
                        "patientId", content, "authorId", "authorName", "authorRole", timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """, note["patientId"], note["content"], note["authorId"],
                    note["authorName"], note["authorRole"], datetime.now())

            # Insert medications
            for med in medications_data:
                await conn.execute("""
                    INSERT INTO medications (
                        "patientId", name, dosage, frequency, route, status,
                        "startDate", "prescribedBy", "createdAt", "updatedAt"
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """, med["patientId"], med["name"], med["dosage"], med["frequency"],
                    med["route"], med["status"], datetime.now(), med["prescribedBy"],
                    datetime.now(), datetime.now())

            # Insert investigations
            for inv in investigations_data:
                await conn.execute("""
                    INSERT INTO investigations (
                        "patientId", type, name, status, "scheduledAt", results,
                        priority, "performedBy", "createdAt", "updatedAt"
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """, inv["patientId"], inv["type"], inv["name"], inv["status"],
                    inv.get("scheduledAt"), inv.get("results"),
                    inv.get("priority", "routine"), inv.get("performedBy"),
                    datetime.now(), datetime.now())

            # Insert therapy if exists
            if 'therapy_data' in locals():
                for therapy in therapy_data:
                    await conn.execute("""
                        INSERT INTO therapy (
                            "patientId", type, description, frequency, status,
                            "performedBy", "startDate", "createdAt", "updatedAt"
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """, therapy["patientId"], therapy["type"], therapy["description"],
                        therapy["frequency"], therapy["status"], therapy["performedBy"],
                        datetime.now(), datetime.now(), datetime.now())

                # Clear therapy_data for next iteration
                del therapy_data

            print(f"Added comprehensive records for {patient_name}")

        print(f"Successfully added unique medical records for all {len(patients)} patients")

    finally:
        await conn.close()

async def main():
    """Main function"""
    print("Updating medical records with unique data for each patient...")

    try:
        print("Clearing existing records...")
        await clear_existing_records()

        print("Adding comprehensive medical records...")
        await add_comprehensive_medical_records()

        print("Medical records update completed successfully!")

    except Exception as e:
        print(f"Error updating medical records: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())