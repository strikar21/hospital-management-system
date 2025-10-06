"""
Day 6 Validation Tests - Pydantic Validators
Tests comprehensive input validation for all medical data
"""

# CRITICAL: Set environment variables FIRST, before any other imports
import os
os.environ['DATABASEURL'] = 'postgresql://test:test@localhost:5432/test_db'
os.environ['DATABASEPASSWORD'] = 'test_password_for_testing'
os.environ['TIMESCALEDBURL'] = 'postgresql://test:test@localhost:5432/test_timescale'
os.environ['TIMESCALEDBPASSWORD'] = 'test_password_for_testing'
os.environ['SECRETKEY'] = 'test-secret-key-minimum-32-characters-long-for-jwt-signing'

import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.validators.medical_validators import MedicationRequest, MedicationUpdate
from app.validators.patient_validators import PatientCreateValidated, PatientUpdateValidated
from app.validators.investigation_validators import InvestigationRequest, InvestigationUpdate
from app.validators.therapy_validators import TherapyRequest, TherapyUpdate
from app.validators.vitals_validators import VitalSignsCreate, VitalSignsUpdate
from app.validators.sanitizers import (
    sanitize_string,
    sanitize_id,
    sanitize_phone,
    validate_dosage_format,
    validate_frequency_format
)


