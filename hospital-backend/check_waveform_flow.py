#!/usr/bin/env python3
"""
Quick check for waveform data flow
"""
import psycopg2
from datetime import datetime, timedelta

def check_waveforms():
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5433,  # TimescaleDB container port
            database='hospitaltimescale',  # TimescaleDB database (not hospitaldb)
            user='hospital_user',
            password='hospital123'
        )
        cur = conn.cursor()

        print("=" * 80)
        print("WAVEFORM DATA FLOW CHECK")
        print("=" * 80)

        # Check vitals (last 10 seconds)
        print("\n1. VITALS (last 10 seconds):")
        cur.execute("""
            SELECT "deviceId", "patientId", time, "heartRate", "oxygenSaturation"
            FROM vitals_realtime
            WHERE time > NOW() - INTERVAL '10 seconds'
            ORDER BY time DESC
            LIMIT 5
        """)
        vitals = cur.fetchall()

        if vitals:
            for v in vitals:
                print(f"   Device: {v[0]}, Patient: {v[1]}, Time: {v[2]}, HR: {v[3]}, SpO2: {v[4]}")
        else:
            print("   No vitals in last 10 seconds")

        # Check waveforms (last 10 seconds)
        print("\n2. WAVEFORMS (last 10 seconds):")
        cur.execute("""
            SELECT "deviceId", "patientId", time, mode
            FROM waveform_snapshots
            WHERE time > NOW() - INTERVAL '10 seconds'
            ORDER BY time DESC
            LIMIT 5
        """)
        waveforms = cur.fetchall()

        if waveforms:
            print(f"   FOUND {len(waveforms)} WAVEFORM SNAPSHOTS!")
            for w in waveforms:
                print(f"   Device: {w[0]}, Patient: {w[1]}, Time: {w[2]}, Mode: {w[3]}")
        else:
            print("   No waveforms in last 10 seconds")

        # Total counts
        print("\n3. TOTAL COUNTS:")
        cur.execute("SELECT COUNT(*) FROM vitals_realtime")
        vitals_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM waveform_snapshots")
        waveform_count = cur.fetchone()[0]

        print(f"   Total vitals: {vitals_count}")
        print(f"   Total waveforms: {waveform_count}")

        # Check most recent waveform
        if waveform_count > 0:
            print("\n4. MOST RECENT WAVEFORM:")
            cur.execute("""
                SELECT "deviceId", "patientId", time, mode, "sampleRate", duration
                FROM waveform_snapshots
                ORDER BY time DESC
                LIMIT 1
            """)
            latest = cur.fetchone()
            print(f"   Device: {latest[0]}")
            print(f"   Patient: {latest[1]}")
            print(f"   Time: {latest[2]}")
            print(f"   Mode: {latest[3]}")
            print(f"   Sample Rate: {latest[4]} Hz")
            print(f"   Duration: {latest[5]} seconds")

        print("\n" + "=" * 80)

        if waveform_count > 0:
            print("SUCCESS: Waveforms are being stored!")
        else:
            print("ISSUE: No waveforms in database yet")

        print("=" * 80)

        cur.close()
        conn.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_waveforms()
