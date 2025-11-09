import psycopg2

conn = psycopg2.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')
cur = conn.cursor()

# Check patient data with attending physician
cur.execute("""
    SELECT
        p.id,
        p."firstName",
        p."lastName",
        p."attendingPhysician",
        CONCAT(s."firstName", ' ', s."lastName") as "attendingPhysicianName",
        s.role
    FROM patients p
    LEFT JOIN staff s ON p."attendingPhysician" = s.id
    WHERE p."dischargeDate" IS NULL
    LIMIT 10
""")

rows = cur.fetchall()
print('\n=== PATIENT ATTENDING PHYSICIAN DATA ===\n')
for row in rows:
    patient_id = row[0][:8] + '...' if row[0] else 'None'
    first_name = row[1] or ''
    last_name = row[2] or ''
    attending_id = row[3] or 'Not assigned'
    attending_name = row[4] or 'Not assigned'
    role = row[5] or ''

    print(f'Patient: {first_name} {last_name}')
    print(f'  ID: {patient_id}')
    print(f'  Attending Physician ID: {attending_id}')
    print(f'  Attending Physician Name: {attending_name}')
    print(f'  Role: {role}')
    print()

cur.close()
conn.close()
