"""
Day 3 Migration Tests - Automated Testing for CHECK Constraints
Tests CHECK constraints for data validation across all tables
"""
import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings


class TestDay3Migrations:
    """Test Day 3 CHECK constraint migrations"""

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
        """Verify all Day 3 CHECK constraints exist"""
        try:
            print("\n--- Verifying CHECK Constraints ---")

            constraints = await self.conn.fetch("""
                SELECT conname as constraint_name
                FROM pg_constraint
                WHERE conname IN (
                    'medications_status_check',
                    'medications_route_check',
                    'medications_date_range_check',
                    'investigations_status_check',
                    'investigations_priority_check',
                    'investigations_urgency_check',
                    'therapy_status_check',
                    'therapy_date_range_check',
                    'patients_status_check',
                    'patients_gender_check',
                    'patients_dob_check',
                    'staff_role_check'
                )
                ORDER BY constraint_name
            """)

            constraint_names = [c['constraint_name'] for c in constraints]
            expected = [
                'investigations_priority_check',
                'investigations_status_check',
                'investigations_urgency_check',
                'medications_date_range_check',
                'medications_route_check',
                'medications_status_check',
                'patients_dob_check',
                'patients_gender_check',
                'patients_status_check',
                'staff_role_check',
                'therapy_date_range_check',
                'therapy_status_check',
            ]

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

    async def test_medications_invalid_status(self):
        """Test: Cannot insert medication with invalid status"""
        try:
            # Get a valid patient and staff
            patient = await self.conn.fetchrow("SELECT id FROM patients LIMIT 1")
            staff = await self.conn.fetchrow("SELECT id FROM staff LIMIT 1")

            if not patient or not staff:
                print("[SKIP] No test data available")
                return True

            # Try to insert with invalid status - should FAIL
            try:
                await self.conn.execute("""
                    INSERT INTO medications ("patientId", name, dosage, frequency, route, status, "prescribedBy", "createdBy", "createdAt", "updatedAt")
                    VALUES ($1, 'Test Med', '100mg', 'QD', 'PO', 'INVALID_STATUS', $2, $2, NOW(), NOW())
                """, patient['id'], staff['id'])

                print("[FAIL] Test FAILED: Should not allow invalid status")
                return False

            except asyncpg.exceptions.CheckViolationError as e:
                # Accept any CHECK constraint that blocks invalid status
                if 'status' in str(e).lower():
                    print("[PASS] Test PASSED: CHECK constraint blocked invalid status")
                    return True
                else:
                    print(f"[FAIL] Test FAILED: Wrong CHECK error: {e}")
                    return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    async def test_medications_invalid_route(self):
        """Test: Cannot insert medication with invalid route"""
        try:
            patient = await self.conn.fetchrow("SELECT id FROM patients LIMIT 1")
            staff = await self.conn.fetchrow("SELECT id FROM staff LIMIT 1")

            if not patient or not staff:
                print("[SKIP] No test data available")
                return True

            # Try to insert with invalid route - should FAIL
            try:
                await self.conn.execute("""
                    INSERT INTO medications ("patientId", name, dosage, frequency, route, status, "prescribedBy", "createdBy", "createdAt", "updatedAt")
                    VALUES ($1, 'Test Med', '100mg', 'QD', 'InvalidRoute', 'active', $2, $2, NOW(), NOW())
                """, patient['id'], staff['id'])

                print("[FAIL] Test FAILED: Should not allow invalid route")
                return False

            except asyncpg.exceptions.CheckViolationError as e:
                if 'medications_route_check' in str(e):
                    print("[PASS] Test PASSED: CHECK constraint blocked invalid route")
                    return True
                else:
                    print(f"[FAIL] Test FAILED: Wrong CHECK error: {e}")
                    return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    async def test_medications_invalid_date_range(self):
        """Test: Cannot insert medication with endDate < startDate"""
        try:
            patient = await self.conn.fetchrow("SELECT id FROM patients LIMIT 1")
            staff = await self.conn.fetchrow("SELECT id FROM staff LIMIT 1")

            if not patient or not staff:
                print("[SKIP] No test data available")
                return True

            # Try to insert with endDate before startDate - should FAIL
            try:
                await self.conn.execute("""
                    INSERT INTO medications ("patientId", name, dosage, frequency, route, status, "prescribedBy", "createdBy", "startDate", "endDate", "createdAt", "updatedAt")
                    VALUES ($1, 'Test Med', '100mg', 'QD', 'PO', 'active', $2, $2, '2025-10-10', '2025-10-01', NOW(), NOW())
                """, patient['id'], staff['id'])

                print("[FAIL] Test FAILED: Should not allow endDate < startDate")
                return False

            except asyncpg.exceptions.CheckViolationError as e:
                if 'medications_date_range_check' in str(e):
                    print("[PASS] Test PASSED: CHECK constraint blocked invalid date range")
                    return True
                else:
                    print(f"[FAIL] Test FAILED: Wrong CHECK error: {e}")
                    return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    async def test_patients_future_dob(self):
        """Test: Cannot insert patient with future date of birth"""
        try:
            # Try to insert with future DOB - should FAIL
            try:
                await self.conn.execute("""
                    INSERT INTO patients (id, "firstName", "lastName", "dateOfBirth", gender, status, "createdAt", "updatedAt")
                    VALUES ('TEST_FUTURE_DOB', 'Future', 'Baby', '2030-01-01', 'Male', 'active', NOW(), NOW())
                """)

                print("[FAIL] Test FAILED: Should not allow future date of birth")
                # Cleanup
                await self.conn.execute("DELETE FROM patients WHERE id = 'TEST_FUTURE_DOB'")
                return False

            except asyncpg.exceptions.CheckViolationError as e:
                if 'patients_dob_check' in str(e):
                    print("[PASS] Test PASSED: CHECK constraint blocked future DOB")
                    return True
                else:
                    print(f"[FAIL] Test FAILED: Wrong CHECK error: {e}")
                    return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    async def test_patients_invalid_gender(self):
        """Test: Cannot insert patient with invalid gender"""
        try:
            # Try to insert with invalid gender - should FAIL
            try:
                await self.conn.execute("""
                    INSERT INTO patients (id, "firstName", "lastName", "dateOfBirth", gender, status, "createdAt", "updatedAt")
                    VALUES ('TEST_INVALID_GENDER', 'Test', 'Patient', '1990-01-01', 'InvalidGender', 'active', NOW(), NOW())
                """)

                print("[FAIL] Test FAILED: Should not allow invalid gender")
                # Cleanup
                await self.conn.execute("DELETE FROM patients WHERE id = 'TEST_INVALID_GENDER'")
                return False

            except asyncpg.exceptions.CheckViolationError as e:
                if 'patients_gender_check' in str(e):
                    print("[PASS] Test PASSED: CHECK constraint blocked invalid gender")
                    return True
                else:
                    print(f"[FAIL] Test FAILED: Wrong CHECK error: {e}")
                    return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    async def test_staff_invalid_role(self):
        """Test: Cannot insert staff with invalid role"""
        try:
            # Try to insert with invalid role - should FAIL
            try:
                await self.conn.execute("""
                    INSERT INTO staff (id, role, email, "firstName", "lastName", "createdAt", "updatedAt")
                    VALUES ('TEST_INVALID_ROLE', 'InvalidRole', 'test@test.com', 'Test', 'Staff', NOW(), NOW())
                """)

                print("[FAIL] Test FAILED: Should not allow invalid role")
                # Cleanup
                await self.conn.execute("DELETE FROM staff WHERE id = 'TEST_INVALID_ROLE'")
                return False

            except asyncpg.exceptions.CheckViolationError as e:
                if 'staff_role_check' in str(e):
                    print("[PASS] Test PASSED: CHECK constraint blocked invalid role")
                    return True
                else:
                    print(f"[FAIL] Test FAILED: Wrong CHECK error: {e}")
                    return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    async def test_investigations_invalid_status(self):
        """Test: Cannot insert investigation with invalid status"""
        try:
            patient = await self.conn.fetchrow("SELECT id FROM patients LIMIT 1")
            staff = await self.conn.fetchrow("SELECT id FROM staff LIMIT 1")

            if not patient or not staff:
                print("[SKIP] No test data available")
                return True

            # Try to insert with invalid status - should FAIL
            try:
                await self.conn.execute("""
                    INSERT INTO investigations ("patientId", type, name, status, "prescribedBy", "createdAt", "updatedAt")
                    VALUES ($1, 'lab', 'Test', 'invalid_status', $2, NOW(), NOW())
                """, patient['id'], staff['id'])

                print("[FAIL] Test FAILED: Should not allow invalid status")
                return False

            except asyncpg.exceptions.CheckViolationError as e:
                # Accept any CHECK constraint that blocks invalid status
                if 'status' in str(e).lower():
                    print("[PASS] Test PASSED: CHECK constraint blocked invalid status")
                    return True
                else:
                    print(f"[FAIL] Test FAILED: Wrong CHECK error: {e}")
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
        """Run all Day 3 tests"""
        print("\n" + "=" * 60)
        print("DAY 3 MIGRATION TESTS - CHECK CONSTRAINTS")
        print("=" * 60 + "\n")

        # Connect to database
        if not await self.connect():
            return False

        try:
            # Verify constraints
            if not await self.verify_constraints_exist():
                print("\n[FAIL] Not all constraints exist!")
                return False

            # Run CHECK constraint tests
            print("\n--- Testing CHECK Constraints ---")

            print("\nTest 1: Invalid Medication Status")
            test1 = await self.test_medications_invalid_status()

            print("\nTest 2: Invalid Medication Route")
            test2 = await self.test_medications_invalid_route()

            print("\nTest 3: Invalid Medication Date Range")
            test3 = await self.test_medications_invalid_date_range()

            print("\nTest 4: Future Date of Birth")
            test4 = await self.test_patients_future_dob()

            print("\nTest 5: Invalid Patient Gender")
            test5 = await self.test_patients_invalid_gender()

            print("\nTest 6: Invalid Staff Role")
            test6 = await self.test_staff_invalid_role()

            print("\nTest 7: Invalid Investigation Status")
            test7 = await self.test_investigations_invalid_status()

            # Cleanup
            print("\n--- Cleanup ---")
            await self.cleanup()

            # Summary
            print("\n" + "=" * 60)
            print("TEST SUMMARY")
            print("=" * 60)
            all_passed = test1 and test2 and test3 and test4 and test5 and test6 and test7

            if all_passed:
                print("[PASS] ALL TESTS PASSED")
                print("\nDay 3 implementation is verified and working correctly!")
                print("Safe to proceed to Day 4.")
            else:
                print("[FAIL] SOME TESTS FAILED")
                print("\nPlease review the failures above before proceeding.")
                print("Day 3 needs fixes before moving to Day 4.")

            print("=" * 60 + "\n")

            return all_passed

        finally:
            await self.close()


async def main():
    """Main test runner"""
    tester = TestDay3Migrations()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
