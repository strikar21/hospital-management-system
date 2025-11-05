"""
Diagnostic script to check why vitals data is coming through but not displaying
"""
import asyncpg
import asyncio
import json

async def diagnose():
    conn = await asyncpg.connect(
        'postgresql://hospital_user:hospital123@localhost:5432/hospitaldb'
    )

    print('\n' + '='*100)
    print('DIAGNOSTIC: DATA FLOW ANALYSIS')
    print('='*100)

    # Step 1: Check what tables exist
    print('\n[1] CHECKING AVAILABLE TABLES...')
    tables_query = "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    tables = await conn.fetch(tables_query)
    print(f'   Found {len(tables)} tables:')
    for table in tables:
        print(f'   - {table["tablename"]}')

    # Step 2: Check if vitals table exists (any variant)
    vitals_tables = [t["tablename"] for t in tables if 'vital' in t["tablename"].lower()]
    print(f'\n[2] VITALS-RELATED TABLES:')
    if vitals_tables:
        for vt in vitals_tables:
            print(f'   - {vt}')
    else:
        print('   *** NO VITALS TABLES FOUND ***')

    # Step 3: Check patients table
    print('\n[3] CHECKING PATIENTS DATA...')
    patients_query = "SELECT id, firstname, lastname FROM patients LIMIT 5"
    try:
        patients = await conn.fetch(patients_query)
        print(f'   Found {len(patients)} patients:')
        for p in patients:
            print(f'   - {p["id"]}: {p["firstname"]} {p["lastname"]}')
    except Exception as e:
        print(f'   ERROR: {e}')

    # Step 4: Check deviceassignments
    print('\n[4] CHECKING DEVICE ASSIGNMENTS...')
    assign_query = "SELECT patientid, deviceid, assignedat FROM deviceassignments WHERE unassignedat IS NULL"
    try:
        assignments = await conn.fetch(assign_query)
        print(f'   Found {len(assignments)} active assignments:')
        for a in assignments:
            print(f'   - Patient {a["patientid"]} → Device {a["deviceid"]} (assigned: {a["assignedat"]})')
    except Exception as e:
        print(f'   ERROR: {e}')

    # Step 5: Check if vitals are being stored
    if vitals_tables:
        for vt in vitals_tables:
            print(f'\n[5] CHECKING {vt.upper()} TABLE...')
            try:
                # Get column names first
                cols_query = f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{vt}'
                    ORDER BY ordinal_position
                """
                cols = await conn.fetch(cols_query)
                print(f'   Columns: {", ".join([c["column_name"] for c in cols])}')

                # Get row count
                count_query = f"SELECT COUNT(*) as count FROM {vt}"
                count = await conn.fetchval(count_query)
                print(f'   Total rows: {count}')

                # Get latest rows
                if count > 0:
                    latest_query = f"SELECT * FROM {vt} ORDER BY time DESC LIMIT 3"
                    latest = await conn.fetch(latest_query)
                    print(f'   Latest {len(latest)} rows:')
                    for row in latest:
                        print(f'     {dict(row)}')
            except Exception as e:
                print(f'   ERROR: {e}')

    await conn.close()
    print('\n' + '='*100)
    print('DIAGNOSTIC COMPLETE')
    print('='*100 + '\n')

if __name__ == '__main__':
    asyncio.run(diagnose())
