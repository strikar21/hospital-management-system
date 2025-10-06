"""
Day 2 Migration Tests - Automated Testing for FK Constraints
Tests FK constraints for investigations, therapy, and casesheetentries tables
"""
import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings


class TestDay2Migrations:
    """Test Day 2 foreign key constraint migrations"""

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

    async def verify_constraints_exist(self):
        """Verify all Day 2 FK constraints exist"""
        try:
            print("\n--- Verifying INVESTIGATIONS Constraints ---")

            # Check investigations constraints
            inv_constraints = await self.conn.fetch("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'investigations'
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name IN ('fk_investigations_patient', 'fk_investigations_prescriber', 'fk_investigations_performer')
            """)

            inv_names = [c['constraint_name'] for c in inv_constraints]
            expected_inv = ['fk_investigations_patient', 'fk_investigations_prescriber', 'fk_investigations_performer']

            for expected in expected_inv:
                if expected in inv_names:
                    print(f"[PASS] Constraint exists: {expected}")
                else:
                    print(f"[FAIL] Constraint missing: {expected}")

            print("\n--- Verifying THERAPY Constraints ---")

            # Check therapy constraints
            therapy_constraints = await self.conn.fetch("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'therapy'
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name IN ('fk_therapy_patient', 'fk_therapy_prescriber')
            """)

            therapy_names = [c['constraint_name'] for c in therapy_constraints]
            expected_therapy = ['fk_therapy_patient', 'fk_therapy_prescriber']

            for expected in expected_therapy:
                if expected in therapy_names:
                    print(f"[PASS] Constraint exists: {expected}")
                else:
                    print(f"[FAIL] Constraint missing: {expected}")

            print("\n--- Verifying CASESHEETENTRIES Constraints ---")

            # Check casesheetentries constraints
            case_constraints = await self.conn.fetch("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'casesheetentries'
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name IN ('fk_casesheetentries_patient', 'fk_casesheetentries_creator', 'fk_casesheetentries_performer')
            """)

            case_names = [c['constraint_name'] for c in case_constraints]
            expected_case = ['fk_casesheetentries_patient', 'fk_casesheetentries_creator', 'fk_casesheetentries_performer']

            for expected in expected_case:
                if expected in case_names:
                    print(f"[PASS] Constraint exists: {expected}")
                else:
                    print(f"[FAIL] Constraint missing: {expected}")

            # Check if all exist
            all_exist = (
                all(e in inv_names for e in expected_inv) and
                all(e in therapy_names for e in expected_therapy) and
                all(e in case_names for e in expected_case)
            )

            return all_exist

        except Exception as e:
            print(f"[FAIL] Failed to verify constraints: {e}")
            return False

    async def test_investigations_invalid_prescriber(self):
        """Test: Cannot insert investigation with invalid prescriber ID"""
        try:
            # Get a valid patient ID
            patient = await self.conn.fetchrow("SELECT id FROM patients LIMIT 1")
            if not patient:
                print("[WARN]  No patients found, creating test patient")
                await self.conn.execute("""
                    INSERT INTO patients (id, "firstName", "lastName", "dateOfBirth", gender, status, "createdAt", "updatedAt")
                    VALUES ('TEST_PATIENT_DAY2', 'Test', 'Patient', '1990-01-01', 'Male', 'active', NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                """)
                patient_id = 'TEST_PATIENT_DAY2'
            else:
                patient_id = patient['id']

            # Try to insert with invalid prescriber - should FAIL
            try:
                await self.conn.execute("""
                    INSERT INTO investigations ("patientId", type, name, status, "prescribedBy", "createdAt", "updatedAt")
                    VALUES ($1, 'Blood Test', 'CBC', 'pending', 'INVALID_STAFF_ID', NOW(), NOW())
                """, patient_id)

                print("[FAIL] Test FAILED: Should not allow invalid prescriber ID")
                return False

            except asyncpg.exceptions.ForeignKeyViolationError as e:
                if 'fk_investigations_prescriber' in str(e):
                    print("[PASS] Test PASSED: FK constraint blocked invalid prescriber ID")
                    return True
                else:
                    print(f"[FAIL] Test FAILED: Wrong FK error: {e}")
                    return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    async def test_therapy_cascade_delete(self):
        """Test: Deleting patient cascades to delete therapy records"""
        try:
            # Create test patient
            test_patient_id = 'TEST_CASCADE_PATIENT_DAY2'
            await self.conn.execute("""
                INSERT INTO patients (id, "firstName", "lastName", "dateOfBirth", gender, status, "createdAt", "updatedAt")
                VALUES ($1, 'Cascade', 'Test', '1990-01-01', 'Male', 'active', NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET status = 'active'
            """, test_patient_id)

            # Get a valid staff ID
            staff = await self.conn.fetchrow("SELECT id FROM staff LIMIT 1")
            staff_id = staff['id'] if staff else 'SYSTEM'

            # Create therapy for test patient
            await self.conn.execute("""
                INSERT INTO therapy ("patientId", type, description, status, "prescribedBy", "createdAt", "updatedAt")
                VALUES ($1, 'Physical Therapy', 'Test therapy', 'active', $2, NOW(), NOW())
            """, test_patient_id, staff_id)

            # Verify therapy exists
            therapy_count_before = await self.conn.fetchval(
                'SELECT COUNT(*) FROM therapy WHERE "patientId" = $1', test_patient_id
            )

            if therapy_count_before == 0:
                print("[FAIL] Test FAILED: Therapy was not created")
                return False

            # Delete patient
            await self.conn.execute('DELETE FROM patients WHERE id = $1', test_patient_id)

            # Verify therapy was cascade deleted
            therapy_count_after = await self.conn.fetchval(
                'SELECT COUNT(*) FROM therapy WHERE "patientId" = $1', test_patient_id
            )

            if therapy_count_after == 0:
                print("[PASS] Test PASSED: Therapy was cascade deleted with patient")
                return True
            else:
                print(f"[FAIL] Test FAILED: Therapy still exists (count: {therapy_count_after})")
                return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    async def test_casesheetentries_restrict_delete(self):
        """Test: Cannot delete staff who performed case sheet entries"""
        try:
            # Create test patient and staff
            test_patient_id = 'TEST_RESTRICT_PATIENT_DAY2'
            test_staff_id = 'TEST_RESTRICT_STAFF_DAY2'

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

            # Create case sheet entry performed by test staff
            await self.conn.execute("""
                INSERT INTO casesheetentries ("patientId", "entryType", description, "performedBy", timestamp, "createdAt", "updatedAt")
                VALUES ($1, 'Note', 'Test entry', $2, NOW(), NOW(), NOW())
            """, test_patient_id, test_staff_id)

            # Try to delete staff - should FAIL
            try:
                await self.conn.execute('DELETE FROM staff WHERE id = $1', test_staff_id)
                print("[FAIL] Test FAILED: Should not allow deleting staff who performed entries")
                return False

            except asyncpg.exceptions.ForeignKeyViolationError as e:
                if 'fk_casesheetentries_performer' in str(e):
                    print("[PASS] Test PASSED: FK constraint prevented deleting performer")
                    # Cleanup: delete patient (will cascade delete entry)
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
        """Run all Day 2 tests"""
        print("\n" + "=" * 60)
        print("DAY 2 MIGRATION TESTS - FOREIGN KEY CONSTRAINTS")
        print("=" * 60 + "\n")

        # Connect to database
        if not await self.connect():
            return False

        try:
            # Verify constraints
            print("--- Verifying All Constraints ---")
            if not await self.verify_constraints_exist():
                print("\n[FAIL] Not all constraints exist!")
                return False

            # Run FK tests
            print("\n--- Testing FK Constraints ---")

            print("\nTest 1: Invalid Prescriber FK (investigations)")
            test1 = await self.test_investigations_invalid_prescriber()

            print("\nTest 2: CASCADE Delete (therapy)")
            test2 = await self.test_therapy_cascade_delete()

            print("\nTest 3: RESTRICT Delete (casesheetentries)")
            test3 = await self.test_casesheetentries_restrict_delete()

            # Cleanup
            print("\n--- Cleanup ---")
            await self.cleanup()

            # Summary
            print("\n" + "=" * 60)
            print("TEST SUMMARY")
            print("=" * 60)
            all_passed = test1 and test2 and test3

            if all_passed:
                print("[PASS] ALL TESTS PASSED")
                print("\nDay 2 implementation is verified and working correctly!")
                print("Safe to proceed to Day 3.")
            else:
                print("[FAIL] SOME TESTS FAILED")
                print("\nPlease review the failures above before proceeding.")
                print("Day 2 needs fixes before moving to Day 3.")

            print("=" * 60 + "\n")

            return all_passed

        finally:
            await self.close()


async def main():
    """Main test runner"""
    tester = TestDay2Migrations()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