class TestDay6Validators:
    """Test Day 6 Pydantic validators"""

    def __init__(self):
        self.results = []

    # ==================== Medication Validators ====================

    def test_medication_valid(self):
        """Test: Valid medication data is accepted"""
        try:
            med = MedicationRequest(
                name="Paracetamol",
                dosage="500mg",
                route="Oral",
                frequency="TDS",
                prescribedBy="DOC0001"
            )

            if med.name == "Paracetamol" and med.dosage == "500mg":
                print("[PASS] Test PASSED: Valid medication accepted")
                return True
            else:
                print(f"[FAIL] Medication data incorrect: {med}")
                return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    def test_medication_invalid_dosage(self):
        """Test: Negative dosage is rejected"""
        try:
            med = MedicationRequest(
                name="Paracetamol",
                dosage="-500mg",
                route="Oral",
                frequency="TDS",
                prescribedBy="DOC0001"
            )
            print("[FAIL] Should have rejected negative dosage")
            return False

        except ValidationError as e:
            if "positive" in str(e).lower():
                print("[PASS] Test PASSED: Negative dosage rejected")
                return True
            else:
                print(f"[FAIL] Wrong error: {e}")
                return False

    def test_medication_invalid_route(self):
        """Test: Invalid route is rejected"""
        try:
            med = MedicationRequest(
                name="Paracetamol",
                dosage="500mg",
                route="oarl",  # Typo - should be "Oral"
                frequency="TDS",
                prescribedBy="DOC0001"
            )
            print("[FAIL] Should have rejected invalid route")
            return False

        except ValidationError as e:
            print("[PASS] Test PASSED: Invalid route rejected")
            return True

    def test_medication_invalid_prescriber_id(self):
        """Test: Invalid prescriber ID format is rejected"""
        try:
            med = MedicationRequest(
                name="Paracetamol",
                dosage="500mg",
                route="Oral",
                frequency="TDS",
                prescribedBy="INVALID_ID"
            )
            print("[FAIL] Should have rejected invalid prescriber ID")
            return False

        except ValidationError as e:
            if "id" in str(e).lower():
                print("[PASS] Test PASSED: Invalid prescriber ID rejected")
                return True
            else:
                print(f"[FAIL] Wrong error: {e}")
                return False

    def test_medication_date_range_validation(self):
        """Test: End date before start date is rejected"""
        try:
            med = MedicationRequest(
                name="Paracetamol",
                dosage="500mg",
                route="Oral",
                frequency="TDS",
                prescribedBy="DOC0001",
                startDate=datetime.now(),
                endDate=datetime.now() - timedelta(days=1)
            )
            print("[FAIL] Should have rejected end date before start date")
            return False

        except ValidationError as e:
            if "before" in str(e).lower():
                print("[PASS] Test PASSED: Invalid date range rejected")
                return True
            else:
                print(f"[FAIL] Wrong error: {e}")
                return False

    # ==================== Patient Validators ====================

    def test_patient_valid(self):
        """Test: Valid patient data is accepted"""
        try:
            patient = PatientCreateValidated(
                firstName="John",
                lastName="Doe",
                dateOfBirth=date(1990, 1, 1),
                gender="Male",
                phoneNumber="+1234567890",
                bloodType="O+"
            )

            if patient.firstName == "John" and patient.gender == "Male":
                print("[PASS] Test PASSED: Valid patient accepted")
                return True
            else:
                print(f"[FAIL] Patient data incorrect")
                return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    def test_patient_future_dob_rejected(self):
        """Test: Future date of birth is rejected"""
        try:
            patient = PatientCreateValidated(
                firstName="John",
                lastName="Doe",
                dateOfBirth=date.today() + timedelta(days=365),
                gender="Male"
            )
            print("[FAIL] Should have rejected future DOB")
            return False

        except ValidationError as e:
            if "future" in str(e).lower():
                print("[PASS] Test PASSED: Future DOB rejected")
                return True
            else:
                print(f"[FAIL] Wrong error: {e}")
                return False

    def test_patient_invalid_phone(self):
        """Test: Invalid phone number is rejected"""
        try:
            patient = PatientCreateValidated(
                firstName="John",
                lastName="Doe",
                phoneNumber="123"  # Too short
            )
            print("[FAIL] Should have rejected invalid phone")
            return False

        except ValidationError as e:
            if "phone" in str(e).lower() or "short" in str(e).lower():
                print("[PASS] Test PASSED: Invalid phone rejected")
                return True
            else:
                print(f"[FAIL] Wrong error: {e}")
                return False

    def test_patient_name_no_numbers(self):
        """Test: Names with numbers are rejected"""
        try:
            patient = PatientCreateValidated(
                firstName="John123",
                lastName="Doe"
            )
            print("[FAIL] Should have rejected name with numbers")
            return False

        except ValidationError as e:
            if "number" in str(e).lower():
                print("[PASS] Test PASSED: Name with numbers rejected")
                return True
            else:
                print(f"[FAIL] Wrong error: {e}")
                return False

    # ==================== Vital Signs Validators ====================

    def test_vitals_valid(self):
        """Test: Valid vital signs are accepted"""
        try:
            vitals = VitalSignsCreate(
                patientId="PAT0001",
                heartRate=75,
                bloodPressureSystolic=120,
                bloodPressureDiastolic=80,
                temperature=37.0,
                oxygenSaturation=98
            )

            if vitals.heartRate == 75 and vitals.temperature == 37.0:
                print("[PASS] Test PASSED: Valid vitals accepted")
                return True
            else:
                print(f"[FAIL] Vitals data incorrect")
                return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    def test_vitals_out_of_range_heart_rate(self):
        """Test: Out-of-range heart rate is rejected"""
        try:
            vitals = VitalSignsCreate(
                patientId="PAT0001",
                heartRate=999  # Way too high
            )
            print("[FAIL] Should have rejected out-of-range heart rate")
            return False

        except ValidationError as e:
            print("[PASS] Test PASSED: Out-of-range heart rate rejected")
            return True

    def test_vitals_diastolic_higher_than_systolic(self):
        """Test: Diastolic > systolic BP is rejected"""
        try:
            vitals = VitalSignsCreate(
                patientId="PAT0001",
                bloodPressureSystolic=120,
                bloodPressureDiastolic=130  # Higher than systolic
            )
            print("[FAIL] Should have rejected diastolic > systolic")
            return False

        except ValidationError as e:
            if "lower" in str(e).lower():
                print("[PASS] Test PASSED: Invalid BP ratio rejected")
                return True
            else:
                print(f"[FAIL] Wrong error: {e}")
                return False

    def test_vitals_invalid_patient_id(self):
        """Test: Invalid patient ID format is rejected"""
        try:
            vitals = VitalSignsCreate(
                patientId="INVALID",
                heartRate=75
            )
            print("[FAIL] Should have rejected invalid patient ID")
            return False

        except ValidationError as e:
            if "id" in str(e).lower():
                print("[PASS] Test PASSED: Invalid patient ID rejected")
                return True
            else:
                print(f"[FAIL] Wrong error: {e}")
                return False

    # ==================== Sanitizer Tests ====================

    def test_sanitize_phone(self):
        """Test: Phone sanitizer cleans input"""
        try:
            result = sanitize_phone("+1 (234) 567-8900")
            if result == "+12345678900":
                print("[PASS] Test PASSED: Phone sanitizer works")
                return True
            else:
                print(f"[FAIL] Phone sanitizer output incorrect: {result}")
                return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    def test_validate_dosage_positive(self):
        """Test: Dosage validator accepts positive values"""
        try:
            result = validate_dosage_format("500mg")
            if result == "500mg":
                print("[PASS] Test PASSED: Valid dosage accepted")
                return True
            else:
                print(f"[FAIL] Dosage result incorrect: {result}")
                return False

        except Exception as e:
            print(f"[FAIL] Test error: {e}")
            return False

    def test_validate_dosage_negative_rejected(self):
        """Test: Dosage validator rejects negative values"""
        try:
            result = validate_dosage_format("-500mg")
            print("[FAIL] Should have rejected negative dosage")
            return False

        except ValueError as e:
            if "positive" in str(e).lower():
                print("[PASS] Test PASSED: Negative dosage rejected")
                return True
            else:
                print(f"[FAIL] Wrong error: {e}")
                return False

    def run_all_tests(self):
        """Run all Day 6 validation tests"""
        print("\n" + "=" * 60)
        print("DAY 6 VALIDATION TESTS - PYDANTIC VALIDATORS")
        print("=" * 60 + "\n")

        print("--- Testing Medication Validators ---")
        print("\nTest 1: Valid Medication")
        test1 = self.test_medication_valid()

        print("\nTest 2: Negative Dosage Rejected")
        test2 = self.test_medication_invalid_dosage()

        print("\nTest 3: Invalid Route Rejected")
        test3 = self.test_medication_invalid_route()

        print("\nTest 4: Invalid Prescriber ID Rejected")
        test4 = self.test_medication_invalid_prescriber_id()

        print("\nTest 5: Invalid Date Range Rejected")
        test5 = self.test_medication_date_range_validation()

        print("\n--- Testing Patient Validators ---")
        print("\nTest 6: Valid Patient")
        test6 = self.test_patient_valid()

        print("\nTest 7: Future DOB Rejected")
        test7 = self.test_patient_future_dob_rejected()

        print("\nTest 8: Invalid Phone Rejected")
        test8 = self.test_patient_invalid_phone()

        print("\nTest 9: Name with Numbers Rejected")
        test9 = self.test_patient_name_no_numbers()

        print("\n--- Testing Vital Signs Validators ---")
        print("\nTest 10: Valid Vitals")
        test10 = self.test_vitals_valid()

        print("\nTest 11: Out-of-Range Heart Rate Rejected")
        test11 = self.test_vitals_out_of_range_heart_rate()

        print("\nTest 12: Diastolic > Systolic Rejected")
        test12 = self.test_vitals_diastolic_higher_than_systolic()

        print("\nTest 13: Invalid Patient ID Rejected")
        test13 = self.test_vitals_invalid_patient_id()

        print("\n--- Testing Sanitizers ---")
        print("\nTest 14: Phone Sanitizer")
        test14 = self.test_sanitize_phone()

        print("\nTest 15: Dosage Validator (Positive)")
        test15 = self.test_validate_dosage_positive()

        print("\nTest 16: Dosage Validator (Negative Rejected)")
        test16 = self.test_validate_dosage_negative_rejected()

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        all_tests = [test1, test2, test3, test4, test5, test6, test7, test8,
                     test9, test10, test11, test12, test13, test14, test15, test16]
        all_passed = all(all_tests)

        passed_count = sum(all_tests)
        total_count = len(all_tests)

        if all_passed:
            print(f"[PASS] ALL TESTS PASSED ({passed_count}/{total_count})")
            print("\nDay 6 Pydantic validation is working correctly!")
            print("All invalid medical data is being rejected.")
            print("Patient safety validations are enforced.")
        else:
            print(f"[FAIL] SOME TESTS FAILED ({passed_count}/{total_count} passed)")
            print("\nPlease review the failures above.")

        print("=" * 60 + "\n")

        return all_passed


def main():
    """Main test runner"""
    tester = TestDay6Validators()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
