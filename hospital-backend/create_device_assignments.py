"""Create new device assignments with TEXT patient IDs"""

import asyncio
import asyncpg

async def create_assignments():
    conn = await asyncpg.connect(
        user='hospital_user',
        password='hospital123',
        database='hospitaldb',
        host='localhost',
        port=5432
    )

    try:
        print("Creating new device assignments with TEXT patient IDs...")
        print("=" * 70)

        # Define new assignments
        assignments = [
            {'patientId': 'PAT0001', 'deviceId': 'fit-00001', 'assignedBy': 'ADM0001'},
            {'patientId': 'PAT0002', 'deviceId': 'fit-00002', 'assignedBy': 'ADM0001'},
        ]

        for assignment in assignments:
            # Insert new assignment
            await conn.execute("""
                INSERT INTO deviceassignments ("patientId", "deviceId", "assignedBy", "assignedAt", "status")
                VALUES ($1, $2, $3, NOW(), 'active')
            """, assignment['patientId'], assignment['deviceId'], assignment['assignedBy'])

            print(f"✓ Assigned {assignment['deviceId']} -> {assignment['patientId']}")

        print("\n" + "=" * 70)
        print("Verifying new assignments...")
        print("=" * 70 + "\n")

        # Verify new assignments
        result = await conn.fetch("""
            SELECT da."patientId", da."deviceId", da."assignedAt", da."status",
                   p."firstName", p."lastName"
            FROM deviceassignments da
            LEFT JOIN patients p ON da."patientId" = p.id
            WHERE da."unassignedAt" IS NULL
            ORDER BY da."assignedAt" DESC
        """)

        if result:
            print("Active Device Assignments:")
            print("\n| Patient ID | Patient Name | Device ID | Status | Assigned At |")
            print("|------------|--------------|-----------|--------|-------------|")
            for r in result:
                patient_name = f"{r['firstName']} {r['lastName']}" if r['firstName'] else "Unknown"
                assigned_at = r['assignedAt'].strftime('%Y-%m-%d %H:%M')
                status = r['status'] or 'N/A'
                print(f"| {r['patientId']} | {patient_name} | {r['deviceId']} | {status} | {assigned_at} |")

            print(f"\nTotal active assignments: {len(result)}")
        else:
            print("No active assignments found.")

        print("\n" + "=" * 70)
        print("Device assignment creation complete!")
        print("=" * 70)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

asyncio.run(create_assignments())
