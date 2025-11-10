import asyncio
import asyncpg
from datetime import datetime

async def check_vitals():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='hospital_user',
        password='hospital123',
        database='hospitaldb'
    )
    
    try:
        # Check all devices and their lastSeen timestamps
        devices = await conn.fetch("""
            SELECT id, "deviceType", name, status, "lastSeen", "batteryLevel"
            FROM devices
            ORDER BY "lastSeen" DESC NULLS LAST
            LIMIT 10
        """)
        
        print("\n=== ALL DEVICES (Last 10, sorted by lastSeen) ===")
        now = datetime.now(devices[0]['lastSeen'].tzinfo if devices and devices[0]['lastSeen'] else None)
        
        for device in devices:
            last_seen = device['lastSeen']
            if last_seen:
                age = now - last_seen
                age_sec = int(age.total_seconds())
                if age_sec < 60:
                    age_str = f"{age_sec}s ago"
                    status = "CONNECTED"
                elif age_sec < 300:
                    age_str = f"{age_sec//60}m ago"
                    status = "RECENT"
                else:
                    age_str = f"{age_sec//3600}h ago" if age_sec > 3600 else f"{age_sec//60}m ago"
                    status = "OLD"
            else:
                age_str = "NEVER"
                status = "NEVER"
            
            print(f"[{status}] {device['id']}: {device['name']}")
            print(f"        Status: {device['status']}, Battery: {device['batteryLevel']}%")
            print(f"        Last Seen: {last_seen} ({age_str})")
        
        # Check TimescaleDB for recent vitals
        try:
            ts_conn = await asyncpg.connect(
                host='localhost',
                port=5433,
                user='hospital_user',
                password='hospital123',
                database='hospitaltimescale'
            )
            
            recent_vitals = await ts_conn.fetch("""
                SELECT "patientId", "deviceId", time, "heartRate", "oxygenSaturation"
                FROM vitals_realtime
                WHERE time > NOW() - INTERVAL '5 minutes'
                ORDER BY time DESC
                LIMIT 10
            """)
            
            print("\n=== RECENT VITALS (Last 5 minutes in TimescaleDB) ===")
            if recent_vitals:
                print(f"Found {len(recent_vitals)} vitals in last 5 minutes:")
                for v in recent_vitals:
                    age = now - v['time']
                    age_str = f"{int(age.total_seconds())}s ago"
                    print(f"  Patient: {v['patientId'][:8]}..., Device: {v['deviceId']}")
                    print(f"  Time: {v['time']} ({age_str})")
                    print(f"  HR: {v['heartRate']}, SpO2: {v['oxygenSaturation']}")
            else:
                print("NO vitals in last 5 minutes!")
                print("\nThis means: Backend MQTT service is NOT processing vitals")
                print("            OR: No devices are sending data")
            
            await ts_conn.close()
        except Exception as e:
            print(f"\nCould not check TimescaleDB: {e}")
        
    finally:
        await conn.close()

asyncio.run(check_vitals())
