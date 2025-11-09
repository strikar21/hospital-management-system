"""
Quick script to check if ECG/EEG analysis is working
"""
import asyncio
import asyncpg

async def check_analysis():
    # Connect to TimescaleDB
    conn = await asyncpg.connect(
        host='localhost',
        port=5433,
        user='hospital_user',
        password='hospital123',
        database='hospitaltimescale'
    )

    try:
        # Get last 5 vitals records
        rows = await conn.fetch("""
            SELECT time, "patientId", "deviceId", mode, "heartRate",
                   "rrInterval", "qrsDuration", "qtInterval", rhythm,
                   "alphaPower", "betaPower", "dominantFrequency", "seizureActivity"
            FROM vitals_realtime
            ORDER BY time DESC
            LIMIT 5
        """)

        print(f"\nLast 5 Vitals Records:\n")
        print(f"{'Time':<25} {'Mode':<6} {'HR':<6} {'RR Int':<8} {'QRS':<8} {'Rhythm':<15} {'Alpha':<8}")
        print("=" * 100)

        ecg_analysis_count = 0
        eeg_analysis_count = 0

        for row in rows:
            time_str = row['time'].strftime('%Y-%m-%d %H:%M:%S')
            mode = row['mode'] or '??'
            hr = row['heartRate'] or 0
            rr = row['rrInterval'] if row['rrInterval'] is not None else 'NULL'
            qrs = row['qrsDuration'] if row['qrsDuration'] is not None else 'NULL'
            rhythm = row['rhythm'] or 'NULL'
            alpha = row['alphaPower'] if row['alphaPower'] is not None else 'NULL'

            print(f"{time_str:<25} {mode:<6} {hr:<6} {str(rr):<8} {str(qrs):<8} {rhythm:<15} {str(alpha):<8}")

            # Count analysis
            if mode == 'ecg' and row['rrInterval'] is not None:
                ecg_analysis_count += 1
            if mode == 'eeg' and row['alphaPower'] is not None:
                eeg_analysis_count += 1

        print("\n" + "=" * 100)
        print(f"\nAnalysis Coverage:")
        print(f"  ECG Analysis: {ecg_analysis_count}/5 records have analysis data")
        print(f"  EEG Analysis: {eeg_analysis_count}/5 records have analysis data")

        if ecg_analysis_count == 0 and eeg_analysis_count == 0:
            print("\nNO ANALYSIS DATA FOUND - Analysis is NOT running!")
        else:
            print(f"\nAnalysis IS running!")

    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(check_analysis())
