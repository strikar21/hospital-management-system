"""
Apply Migration 015: Patient Alerts Table (using psycopg2)
Creates table for persistent alert storage (fixes mqtt_service.py:306 TODO)
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
import os
from datetime import datetime

# Database connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'hospitaldb',
    'user': 'hospital_user',
    'password': 'hospital123'
}

def print_status(message, status='INFO'):
    """Print formatted status message"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    prefix = {
        'INFO': '   ',
        'SUCCESS': '[OK]  ',
        'ERROR': '[ERR] ',
        'WARNING': '[WARN]'
    }.get(status, '   ')
    print(f"[{timestamp}] {prefix}{message}")

def apply_migration():
    """Apply migration 015"""
    conn = None
    try:
        # Connect to database
        print_status("Connecting to PostgreSQL database...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        print_status("Connected successfully", 'SUCCESS')

        # Read migration SQL file
        migration_file = os.path.join(
            os.path.dirname(__file__),
            'migrations',
            '015_create_patient_alerts_table.sql'
        )

        print_status(f"Reading migration file: {migration_file}")
        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        # Apply migration
        print_status("Applying migration 015...")
        cursor.execute(migration_sql)
        print_status("Migration applied successfully", 'SUCCESS')

        # Verify table created
        print_status("\nVerifying table created:")
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'patient_alerts'
        """)
        if cursor.fetchone()[0] == 1:
            print_status("  patient_alerts table created", 'SUCCESS')
        else:
            print_status("  patient_alerts table NOT found", 'ERROR')
            return False

        # Show table structure
        print_status("\nPatient Alerts table structure:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'patient_alerts'
            ORDER BY ordinal_position
        """)
        for row in cursor.fetchall():
            col_name, data_type, is_nullable, max_length = row
            nullable = "NULL" if is_nullable == 'YES' else "NOT NULL"
            length_info = f"({max_length})" if max_length else ""
            print_status(f"  - {col_name}: {data_type}{length_info} ({nullable})")

        # Verify indexes
        print_status("\nVerifying indexes created:")
        expected_indexes = [
            'idx_patient_alerts_patient',
            'idx_patient_alerts_status',
            'idx_patient_alerts_timestamp',
            'idx_patient_alerts_severity',
            'idx_patient_alerts_patient_status'
        ]

        for index_name in expected_indexes:
            cursor.execute("""
                SELECT COUNT(*) FROM pg_indexes
                WHERE indexname = %s
            """, (index_name,))
            if cursor.fetchone()[0] == 1:
                print_status(f"  {index_name}", 'SUCCESS')
            else:
                print_status(f"  {index_name} NOT found", 'WARNING')

        # Verify foreign keys
        print_status("\nVerifying foreign key constraints:")
        cursor.execute("""
            SELECT
                con.conname AS constraint_name,
                pg_get_constraintdef(con.oid) AS constraint_def
            FROM pg_constraint con
            INNER JOIN pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'patient_alerts'
              AND con.contype = 'f'
            ORDER BY con.conname
        """)
        fk_constraints = cursor.fetchall()
        if fk_constraints:
            for fk in fk_constraints:
                print_status(f"  {fk[0]}: {fk[1][:50]}...", 'SUCCESS')
        else:
            print_status("  No foreign key constraints found", 'WARNING')

        # Verify trigger
        print_status("\nVerifying triggers:")
        cursor.execute("""
            SELECT trigger_name
            FROM information_schema.triggers
            WHERE event_object_table = 'patient_alerts'
        """)
        triggers = cursor.fetchall()
        if triggers:
            for trig in triggers:
                print_status(f"  {trig[0]}", 'SUCCESS')
        else:
            print_status("  No triggers found", 'WARNING')

        print_status("\n" + "="*60, 'SUCCESS')
        print_status("Migration 015 completed successfully!", 'SUCCESS')
        print_status("="*60, 'SUCCESS')
        print_status("\nNext steps:")
        print_status("  1. Implement alert storage in mqtt_service.py:306")
        print_status("  2. Add GET /patients/{id}/alerts endpoint if missing")
        print_status("  3. Test alert persistence and acknowledgment")

        return True

    except Exception as e:
        print_status(f"Error applying migration: {str(e)}", 'ERROR')
        import traceback
        traceback.print_exc()
        return False

    finally:
        if conn:
            conn.close()
            print_status("Database connection closed")

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
