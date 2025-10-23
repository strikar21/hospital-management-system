"""
Apply Migration 013: Certificate Provisioning Infrastructure
Creates tables for device certificate management and provisioning codes
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
    """Apply migration 013"""
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
            '013_certificate_provisioning.sql'
        )

        print_status(f"Reading migration file: {migration_file}")
        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        # Apply migration
        print_status("Applying migration 013...")
        cursor.execute(migration_sql)
        print_status("Migration applied successfully", 'SUCCESS')

        # Verify tables created
        print_status("\nVerifying tables created:")

        # Check provisioning_codes table
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'provisioning_codes'
        """)
        if cursor.fetchone()[0] == 1:
            print_status("  ✓ provisioning_codes table created", 'SUCCESS')
        else:
            print_status("  ✗ provisioning_codes table NOT found", 'ERROR')
            return False

        # Check device_certificates table
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'device_certificates'
        """)
        if cursor.fetchone()[0] == 1:
            print_status("  ✓ device_certificates table created", 'SUCCESS')
        else:
            print_status("  ✗ device_certificates table NOT found", 'ERROR')
            return False

        # Verify indexes
        print_status("\nVerifying indexes created:")
        expected_indexes = [
            'idx_provisioning_codes_active',
            'idx_provisioning_codes_technician',
            'idx_device_certificates_expiry',
            'idx_device_certificates_revoked',
            'idx_device_certificates_device',
            'idx_device_certificates_mac'
        ]

        for index_name in expected_indexes:
            cursor.execute("""
                SELECT COUNT(*) FROM pg_indexes
                WHERE indexname = %s
            """, (index_name,))
            if cursor.fetchone()[0] == 1:
                print_status(f"  ✓ {index_name}", 'SUCCESS')
            else:
                print_status(f"  ✗ {index_name} NOT found", 'WARNING')

        # Show table structure
        print_status("\nProvisioning Codes table structure:")
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'provisioning_codes'
            ORDER BY ordinal_position
        """)
        for row in cursor.fetchall():
            col_name, data_type, max_length = row
            length_info = f"({max_length})" if max_length else ""
            print_status(f"  - {col_name}: {data_type}{length_info}")

        print_status("\nDevice Certificates table structure:")
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'device_certificates'
            ORDER BY ordinal_position
        """)
        for row in cursor.fetchall():
            col_name, data_type, max_length = row
            length_info = f"({max_length})" if max_length else ""
            print_status(f"  - {col_name}: {data_type}{length_info}")

        print_status("\n" + "="*60, 'SUCCESS')
        print_status("Migration 013 completed successfully!", 'SUCCESS')
        print_status("="*60, 'SUCCESS')

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
