"""
Seed test patients for dashboard testing
Run this to create sample patients with room assignments
"""
import asyncio
import asyncpg
from datetime import datetime, date
from app.core.config import settings

async def seed_patients():
    """Create test patients for dashboard"""

    patients = [
        {
            "id": "PAT0001",
            "firstName": "Rajesh",
            "lastName": "Kumar",
            "dateOfBirth": "1975-05-15",
            "gender": "male",
            "bloodType": "O+",
            "phoneNumber": "+91-9876543210",
            "emergencyContactName": "Sunita Kumar",
            "emergencyContactPhone": "+91-9876543211",
            "roomNumber": "101",
            "bedNumber": "A",
            "status": "active",
            "admissionDate": datetime.utcnow()
        },
        {
            "id": "PAT0002",
            "firstName": "Priya",
            "lastName": "Sharma",
            "dateOfBirth": "1988-08-22",
            "gender": "female",
            "bloodType": "A+",
            "phoneNumber": "+91-9876543212",
            "emergencyContactName": "Rahul Sharma",
            "emergencyContactPhone": "+91-9876543213",
            "roomNumber": "101",
            "bedNumber": "B",
            "status": "active",
            "admissionDate": datetime.utcnow()
        },
        {
            "id": "PAT0003",
            "firstName": "Mohammed",
            "lastName": "Ali",
            "dateOfBirth": "1965-12-10",
            "gender": "male",
            "bloodType": "B+",
            "phoneNumber": "+91-9876543214",
            "emergencyContactName": "Fatima Ali",
            "emergencyContactPhone": "+91-9876543215",
            "roomNumber": "102",
            "bedNumber": "A",
            "status": "active",
            "admissionDate": datetime.utcnow()
        },
        {
            "id": "PAT0004",
            "firstName": "Lakshmi",
            "lastName": "Devi",
            "dateOfBirth": "1992-03-18",
            "gender": "female",
            "bloodType": "AB+",
            "phoneNumber": "+91-9876543216",
            "emergencyContactName": "Ravi Devi",
            "emergencyContactPhone": "+91-9876543217",
            "roomNumber": "102",
            "bedNumber": "B",
            "status": "active",
            "admissionDate": datetime.utcnow()
        },
        {
            "id": "PAT0005",
            "firstName": "Amit",
            "lastName": "Patel",
            "dateOfBirth": "1980-11-25",
            "gender": "male",
            "bloodType": "O-",
            "phoneNumber": "+91-9876543218",
            "emergencyContactName": "Neha Patel",
            "emergencyContactPhone": "+91-9876543219",
            "roomNumber": "103",
            "bedNumber": "A",
            "status": "active",
            "admissionDate": datetime.utcnow()
        }
    ]

    try:
        # Connect to PostgreSQL
        conn = await asyncpg.connect(settings.databaseUrl)

        print("Seeding test patients...")

        for patient in patients:
            # Check if patient already exists
            existing = await conn.fetchval(
                "SELECT id FROM patients WHERE id = $1",
                patient["id"]
            )

            if existing:
                print(f"[SKIP] Patient {patient['id']} already exists")
                continue

            # Insert new patient
            await conn.execute("""
                INSERT INTO patients (
                    id, "firstName", "lastName", "dateOfBirth", gender, "bloodType",
                    "phoneNumber", "emergencyContactName", "emergencyContactPhone",
                    "roomNumber", "bedNumber", "admissionDate", status, "createdAt", "updatedAt"
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW(), NOW())
            """,
                patient["id"],
                patient["firstName"],
                patient["lastName"],
                patient["dateOfBirth"],
                patient["gender"],
                patient["bloodType"],
                patient["phoneNumber"],
                patient["emergencyContactName"],
                patient["emergencyContactPhone"],
                patient["roomNumber"],
                patient["bedNumber"],
                patient["admissionDate"],
                patient["status"]
            )
            print(f"[OK] Created patient: {patient['id']} - {patient['firstName']} {patient['lastName']} (Room {patient['roomNumber']}-{patient['bedNumber']})")

        # Verify count
        count = await conn.fetchval("SELECT COUNT(*) FROM patients")
        print(f"\n[SUCCESS] Patient seeding complete! Total patients: {count}")
        print("\nTest Patients Created:")
        print("=" * 70)
        print("PAT0001 - Rajesh Kumar (M, O+)      - Room 101-A")
        print("PAT0002 - Priya Sharma (F, A+)      - Room 101-B")
        print("PAT0003 - Mohammed Ali (M, B+)      - Room 102-A")
        print("PAT0004 - Lakshmi Devi (F, AB+)     - Room 102-B")
        print("PAT0005 - Amit Patel (M, O-)        - Room 103-A")
        print("=" * 70)
        print("\nYou can now see these patients in the dashboard!")

        await conn.close()

    except Exception as e:
        print(f"[ERROR] Failed to seed patients: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(seed_patients())
