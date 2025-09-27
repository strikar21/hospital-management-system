#!/usr/bin/env python3
"""
Script to populate the hospital database with sample staff and patients
"""

import asyncio
import asyncpg
from datetime import datetime, date
import uuid
from app.core.config import settings
from app.core.security import hash_pin, hash_password

async def populate_staff():
    """Create comprehensive staff members"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        # Create staff members with full details
        staff_data = [
            {
                "id": "DOC0001",
                "firstName": "Sarah",
                "lastName": "Johnson",
                "role": "Doctor",
                "email": "sarah.johnson@hospital.com",
                "phoneNumber": "+1-555-0101",
                "department": "Cardiology",
                "pin": hash_pin("1234"),
                "password": hash_password("doctor123"),
                "nfcCardId": "CARD_DOC_001",
                "isActive": True
            },
            {
                "id": "DOC0002",
                "firstName": "Michael",
                "lastName": "Chen",
                "role": "Doctor",
                "email": "michael.chen@hospital.com",
                "phoneNumber": "+1-555-0102",
                "department": "Emergency Medicine",
                "pin": hash_pin("2345"),
                "password": hash_password("doctor456"),
                "nfcCardId": "CARD_DOC_002",
                "isActive": True
            },
            {
                "id": "NUR0001",
                "firstName": "Emily",
                "lastName": "Rodriguez",
                "role": "Nurse",
                "email": "emily.rodriguez@hospital.com",
                "phoneNumber": "+1-555-0201",
                "department": "ICU",
                "pin": hash_pin("5678"),
                "password": hash_password("nurse123"),
                "nfcCardId": "CARD_NUR_001",
                "isActive": True
            },
            {
                "id": "NUR0002",
                "firstName": "James",
                "lastName": "Wilson",
                "role": "Nurse",
                "email": "james.wilson@hospital.com",
                "phoneNumber": "+1-555-0202",
                "department": "General Ward",
                "pin": hash_pin("5679"),
                "password": hash_password("nurse124"),
                "nfcCardId": "CARD_NUR_002",
                "isActive": True
            },
            {
                "id": "ADM0001",
                "firstName": "Lisa",
                "lastName": "Thompson",
                "role": "Administrator",
                "email": "lisa.thompson@hospital.com",
                "phoneNumber": "+1-555-0301",
                "department": "Administration",
                "pin": hash_pin("9999"),
                "password": hash_password("admin123"),
                "nfcCardId": "CARD_ADM_001",
                "isActive": True
            },
            {
                "id": "TEC0001",
                "firstName": "David",
                "lastName": "Kumar",
                "role": "Technician",
                "email": "david.kumar@hospital.com",
                "phoneNumber": "+1-555-0401",
                "department": "IT Support",
                "pin": hash_pin("2222"),
                "password": hash_password("tech123"),
                "nfcCardId": "CARD_TEC_001",
                "isActive": True
            }
        ]

        for staff in staff_data:
            await conn.execute("""
                INSERT INTO staff (
                    id, "firstName", "lastName", role, email, "phoneNumber", department,
                    pin, password, "nfcCardId", "isActive", "createdAt", "updatedAt"
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (id) DO UPDATE SET
                    "firstName" = EXCLUDED."firstName",
                    "lastName" = EXCLUDED."lastName",
                    role = EXCLUDED.role,
                    email = EXCLUDED.email,
                    "phoneNumber" = EXCLUDED."phoneNumber",
                    department = EXCLUDED.department,
                    pin = EXCLUDED.pin,
                    password = EXCLUDED.password,
                    "nfcCardId" = EXCLUDED."nfcCardId",
                    "updatedAt" = NOW()
            """, staff["id"], staff["firstName"], staff["lastName"], staff["role"],
                staff["email"], staff["phoneNumber"], staff["department"],
                staff["pin"], staff["password"], staff["nfcCardId"],
                staff["isActive"], datetime.now(), datetime.now())

        print(f"Created {len(staff_data)} staff members")

    finally:
        await conn.close()

async def populate_patients():
    """Create patients with comprehensive medical histories"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        # Create patients with detailed medical information
        patients_data = [
            {
                "id": str(uuid.uuid4()),
                "firstName": "Robert",
                "lastName": "Anderson",
                "dateOfBirth": date(1965, 3, 15),
                "gender": "Male",
                "phoneNumber": "+1-555-1001",
                "emergencyContactName": "Mary Anderson (Wife)",
                "emergencyContactPhone": "+1-555-1002",
                "bloodType": "A+",
                "allergies": "Penicillin, Shellfish",
                "medicalHistory": "Hypertension since 2018, Type 2 Diabetes since 2020, Previous MI in 2021",
                "currentMedications": "Metformin 500mg BID, Lisinopril 10mg daily, Atorvastatin 20mg daily",
                "admissionDate": datetime.now(),
                "roomNumber": "201",
                "bedNumber": "A",
                "attendingPhysician": "DOC0001",
                "nurseInCharge": "NUR0001",
                "status": "active"
            },
            {
                "id": str(uuid.uuid4()),
                "firstName": "Maria",
                "lastName": "Garcia",
                "dateOfBirth": date(1978, 7, 22),
                "gender": "Female",
                "phoneNumber": "+1-555-1003",
                "emergencyContactName": "Carlos Garcia (Husband)",
                "emergencyContactPhone": "+1-555-1004",
                "bloodType": "O-",
                "allergies": "Latex, Aspirin",
                "medicalHistory": "Asthma since childhood, Gestational diabetes in 2010, Chronic back pain",
                "currentMedications": "Albuterol inhaler PRN, Ibuprofen 400mg PRN, Omeprazole 20mg daily",
                "admissionDate": datetime.now(),
                "roomNumber": "202",
                "bedNumber": "B",
                "attendingPhysician": "DOC0002",
                "nurseInCharge": "NUR0002",
                "status": "active"
            },
            {
                "id": str(uuid.uuid4()),
                "firstName": "William",
                "lastName": "Johnson",
                "dateOfBirth": date(1952, 11, 8),
                "gender": "Male",
                "phoneNumber": "+1-555-1005",
                "emergencyContactName": "Susan Johnson (Daughter)",
                "emergencyContactPhone": "+1-555-1006",
                "bloodType": "B+",
                "allergies": "None known",
                "medicalHistory": "COPD, Previous stroke 2019, Atrial fibrillation, CHF",
                "currentMedications": "Warfarin 5mg daily, Digoxin 0.25mg daily, Furosemide 40mg BID, Spiriva inhaler",
                "admissionDate": datetime.now(),
                "roomNumber": "203",
                "bedNumber": "A",
                "attendingPhysician": "DOC0001",
                "nurseInCharge": "NUR0001",
                "status": "active"
            },
            {
                "id": str(uuid.uuid4()),
                "firstName": "Jennifer",
                "lastName": "Lee",
                "dateOfBirth": date(1990, 5, 30),
                "gender": "Female",
                "phoneNumber": "+1-555-1007",
                "emergencyContactName": "David Lee (Brother)",
                "emergencyContactPhone": "+1-555-1008",
                "bloodType": "AB+",
                "allergies": "Sulfa drugs",
                "medicalHistory": "Anxiety disorder, Migraine headaches, Previous appendectomy 2015",
                "currentMedications": "Sertraline 50mg daily, Sumatriptan 50mg PRN, Birth control pill",
                "admissionDate": datetime.now(),
                "roomNumber": "204",
                "bedNumber": "A",
                "attendingPhysician": "DOC0002",
                "nurseInCharge": "NUR0002",
                "status": "active"
            },
            {
                "id": str(uuid.uuid4()),
                "firstName": "Thomas",
                "lastName": "Brown",
                "dateOfBirth": date(1943, 12, 12),
                "gender": "Male",
                "phoneNumber": "+1-555-1009",
                "emergencyContactName": "Patricia Brown (Wife)",
                "emergencyContactPhone": "+1-555-1010",
                "bloodType": "O+",
                "allergies": "Codeine, NSAIDs",
                "medicalHistory": "Prostate cancer (remission), Osteoarthritis, Chronic kidney disease stage 3",
                "currentMedications": "Acetaminophen 1000mg TID, Calcium carbonate 500mg BID, Vitamin D3 1000IU daily",
                "admissionDate": datetime.now(),
                "roomNumber": "205",
                "bedNumber": "B",
                "attendingPhysician": "DOC0001",
                "nurseInCharge": "NUR0001",
                "status": "active"
            }
        ]

        for patient in patients_data:
            await conn.execute("""
                INSERT INTO patients (
                    id, "firstName", "lastName", "dateOfBirth", gender, "phoneNumber",
                    "emergencyContactName", "emergencyContactPhone", "bloodType", allergies,
                    "medicalHistory", "currentMedications", "admissionDate", "roomNumber",
                    "bedNumber", "attendingPhysician", "nurseInCharge", status, "createdAt", "updatedAt"
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
            """, patient["id"], patient["firstName"], patient["lastName"], patient["dateOfBirth"],
                patient["gender"], patient["phoneNumber"], patient["emergencyContactName"],
                patient["emergencyContactPhone"], patient["bloodType"], patient["allergies"],
                patient["medicalHistory"], patient["currentMedications"], patient["admissionDate"],
                patient["roomNumber"], patient["bedNumber"], patient["attendingPhysician"],
                patient["nurseInCharge"], patient["status"], datetime.now(), datetime.now())

        print(f"Created {len(patients_data)} patients with comprehensive medical histories")

        # Get patient IDs for creating medications and other records
        patient_ids = await conn.fetch("SELECT id, \"firstName\", \"lastName\" FROM patients ORDER BY \"createdAt\" DESC LIMIT 5")
        return [dict(row) for row in patient_ids]

    finally:
        await conn.close()

async def populate_medications(patient_ids):
    """Create medication records for patients"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        medications_data = []

        # Create medications for each patient
        for i, patient in enumerate(patient_ids):
            patient_id = patient['id']

            if i == 0:  # Robert Anderson - Cardiac patient
                medications_data.extend([
                    {
                        "patientId": patient_id,
                        "name": "Metformin",
                        "dosage": "500mg",
                        "frequency": "Twice daily",
                        "route": "Oral",
                        "status": "active",
                        "startDate": datetime.now(),
                        "prescribedBy": "DOC0001"
                    },
                    {
                        "patientId": patient_id,
                        "name": "Lisinopril",
                        "dosage": "10mg",
                        "frequency": "Once daily",
                        "route": "Oral",
                        "status": "active",
                        "startDate": datetime.now(),
                        "prescribedBy": "DOC0001"
                    }
                ])
            elif i == 1:  # Maria Garcia - Asthma patient
                medications_data.extend([
                    {
                        "patientId": patient_id,
                        "name": "Albuterol",
                        "dosage": "90mcg/puff",
                        "frequency": "As needed",
                        "route": "Inhalation",
                        "status": "active",
                        "startDate": datetime.now(),
                        "prescribedBy": "DOC0002"
                    },
                    {
                        "patientId": patient_id,
                        "name": "Omeprazole",
                        "dosage": "20mg",
                        "frequency": "Once daily",
                        "route": "Oral",
                        "status": "active",
                        "startDate": datetime.now(),
                        "prescribedBy": "DOC0002"
                    }
                ])

        for med in medications_data:
            await conn.execute("""
                INSERT INTO medications (
                    "patientId", name, dosage, frequency, route, status,
                    "startDate", "prescribedBy", "createdAt", "updatedAt"
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, med["patientId"], med["name"], med["dosage"], med["frequency"],
                med["route"], med["status"], med["startDate"], med["prescribedBy"],
                datetime.now(), datetime.now())

        print(f"Created {len(medications_data)} medication records")

    finally:
        await conn.close()

async def populate_patient_notes(patient_ids):
    """Create patient notes"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        notes_data = []

        for i, patient in enumerate(patient_ids):
            patient_id = patient['id']
            patient_name = f"{patient['firstName']} {patient['lastName']}"

            notes_data.extend([
                {
                    "patientId": patient_id,
                    "content": f"Initial assessment completed for {patient_name}. Patient stable and oriented.",
                    "authorId": "DOC0001",
                    "authorName": "Dr. Sarah Johnson",
                    "authorRole": "Doctor",
                    "timestamp": datetime.now()
                },
                {
                    "patientId": patient_id,
                    "content": f"Vital signs stable. Patient responding well to current medication regimen.",
                    "authorId": "NUR0001",
                    "authorName": "Emily Rodriguez",
                    "authorRole": "Nurse",
                    "timestamp": datetime.now()
                }
            ])

        for note in notes_data:
            await conn.execute("""
                INSERT INTO patientnotes (
                    "patientId", content, "authorId", "authorName", "authorRole", timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """, note["patientId"], note["content"], note["authorId"],
                note["authorName"], note["authorRole"], note["timestamp"])

        print(f"Created {len(notes_data)} patient notes")

    finally:
        await conn.close()

async def main():
    """Main function to populate all data"""
    print("Populating Hospital Database...")

    try:
        print("Creating staff members...")
        await populate_staff()

        print("Creating patients...")
        patient_ids = await populate_patients()

        print("Creating medication records...")
        await populate_medications(patient_ids)

        print("Creating patient notes...")
        await populate_patient_notes(patient_ids)

        print("Database population completed successfully!")

    except Exception as e:
        print(f"Error populating database: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())