#!/usr/bin/env python3
"""
Patient Database Cleanup Script
Removes test patients and keeps only 4 well-detailed patients with complete medical histories.

Patients to keep:
1. Thomas Brown (081a5294-da91-4c74-bb8a-e5062f5851dd) - 2 medications, 2 patient notes, detailed medical history
2. Jennifer Lee (6b851aa6-e564-40b6-963f-e1a5efdf024c) - 2 medications, 2 patient notes, detailed medical history
3. Robert Anderson (7163182b-5d6e-412d-93d9-28ecfd86cc6e) - 2 patient notes, detailed medical history
4. William Johnson (9b1f89f3-577d-451e-983d-e6a97f937d76) - 2 patient notes, detailed medical history
"""

import psycopg2
import sys
from datetime import datetime

# Database connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'hospitaldb',
    'user': 'hospital_user',
    'password': 'hospital123'
}

# Patient IDs to keep (these have the most complete medical records)
PATIENTS_TO_KEEP = [
    '081a5294-da91-4c74-bb8a-e5062f5851dd',  # Thomas Brown
    '6b851aa6-e564-40b6-963f-e1a5efdf024c',  # Jennifer Lee
    '7163182b-5d6e-412d-93d9-28ecfd86cc6e',  # Robert Anderson
    '9b1f89f3-577d-451e-983d-e6a97f937d76'   # William Johnson
]

def connect_to_database():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def get_patient_count(cursor):
    """Get current patient count"""
    cursor.execute("SELECT COUNT(*) FROM patients")
    return cursor.fetchone()[0]

def get_patients_to_delete(cursor):
    """Get list of patient IDs to delete"""
    placeholders = ','.join(['%s'] * len(PATIENTS_TO_KEEP))
    cursor.execute(f"""
        SELECT id, "firstName", "lastName"
        FROM patients
        WHERE id NOT IN ({placeholders})
    """, PATIENTS_TO_KEEP)
    return cursor.fetchall()

def delete_related_records(cursor, patient_ids_to_delete):
    """Delete all related records for patients being removed"""
    if not patient_ids_to_delete:
        return

    placeholders = ','.join(['%s'] * len(patient_ids_to_delete))

    # Tables that reference patient IDs
    related_tables = [
        'medicationadministrations',
        'medications',
        'investigations',
        'patientnotes',
        'therapysessions',
        'casesheetentries',
        'deviceassignments',
        'therapy',
        'admissionrecommendations'  # if it references patients
    ]

    deleted_counts = {}

    for table in related_tables:
        try:
            # Check if table exists and has patientId column
            cursor.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table}' AND column_name = 'patientId'
            """)

            if cursor.fetchone():
                cursor.execute(f"""
                    DELETE FROM {table} WHERE "patientId" IN ({placeholders})
                """, patient_ids_to_delete)
                deleted_counts[table] = cursor.rowcount
                if cursor.rowcount > 0:
                    print(f"  Deleted {cursor.rowcount} records from {table}")
        except psycopg2.Error as e:
            print(f"  Warning: Could not clean table {table}: {e}")

    return deleted_counts

def main():
    """Main cleanup function"""
    print("Hospital Patient Database Cleanup")
    print("=" * 50)

    # Connect to database
    conn = connect_to_database()
    cursor = conn.cursor()

    try:
        # Get initial count
        initial_count = get_patient_count(cursor)
        print(f"Current patient count: {initial_count}")

        # Get patients to delete
        patients_to_delete = get_patients_to_delete(cursor)
        patient_ids_to_delete = [p[0] for p in patients_to_delete]

        print(f"Keeping 4 patients with detailed medical histories")
        print(f"Will delete {len(patients_to_delete)} patients")

        if len(patients_to_delete) == 0:
            print("No patients to delete. Database already cleaned.")
            return

        # Show some of the patients being deleted
        print(f"Sample patients being deleted:")
        for patient in patients_to_delete[:10]:  # Show first 10
            print(f"   - {patient[1]} {patient[2]} (ID: {patient[0][:8]}...)")

        if len(patients_to_delete) > 10:
            print(f"   ... and {len(patients_to_delete) - 10} more")

        # Auto-confirm deletion (non-interactive mode)
        print(f"\nProceeding with deletion of {len(patients_to_delete)} patients...")

        print(f"\nStarting cleanup...")

        # Delete related records first
        print(f"Cleaning related records...")
        delete_related_records(cursor, patient_ids_to_delete)

        # Delete patients
        print(f"Deleting patients...")
        placeholders = ','.join(['%s'] * len(patient_ids_to_delete))
        cursor.execute(f"""
            DELETE FROM patients WHERE id IN ({placeholders})
        """, patient_ids_to_delete)

        deleted_patients = cursor.rowcount
        print(f"  Deleted {deleted_patients} patients")

        # Commit transaction
        conn.commit()

        # Get final count
        final_count = get_patient_count(cursor)
        print(f"\nCleanup completed successfully!")
        print(f"Final patient count: {final_count}")
        print(f"Total patients deleted: {initial_count - final_count}")

        # Show kept patients
        print(f"\nPatients kept in database:")
        cursor.execute(f"""
            SELECT "firstName", "lastName", "medicalHistory"
            FROM patients
            WHERE id IN ({','.join(['%s'] * len(PATIENTS_TO_KEEP))})
        """, PATIENTS_TO_KEEP)

        for patient in cursor.fetchall():
            history = patient[2][:60] + "..." if patient[2] and len(patient[2]) > 60 else patient[2]
            print(f"   {patient[0]} {patient[1]} - {history}")

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\nOperation cancelled by user")
        conn.rollback()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()