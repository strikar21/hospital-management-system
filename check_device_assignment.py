import asyncio
import asyncpg

async def check_assignment():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='hospital_user',
        password='hospital123',
        database='hospitaldb'
    )
    
    try:
        # Check device
        device = await conn.fetchrow("""
            SELECT id, "deviceType", name, "macAddress", status, "lastSeen", "batteryLevel"
            FROM devices 
            WHERE id = 'fit-00001'
        """)
        
        print("\n=== DEVICE INFO ===")
        if device:
            print(f"Device ID: {device['id']}")
            print(f"Device Type: {device['deviceType']}")
            print(f"Name: {device['name']}")
            print(f"MAC Address: {device['macAddress']}")
            print(f"Status: {device['status']}")
            print(f"Last Seen: {device['lastSeen']}")
            print(f"Battery Level: {device['batteryLevel']}%")
        else:
            print("❌ Device 'fit-00001' NOT FOUND in database!")
            return
        
        # Check patient
        patient_id = '081a5294-da91-4c74-bb8a-e5062f5851dd'
        patient = await conn.fetchrow("""
            SELECT id, "firstName", "lastName", status
            FROM patients
            WHERE id = $1
        """, patient_id)
        
        print("\n=== PATIENT INFO ===")
        if patient:
            print(f"Patient ID: {patient['id']}")
            print(f"Name: {patient['firstName']} {patient['lastName']}")
            print(f"Status: {patient['status']}")
        else:
            print(f"❌ Patient {patient_id} NOT FOUND!")
            return
        
        # Check device assignment
        assignment = await conn.fetchrow("""
            SELECT "patientId", "deviceId", status, "assignedAt", "assignedBy"
            FROM deviceassignments
            WHERE "deviceId" = 'fit-00001'
            ORDER BY "assignedAt" DESC
            LIMIT 1
        """)
        
        print("\n=== DEVICE ASSIGNMENT ===")
        if assignment:
            print(f"Patient ID: {assignment['patientId']}")
            print(f"Device ID: {assignment['deviceId']}")
            print(f"Status: {assignment['status']}")
            print(f"Assigned At: {assignment['assignedAt']}")
            print(f"Assigned By: {assignment['assignedBy']}")
            
            if assignment['status'] != 'active':
                print(f"\n⚠️ WARNING: Assignment status is '{assignment['status']}', not 'active'!")
            if assignment['patientId'] != patient_id:
                print(f"\n⚠️ WARNING: Device assigned to different patient!")
                print(f"   ESP32 expects: {patient_id}")
                print(f"   Database has: {assignment['patientId']}")
        else:
            print("❌ NO ASSIGNMENT FOUND for device 'fit-00001'!")
            print("\n💡 Solution: Assign device to patient via frontend Device Assignment page")
        
        # Check if patient has any active assignment
        patient_assignment = await conn.fetchrow("""
            SELECT "patientId", "deviceId", status
            FROM deviceassignments
            WHERE "patientId" = $1 AND status = 'active'
        """, patient_id)
        
        print("\n=== PATIENT'S ACTIVE ASSIGNMENT ===")
        if patient_assignment:
            print(f"✅ Patient has active device: {patient_assignment['deviceId']}")
            print(f"   Status: {patient_assignment['status']}")
            
            if patient_assignment['deviceId'] != 'fit-00001':
                print(f"\n⚠️ MISMATCH DETECTED!")
                print(f"   ESP32 watch hardcoded patient: {patient_id}")
                print(f"   ESP32 watch device ID: fit-00001")
                print(f"   Database says patient has device: {patient_assignment['deviceId']}")
                print(f"\n💡 Solution: Update device assignment to match ESP32")
        else:
            print(f"❌ Patient has NO ACTIVE device assignment!")
            print("\n💡 Solution: Assign device 'fit-00001' to patient {patient_id}")
        
        print("\n=== DIAGNOSIS ===")
        if device and patient:
            if assignment and assignment['status'] == 'active' and assignment['patientId'] == patient_id:
                print("✅ Everything looks correct!")
                print("   Device and patient are properly assigned")
                print("\n   If frontend still shows 'watch not connected', check:")
                print("   1. Backend MQTT service is receiving messages")
                print("   2. WebSocket connection between backend and frontend")
                print("   3. Frontend is querying the correct patient ID")
            else:
                print("❌ Device assignment issue detected")
                print("   Run device assignment flow in frontend to fix")
        
    finally:
        await conn.close()

asyncio.run(check_assignment())
