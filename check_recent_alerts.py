import asyncio
import asyncpg
from datetime import datetime

async def check():
    conn = await asyncpg.connect(
        host='localhost', port=5432, user='hospital_user',
        password='hospital123', database='hospitaldb'
    )
    
    try:
        # Check recent alerts
        alerts = await conn.fetch("""
            SELECT id, "patientId", type, severity, message, 
                   source, "alertTimestamp", status
            FROM patient_alerts
            WHERE "createdAt" > NOW() - INTERVAL '10 minutes'
            ORDER BY "alertTimestamp" DESC
            LIMIT 10
        """)
        
        print(f"\n=== RECENT ALERTS (Last 10 minutes) ===")
        print(f"Found {len(alerts)} alerts\n")
        
        if alerts:
            for alert in alerts:
                print(f"[{alert['severity'].upper()}] {alert['message']}")
                print(f"  Patient: {alert['patientId'][:8]}...")
                print(f"  Source: {alert['source']}")
                print(f"  Type: {alert['type']}")
                print(f"  Status: {alert['status']}")
                print(f"  Time: {alert['alertTimestamp']}")
                print()
        else:
            print("No alerts generated yet.")
            print("\nThis is NORMAL if vitals are within normal ranges.")
            print("AlertPipeline only generates alerts when thresholds are breached.")
        
    finally:
        await conn.close()

asyncio.run(check())
