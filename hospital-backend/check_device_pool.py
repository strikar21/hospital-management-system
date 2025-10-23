"""
Check Device Pool Status - Query all devices and assignments
"""
import asyncio
import asyncpg
import os
from datetime import datetime

async def check_devices():
    """Check all devices in the pool"""

    # Database connection
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER", "hospital_user"),
        password=os.getenv("DB_PASSWORD", "hospital123"),
        database=os.getenv("DB_NAME", "hospitaldb")
    )

    try:
        print("\n" + "="*80)
        print("DEVICE POOL STATUS REPORT")
        print("="*80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 1. Count all devices by type and status
        print("📊 DEVICE SUMMARY")
        print("-" * 80)
        summary_query = """
            SELECT "deviceType", status, COUNT(*) as count
            FROM devices
            GROUP BY "deviceType", status
            ORDER BY "deviceType", status
        """
        summary = await conn.fetch(summary_query)

        if summary:
            current_type = None
            for row in summary:
                if current_type != row['deviceType']:
                    current_type = row['deviceType']
                    print(f"\n{current_type.upper()}:")
                print(f"  {row['status']:15s}: {row['count']:3d} devices")
        else:
            print("  No devices found in database")

        # 2. List all watches (ESP32 devices)
        print("\n" + "="*80)
        print("🔌 ALL ESP32 WATCHES")
        print("-" * 80)
        watches_query = """
            SELECT
                id,
                "serialNumber",
                "macAddress",
                "firmwareVersion",
                status,
                "batteryLevel",
                location,
                "assignedPatientId",
                "lastSeen",
                "createdAt"
            FROM devices
            WHERE "deviceType" = 'watch' OR "deviceType" = 'esp32Watch'
            ORDER BY "serialNumber"
        """
        watches = await conn.fetch(watches_query)

        if watches:
            for i, watch in enumerate(watches, 1):
                print(f"\n{i}. Watch ID: {watch['id']}")
                print(f"   Serial: {watch['serialNumber']}")
                print(f"   MAC Address: {watch['macAddress'] or 'N/A'}")
                print(f"   Firmware: {watch['firmwareVersion'] or 'N/A'}")
                print(f"   Status: {watch['status']}")
                print(f"   Battery: {watch['batteryLevel'] or 'N/A'}%")
                print(f"   Location: {watch['location'] or 'N/A'}")
                print(f"   Assigned Patient: {watch['assignedPatientId'] or 'None'}")
                print(f"   Last Seen: {watch['lastSeen'] or 'Never'}")
                print(f"   Created: {watch['createdAt']}")
        else:
            print("  No watches found")

        # 3. Check available watches
        print("\n" + "="*80)
        print("✅ AVAILABLE WATCHES (Ready for Assignment)")
        print("-" * 80)
        available_query = """
            SELECT id, "serialNumber", "batteryLevel", location, "lastSeen"
            FROM devices
            WHERE ("deviceType" = 'watch' OR "deviceType" = 'esp32Watch')
            AND status = 'available'
            ORDER BY "lastSeen" DESC NULLS LAST
        """
        available = await conn.fetch(available_query)

        if available:
            for i, device in enumerate(available, 1):
                last_seen = device['lastSeen']
                connection_status = "UNKNOWN"
                if last_seen:
                    time_diff = (datetime.now() - last_seen).total_seconds() / 60
                    if time_diff <= 5:
                        connection_status = "🟢 CONNECTED"
                    elif time_diff <= 60:
                        connection_status = "🟡 RECENTLY SEEN"
                    else:
                        connection_status = "🔴 OFFLINE"

                print(f"{i}. {device['id']}")
                print(f"   Serial: {device['serialNumber']}")
                print(f"   Battery: {device['batteryLevel'] or 'N/A'}%")
                print(f"   Location: {device['location'] or 'N/A'}")
                print(f"   Status: {connection_status}")
                print(f"   Last Seen: {last_seen or 'Never'}")
                print()
        else:
            print("  ⚠️  No available watches in pool")

        # 4. Check assigned watches
        print("="*80)
        print("📍 ASSIGNED WATCHES (Currently in Use)")
        print("-" * 80)
        assigned_query = """
            SELECT
                d.id,
                d."serialNumber",
                d."batteryLevel",
                d."lastSeen",
                da."patientId",
                p."firstName",
                p."lastName",
                p."roomNumber",
                p."bedNumber",
                da."assignedAt",
                da."assignedBy"
            FROM devices d
            JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
            JOIN patients p ON da."patientId" = p.id
            WHERE d."deviceType" = 'watch' OR d."deviceType" = 'esp32Watch'
            ORDER BY p."roomNumber", p."bedNumber"
        """
        assigned = await conn.fetch(assigned_query)

        if assigned:
            for i, device in enumerate(assigned, 1):
                last_seen = device['lastSeen']
                connection_status = "UNKNOWN"
                if last_seen:
                    time_diff = (datetime.now() - last_seen).total_seconds() / 60
                    if time_diff <= 5:
                        connection_status = "🟢 CONNECTED"
                    elif time_diff <= 60:
                        connection_status = "🟡 RECENTLY SEEN"
                    else:
                        connection_status = "🔴 OFFLINE"

                print(f"{i}. {device['id']}")
                print(f"   Serial: {device['serialNumber']}")
                print(f"   Patient: {device['firstName']} {device['lastName']} ({device['patientId']})")
                print(f"   Location: Room {device['roomNumber']}, Bed {device['bedNumber']}")
                print(f"   Battery: {device['batteryLevel'] or 'N/A'}%")
                print(f"   Status: {connection_status}")
                print(f"   Assigned At: {device['assignedAt']}")
                print(f"   Assigned By: {device['assignedBy']}")
                print()
        else:
            print("  No watches currently assigned")

        # 5. Check other device types
        print("="*80)
        print("🖥️  OTHER DEVICES")
        print("-" * 80)
        other_query = """
            SELECT "deviceType", id, "serialNumber", status, location
            FROM devices
            WHERE "deviceType" NOT IN ('watch', 'esp32Watch')
            ORDER BY "deviceType", id
        """
        other_devices = await conn.fetch(other_query)

        if other_devices:
            current_type = None
            for device in other_devices:
                if current_type != device['deviceType']:
                    current_type = device['deviceType']
                    print(f"\n{current_type.upper()}:")
                print(f"  - {device['id']} ({device['serialNumber'] or 'No Serial'}) - {device['status']} - {device['location'] or 'No Location'}")
        else:
            print("  No other devices found")

        # 6. Device health statistics
        print("\n" + "="*80)
        print("📈 DEVICE HEALTH STATISTICS")
        print("-" * 80)

        total_devices = await conn.fetchval('SELECT COUNT(*) FROM devices')
        total_watches = await conn.fetchval(
            "SELECT COUNT(*) FROM devices WHERE \"deviceType\" IN ('watch', 'esp32Watch')"
        )
        available_watches = await conn.fetchval(
            "SELECT COUNT(*) FROM devices WHERE \"deviceType\" IN ('watch', 'esp32Watch') AND status = 'available'"
        )
        assigned_watches = await conn.fetchval(
            "SELECT COUNT(*) FROM devices WHERE \"deviceType\" IN ('watch', 'esp32Watch') AND status = 'assigned'"
        )

        print(f"Total Devices in System: {total_devices}")
        print(f"Total Watches: {total_watches}")
        print(f"Available Watches: {available_watches}")
        print(f"Assigned Watches: {assigned_watches}")
        print(f"Utilization Rate: {(assigned_watches / total_watches * 100) if total_watches > 0 else 0:.1f}%")

        print("\n" + "="*80)
        print("✅ DEVICE POOL CHECK COMPLETE")
        print("="*80 + "\n")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_devices())
