"""
Day 1 Migration Tests - Automated Testing for FK Constraints
"""
import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings


class TestDay1Migrations:
    """Test Day 1 foreign key constraint migrations"""

    def __init__(self):
        self.conn = None
        self.results = []

    async def connect(self):
        """Connect to database"""
        try:
            self.conn = await asyncpg.connect(settings.databaseUrl)
            print("[PASS] Connected to database successfully")
            return True
        except Exception as e:
            print(f"[FAIL] Failed to connect to database: {e}")
            return False

    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
            print("[PASS] Database connection closed")

    async def apply_migration(self):
        """Apply migration 001"""
        # First check if constraints exist to avoid transaction issues
        try:
            check_query = """
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'medications'
                AND constraint_type = 'FOREIGN KEY'
            """

            constraints = await self.conn.fetch(check_query)
            constraint_names = [c['constraint_name'] for c in constraints]

            if 'fk_medications_patient' in constraint_names:
                print("[WARN] Migration already applied (constraints already exist)")
                return True

            migration_path = Path(__file__).parent.parent / "migrations" / "001_add_foreign_keys_medications.sql"

            if not migration_path.exists():
                print(f"[FAIL] Migration file not found: {migration_path}")
                return False

            with open(migration_path, 'r') as f:
                migration_sql = f.read()

            # Execute migration
            await self.conn.execute(migration_sql)
            print("[PASS] Migration 001 applied successfully")
            return True

        except Exception as e:
            error_msg = str(e)
            # Check if error is because constraints already exist
            if 'already exists' in error_msg or 'duplicate' in error_msg.lower():
                print("[WARN] Migration already applied (constraints already exist)")
                # Reconnect to clear aborted transaction
                await self.conn.close()
                self.conn = await asyncpg.connect(settings.databaseUrl)
                return True
            print(f"[FAIL] Failed to apply migration: {e}")
            return False

    async def verify_constraints_exist(self):
        """Verify FK constraints were created"""
        try:
            query = """
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'medications'
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name IN ('fk_medications_patient', 'fk_medications_prescriber', 'fk_medications_creator')
            """

            constraints = await self.conn.fetch(query)
            constraint_names = [c['constraint_name'] for c in constraints]

            expected = ['fk_medications_patient', 'fk_medications_prescriber', 'fk_medications_creator']

            for expected_constraint in expected:
                if expected_constraint in constraint_names:
                    print(f"[PASS] Constraint exists: {expected_constraint}")
                else:
                    print(f"[FAIL] Constraint missing: {expected_constraint}")
                    return False

            return True

        except Exception as e:
            print(f"[FAIL] Failed to verify constraints: {e}")
            return False

    async def test_invalid_patient_fk(self):
        """Test: Cannot insert medication with invalid patient ID"""
        try:
            # Get a valid staff ID first
            staff = await self.conn.fetchrow("SELECT id FROM staff LIMIT 1")
            if not staff:
                print("[WARN]  No staff found, creating test staff")
                await self.conn.execute("""
                    INSERT INTO staff (id, role, email, "firstName", "lastName", "createdAt", "updatedAt")
                    VALUES ('TEST_STAFF_FK', 'Doctor', 'test@test.com', 'Test', 'Staff', NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                """)
                staff_id = 'TEST_STAFF_FK'
            else:
                staff_id = staff['id']

            # Try to insert with invalid patient - should FAIL
            try:
                await self.conn.execute("""
                    INSERT INTO medications ("patientId", name, dosage, frequency, route, status, "prescribedBy", "createdBy", "createdAt", "updatedAt")
                    VALUES ('INVALID_PATIENT_ID', 'Aspirin', '500mg', 'BID', 'PO', 'active', $1, $1, NOW(), NOW())
                """, staff_id)

                print("[FAIL] Test FAILED: Should not allow invalid patient ID")
                return False

            except asyncpg.exceptions.ForeignKeyViolationError as e:
                if 'fk_medications_patient' in str(e):
                    print("[PASS] Test PASSED: FK constraint blocked invalid patient ID")
                    return True
                else:
                    print(f"[FAIL] Test FAILED: Wrong FK error: {e}")
                    return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    async def test_invalid_prescriber_fk(self):
        """Test: Cannot insert medication with invalid prescriber ID"""
        try:
            # Get a valid patient ID
            patient = await self.conn.fetchrow("SELECT id FROM patients LIMIT 1")
            if not patient:
                print("[WARN]  No patients found, creating test patient")
                await self.conn.execute("""
                    INSERT INTO patients (id, "firstName", "lastName", "dateOfBirth", gender, status, "createdAt", "updatedAt")
                    VALUES ('TEST_PATIENT_FK', 'Test', 'Patient', '1990-01-01', 'Male', 'active', NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                """)
                patient_id = 'TEST_PATIENT_FK'
            else:
                patient_id = patient['id']

            # Try to insert with invalid prescriber - should FAIL
            try:
                await self.conn.execute("""
                    INSERT INTO medications ("patientId", name, dosage, frequency, route, status, "prescribedBy", "createdBy", "createdAt", "updatedAt")
                    VALUES ($1, 'Aspirin', '500mg', 'BID', 'PO', 'active', 'INVALID_STAFF_ID', 'INVALID_STAFF_ID', NOW(), NOW())
                """, patient_id)

                print("[FAIL] Test FAILED: Should not allow invalid prescriber ID")
                return False

            except asyncpg.exceptions.ForeignKeyViolationError as e:
                if 'fk_medications_prescriber' in str(e):
                    print("[PASS] Test PASSED: FK constraint blocked invalid prescriber ID")
                    return True
                else:
                    print(f"[FAIL] Test FAILED: Wrong FK error: {e}")
                    return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    async def test_cascade_delete(self):
        """Test: Deleting patient cascades to delete medications"""
        try:
            # Create test patient
            test_patient_id = 'TEST_CASCADE_PATIENT'
            await self.conn.execute("""
                INSERT INTO patients (id, "firstName", "lastName", "dateOfBirth", gender, status, "createdAt", "updatedAt")
                VALUES ($1, 'Cascade', 'Test', '1990-01-01', 'Male', 'active', NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET status = 'active'
            """, test_patient_id)

            # Get a valid staff ID
            staff = await self.conn.fetchrow("SELECT id FROM staff LIMIT 1")
            staff_id = staff['id'] if staff else 'TEST_STAFF_FK'

            # Create medication for test patient
            await self.conn.execute("""
                INSERT INTO medications ("patientId", name, dosage, frequency, route, status, "prescribedBy", "createdBy", "createdAt", "updatedAt")
                VALUES ($1, 'Cascade Test Med', '100mg', 'QD', 'PO', 'active', $2, $2, NOW(), NOW())
            """, test_patient_id, staff_id)

            # Verify medication exists
            med_count_before = await self.conn.fetchval(
                'SELECT COUNT(*) FROM medications WHERE "patientId" = $1', test_patient_id
            )

            if med_count_before == 0:
                print("[FAIL] Test FAILED: Medication was not created")
                return False

            # Delete patient
            await self.conn.execute('DELETE FROM patients WHERE id = $1', test_patient_id)

            # Verify medication was cascade deleted
            med_count_after = await self.conn.fetchval(
                'SELECT COUNT(*) FROM medications WHERE "patientId" = $1', test_patient_id
            )

            if med_count_after == 0:
                print("[PASS] Test PASSED: Medication was cascade deleted with patient")
                return True
            else:
                print(f"[FAIL] Test FAILED: Medication still exists (count: {med_count_after})")
                return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    async def test_restrict_delete(self):
        """Test: Cannot delete staff who prescribed medications"""
        try:
            # Create test patient and staff
            test_patient_id = 'TEST_RESTRICT_PATIENT'
            test_staff_id = 'TEST_RESTRICT_STAFF'

            await self.conn.execute("""
                INSERT INTO patients (id, "firstName", "lastName", "dateOfBirth", gender, status, "createdAt", "updatedAt")
                VALUES ($1, 'Restrict', 'Test', '1990-01-01', 'Male', 'active', NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET status = 'active'
            """, test_patient_id)

            await self.conn.execute("""
                INSERT INTO staff (id, role, email, "firstName", "lastName", "createdAt", "updatedAt")
                VALUES ($1, 'Doctor', 'restrict@test.com', 'Restrict', 'Test', NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET role = 'Doctor'
            """, test_staff_id)

            # Create medication prescribed by test staff
            await self.conn.execute("""
                INSERT INTO medications ("patientId", name, dosage, frequency, route, status, "prescribedBy", "createdBy", "createdAt", "updatedAt")
                VALUES ($1, 'Restrict Test Med', '100mg', 'QD', 'PO', 'active', $2, $2, NOW(), NOW())
            """, test_patient_id, test_staff_id)

            # Try to delete staff - should FAIL
            try:
                await self.conn.execute('DELETE FROM staff WHERE id = $1', test_staff_id)
                print("[FAIL] Test FAILED: Should not allow deleting staff who prescribed medications")
                return False

            except asyncpg.exceptions.ForeignKeyViolationError as e:
                if 'fk_medications_prescriber' in str(e):
                    print("[PASS] Test PASSED: FK constraint prevented deleting prescriber")
                    # Cleanup: delete patient (will cascade delete medication)
                    await self.conn.execute('DELETE FROM patients WHERE id = $1', test_patient_id)
                    # Now can delete staff
                    await self.conn.execute('DELETE FROM staff WHERE id = $1', test_staff_id)
                    return True
                else:
                    print(f"[FAIL] Test FAILED: Wrong FK error: {e}")
                    return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    async def cleanup(self):
        """Clean up test data"""
        try:
            await self.conn.execute("DELETE FROM patients WHERE id LIKE 'TEST_%'")
            await self.conn.execute("DELETE FROM staff WHERE id LIKE 'TEST_%'")
            print("[PASS] Test data cleaned up")
        except Exception as e:
            print(f"[WARN]  Cleanup warning: {e}")

    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("DAY 1 MIGRATION TESTS - FOREIGN KEY CONSTRAINTS")
        print("="*60 + "\n")

        # Connect to database
        if not await self.connect():
            return False

        try:
            # Apply migration
            print("\n--- Applying Migration ---")
            if not await self.apply_migration():
                return False

            # Verify constraints
            print("\n--- Verifying Constraints ---")
            if not await self.verify_constraints_exist():
                return False

            # Run FK tests
            print("\n--- Testing FK Constraints ---")

            print("\nTest 1: Invalid Patient FK")
            test1 = await self.test_invalid_patient_fk()

            print("\nTest 2: Invalid Prescriber FK")
            test2 = await self.test_invalid_prescriber_fk()

            print("\nTest 3: CASCADE Delete")
            test3 = await self.test_cascade_delete()

            print("\nTest 4: RESTRICT Delete")
            test4 = await self.test_restrict_delete()

            # Cleanup
            print("\n--- Cleanup ---")
            await self.cleanup()

            # Summary
            print("\n" + "="*60)
            print("TEST SUMMARY")
            print("="*60)
            all_passed = test1 and test2 and test3 and test4

            if all_passed:
                print("[PASS] ALL TESTS PASSED")
                print("\nDay 1 implementation is verified and working correctly!")
                print("Safe to proceed to Day 2.")
            else:
                print("[FAIL] SOME TESTS FAILED")
                print("\nPlease review the failures above before proceeding.")
                print("Day 1 needs fixes before moving to Day 2.")

            print("="*60 + "\n")

            return all_passed

        finally:
            await self.close()


async def main():
    """Main test runner"""
    tester = TestDay1Migrations()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
