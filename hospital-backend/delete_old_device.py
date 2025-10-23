"""
Delete old device record with colon-based serial number
This allows re-provisioning with sanitized device ID
"""

import asyncio
import asyncpg

async def delete_old_device():
    # Connect to database
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='hospitaldb',
        user='hospital_user',
        password='hospital123'
    )

    try:
        # Find device with old serial number
        old_serial = "SN-A0:A3:B3:AA:13:B0"

        device = await conn.fetchrow(
            'SELECT id, "serialNumber", "deviceType" FROM devices WHERE "serialNumber" = $1',
            old_serial
        )

        if device:
            print(f"Found device: {device['id']}")
            print(f"  Serial: {device['serialNumber']}")
            print(f"  Type: {device['deviceType']}")

            # Delete device (CASCADE will delete related records)
            await conn.execute(
                'DELETE FROM devices WHERE "serialNumber" = $1',
                old_serial
            )

            print(f"[OK] Deleted device with serial {old_serial}")
            print("Device can now re-provision with sanitized ID")
        else:
            print(f"No device found with serial {old_serial}")

        # Also check for device with old ID
        old_id = "ESP32-WATCH-A0:A3:B3:AA:13:B0"
        device_by_id = await conn.fetchrow(
            'SELECT id, "serialNumber" FROM devices WHERE id = $1',
            old_id
        )

        if device_by_id:
            print(f"\nFound device by ID: {device_by_id['id']}")
            await conn.execute('DELETE FROM devices WHERE id = $1', old_id)
            print(f"[OK] Deleted device with ID {old_id}")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(delete_old_device())
