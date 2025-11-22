"""
Seed staff members for login authentication
Run this to create default staff accounts for testing
"""
import asyncio
import asyncpg
from app.core.config import settings
from app.core.security import hash_pin, hash_password

async def seed_staff():
    """Create default staff members with credentials"""

    staff_members = [
        {
            "id": "DOC0001",
            "firstName": "Dr. Sarah",
            "lastName": "Johnson",
            "role": "doctor",
            "email": "sarah.johnson@hospital.com",
            "phoneNumber": "+91-9876543210",
            "department": "Cardiology",
            "pin": hash_pin("1234"),
            "password": hash_password("doctor123"),
            "isActive": True
        },
        {
            "id": "DOC0002",
            "firstName": "Dr. Michael",
            "lastName": "Chen",
            "role": "doctor",
            "email": "michael.chen@hospital.com",
            "phoneNumber": "+91-9876543211",
            "department": "Neurology",
            "pin": hash_pin("1235"),
            "password": hash_password("doctor124"),
            "isActive": True
        },
        {
            "id": "NUR0001",
            "firstName": "Nurse Priya",
            "lastName": "Sharma",
            "role": "nurse",
            "email": "priya.sharma@hospital.com",
            "phoneNumber": "+91-9876543212",
            "department": "ICU",
            "pin": hash_pin("5678"),
            "password": hash_password("nurse123"),
            "isActive": True
        },
        {
            "id": "NUR0002",
            "firstName": "Nurse David",
            "lastName": "Wilson",
            "role": "nurse",
            "email": "david.wilson@hospital.com",
            "phoneNumber": "+91-9876543213",
            "department": "General Ward",
            "pin": hash_pin("5679"),
            "password": hash_password("nurse124"),
            "isActive": True
        },
        {
            "id": "ADM0001",
            "firstName": "Admin",
            "lastName": "User",
            "role": "admin",
            "email": "admin@hospital.com",
            "phoneNumber": "+91-9876543214",
            "department": "Administration",
            "pin": hash_pin("9999"),
            "password": hash_password("admin123"),
            "isActive": True
        },
        {
            "id": "PRV0001",
            "firstName": "Provisioner",
            "lastName": "Tech",
            "role": "provisioner",
            "email": "provisioner@hospital.com",
            "phoneNumber": "+91-9876543215",
            "department": "IT",
            "pin": hash_pin("1111"),
            "password": hash_password("prov123"),
            "isActive": True
        },
        {
            "id": "TEC0001",
            "firstName": "Technician",
            "lastName": "Support",
            "role": "technician",
            "email": "tech@hospital.com",
            "phoneNumber": "+91-9876543216",
            "department": "IT",
            "pin": hash_pin("2222"),
            "password": hash_password("tech123"),
            "isActive": True
        }
    ]

    try:
        # Connect to PostgreSQL
        conn = await asyncpg.connect(settings.databaseUrl)

        print("Seeding staff members...")

        for staff in staff_members:
            # Check if staff member already exists
            existing = await conn.fetchval(
                "SELECT id FROM staff WHERE id = $1",
                staff["id"]
            )

            if existing:
                # Update existing
                await conn.execute("""
                    UPDATE staff SET
                        "firstName" = $2,
                        "lastName" = $3,
                        role = $4,
                        email = $5,
                        "phoneNumber" = $6,
                        department = $7,
                        pin = $8,
                        password = $9,
                        "isActive" = $10,
                        "updatedAt" = NOW()
                    WHERE id = $1
                """,
                    staff["id"],
                    staff["firstName"],
                    staff["lastName"],
                    staff["role"],
                    staff["email"],
                    staff["phoneNumber"],
                    staff["department"],
                    staff["pin"],
                    staff["password"],
                    staff["isActive"]
                )
                print(f"[OK] Updated staff member: {staff['id']} ({staff['firstName']} {staff['lastName']})")
            else:
                # Insert new
                await conn.execute("""
                    INSERT INTO staff (
                        id, "firstName", "lastName", role, email, "phoneNumber",
                        department, pin, password, "isActive", "createdAt", "updatedAt"
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
                """,
                    staff["id"],
                    staff["firstName"],
                    staff["lastName"],
                    staff["role"],
                    staff["email"],
                    staff["phoneNumber"],
                    staff["department"],
                    staff["pin"],
                    staff["password"],
                    staff["isActive"]
                )
                print(f"[OK] Created staff member: {staff['id']} ({staff['firstName']} {staff['lastName']})")

        # Verify count
        count = await conn.fetchval("SELECT COUNT(*) FROM staff")
        print(f"\n[SUCCESS] Staff seeding complete! Total staff members: {count}")
        print("\nLogin Credentials:")
        print("=" * 60)
        print("Doctor 1:  PIN: 1234 | Password: doctor123  | ID: DOC0001")
        print("Doctor 2:  PIN: 1235 | Password: doctor124  | ID: DOC0002")
        print("Nurse 1:   PIN: 5678 | Password: nurse123   | ID: NUR0001")
        print("Nurse 2:   PIN: 5679 | Password: nurse124   | ID: NUR0002")
        print("Admin:     PIN: 9999 | Password: admin123   | ID: ADM0001")
        print("Provision: PIN: 1111 | Password: prov123    | ID: PRV0001")
        print("Tech:      PIN: 2222 | Password: tech123    | ID: TEC0001")
        print("=" * 60)

        await conn.close()

    except Exception as e:
        print(f"[ERROR] Failed to seed staff: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(seed_staff())
