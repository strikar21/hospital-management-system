"""
Quick script to check ESP32 devices in database
"""
import asyncio
import asyncpg

async def check_devices():
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')

    devices = await conn.fetch('''
        SELECT d.id, d."serialNumber", d."deviceType", d."macAddress",
               d."firmwareVersion", da."patientId" as "assignedPatientId",
               d.status, d."batteryLevel"
        FROM devices d
        LEFT JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
        WHERE d."deviceType" = 'watch'
        ORDER BY d."createdAt" DESC
        LIMIT 10
    ''')

    print("=" * 120)
    print("ESP32 WATCH DEVICES IN DATABASE")
    print("=" * 120)
    print(f"{'ID':<20} {'Serial':<15} {'MAC Address':<20} {'FW':<10} {'Patient':<15} {'Status':<12} {'Battery':<8}")
    print("-" * 120)

    for row in devices:
        device_id = row['id']
        serial = row['serialNumber']
        mac = row.get('macAddress', 'N/A')
        fw = row.get('firmwareVersion', 'N/A')
        patient = row.get('assignedPatientId', 'N/A')
        status = row['status']
        battery = row.get('batteryLevel', 'N/A')

        print(f"{device_id:<20} {serial:<15} {mac:<20} {fw:<10} {str(patient):<15} {status:<12} {str(battery):<8}")

    print(f"\nTotal ESP32 watches: {len(devices)}")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_devices())
