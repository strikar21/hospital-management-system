import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_calibration():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))

    print("=" * 80)
    print("CALIBRATION FLOW DIAGNOSTIC")
    print("=" * 80)

    # Check devices
    print("\n1. DEVICES:")
    devices = await conn.fetch("SELECT id, status FROM devices LIMIT 10")
    for d in devices:
        print(f"   - Device: {d['id']}, Status: {d['status']}")

    # Check assignments
    print("\n2. ACTIVE DEVICE ASSIGNMENTS:")
    assignments = await conn.fetch("""
        SELECT da."deviceId", da."patientId", d.status as device_status
        FROM deviceassignments da
        JOIN devices d ON da."deviceId" = d.id
        WHERE da."assignedAt" IS NOT NULL
        AND da."unassignedAt" IS NULL
        ORDER BY da."assignedAt" DESC
        LIMIT 10
    """)

    if assignments:
        for a in assignments:
            print(f"   - Device {a['deviceId']} -> Patient {a['patientId']} (device status: {a['device_status']})")
    else:
        print("   *** NO ACTIVE ASSIGNMENTS FOUND ***")

    # Check patients
    print("\n3. ACTIVE PATIENTS:")
    patients = await conn.fetch("SELECT id, \"firstName\", \"lastName\", status FROM patients WHERE status = 'active' LIMIT 10")
    for p in patients:
        print(f"   - Patient: {p['id']}, Name: {p['firstName']} {p['lastName']}, Status: {p['status']}")

    await conn.close()

asyncio.run(check_calibration())
