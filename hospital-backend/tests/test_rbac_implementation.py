"""
Automated RBAC Implementation Tests
Tests all role-based access control and security features
"""

import pytest
import requests
import time
from typing import Dict, Optional

# Base URL for API
BASE_URL = "http://localhost:8001"

# Test user credentials (matches populate_database.py)
TEST_USERS = {
    "doctor": {"staffId": "DOC0001", "pin": "1234"},
    "nurse": {"staffId": "NUR0001", "pin": "5678"},
    "admin": {"staffId": "ADM0001", "pin": "9999"}
}

# Global tokens storage
tokens: Dict[str, Optional[str]] = {
    "doctor": None,
    "nurse": None,
    "admin": None
}


class TestAuthentication:
    """Test authentication and token generation"""

    def test_01_backend_is_running(self):
        """Test that backend server is accessible"""
        try:
            response = requests.get(f"{BASE_URL}/docs", timeout=5)
            assert response.status_code == 200, "Backend is not running"
            print("[PASS] Backend is running")
        except requests.exceptions.ConnectionError:
            pytest.fail("[FAIL] Backend is not running. Start with: python -m uvicorn main:app --port 8001")

    def test_02_login_as_doctor(self):
        """Test doctor login and token generation"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=TEST_USERS["doctor"]
        )
        assert response.status_code == 200, f"Doctor login failed: {response.text}"
        data = response.json()
        assert "accessToken" in data, "No accessToken in response"
        tokens["doctor"] = data["accessToken"]
        print(f"[PASS] Doctor login successful, token: {tokens['doctor'][:20]}...")

    def test_03_login_as_nurse(self):
        """Test nurse login and token generation"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=TEST_USERS["nurse"]
        )
        assert response.status_code == 200, f"Nurse login failed: {response.text}"
        data = response.json()
        assert "accessToken" in data, "No accessToken in response"
        tokens["nurse"] = data["accessToken"]
        print(f"[PASS] Nurse login successful, token: {tokens['nurse'][:20]}...")

    def test_04_login_as_admin(self):
        """Test admin login and token generation"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=TEST_USERS["admin"]
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "accessToken" in data, "No accessToken in response"
        tokens["admin"] = data["accessToken"]
        print(f"[PASS] Admin login successful, token: {tokens['admin'][:20]}...")

    def test_05_invalid_credentials(self):
        """Test login with invalid credentials fails"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"staffId": "DOC0001", "pin": "9999"}
        )
        assert response.status_code in [401, 403], "Invalid login should fail"
        print("[PASS] Invalid credentials rejected")


class TestMedicationRBAC:
    """Test RBAC for medication endpoints"""

    def test_10_doctor_can_prescribe(self):
        """Test doctor can prescribe medication"""
        assert tokens["doctor"], "Doctor not logged in"

        response = requests.post(
            f"{BASE_URL}/api/v2/atomic/patients/PAT001/medications",
            headers={"Authorization": f"Bearer {tokens['doctor']}"},
            json={
                "name": "Test Medication",
                "dosage": "100mg",
                "frequency": "Daily",
                "route": "Oral",
                "prescribedBy": "DOC0001"
            }
        )

        # Should succeed (200) or patient not found (404), but not forbidden
        assert response.status_code in [200, 404], f"Doctor prescribe failed: {response.status_code} - {response.text}"
        if response.status_code != 404:
            print("[PASS] Doctor can prescribe medications")
        else:
            print("[WARN] Patient PAT001 not found (expected in test env), but RBAC passed")

    def test_11_nurse_cannot_prescribe(self):
        """Test nurse CANNOT prescribe medication"""
        assert tokens["nurse"], "Nurse not logged in"

        response = requests.post(
            f"{BASE_URL}/api/v2/atomic/patients/PAT001/medications",
            headers={"Authorization": f"Bearer {tokens['nurse']}"},
            json={
                "name": "Test Medication",
                "dosage": "100mg",
                "frequency": "Daily",
                "route": "Oral",
                "prescribedBy": "NUR0001"
            }
        )

        assert response.status_code == 403, f"Nurse should not be able to prescribe: {response.status_code}"
        print("[PASS] Nurse CANNOT prescribe medications (403 Forbidden)")

    def test_12_no_auth_cannot_prescribe(self):
        """Test unauthenticated request is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/v2/atomic/patients/PAT001/medications",
            json={
                "name": "Test Medication",
                "dosage": "100mg",
                "route": "Oral",
                "prescribedBy": "DOC0001"
            }
        )

        assert response.status_code in [401, 403], f"Unauthenticated request should fail: {response.status_code}"
        print("[PASS] Unauthenticated requests rejected")

    def test_13_doctor_cannot_impersonate(self):
        """Test doctor cannot prescribe as another doctor"""
        assert tokens["doctor"], "Doctor not logged in"

        response = requests.post(
            f"{BASE_URL}/api/v2/atomic/patients/PAT001/medications",
            headers={"Authorization": f"Bearer {tokens['doctor']}"},
            json={
                "name": "Test Medication",
                "dosage": "100mg",
                "frequency": "Daily",
                "route": "Oral",
                "prescribedBy": "DOC0002"  # Different doctor
            }
        )

        assert response.status_code == 403, f"Impersonation should be blocked: {response.status_code}"
        print("[PASS] Doctor cannot impersonate another doctor (403 Forbidden)")


class TestInvestigationRBAC:
    """Test RBAC for investigation endpoints"""

    def test_20_doctor_can_order_investigation(self):
        """Test doctor can order investigation"""
        assert tokens["doctor"], "Doctor not logged in"

        response = requests.post(
            f"{BASE_URL}/api/v2/atomic/patients/PAT001/investigations",
            headers={"Authorization": f"Bearer {tokens['doctor']}"},
            json={
                "testName": "Blood Test",
                "testType": "Lab",
                "priority": "Normal",
                "prescribedBy": "DOC0001"
            }
        )

        assert response.status_code in [200, 404], f"Doctor order investigation failed: {response.status_code}"
        print("[PASS] Doctor can order investigations")

    def test_21_nurse_cannot_order_investigation(self):
        """Test nurse CANNOT order investigation"""
        assert tokens["nurse"], "Nurse not logged in"

        response = requests.post(
            f"{BASE_URL}/api/v2/atomic/patients/PAT001/investigations",
            headers={"Authorization": f"Bearer {tokens['nurse']}"},
            json={
                "testName": "Blood Test",
                "testType": "Lab",
                "priority": "Normal",
                "prescribedBy": "NUR0001"
            }
        )

        assert response.status_code == 403, f"Nurse should not order investigations: {response.status_code}"
        print("[PASS] Nurse CANNOT order investigations (403 Forbidden)")


class TestDischargeRBAC:
    """Test RBAC for discharge workflow"""

    def test_30_doctor_can_request_discharge(self):
        """Test doctor can request discharge"""
        assert tokens["doctor"], "Doctor not logged in"

        response = requests.post(
            f"{BASE_URL}/api/v1/discharge/doctor-request",
            headers={"Authorization": f"Bearer {tokens['doctor']}"},
            json={
                "patientId": "PAT_TEST_001",
                "dischargeReason": "Treatment complete",
                "requestedBy": "DOC0001"
            }
        )

        # 200 (success) or 400/404 (patient not found/already discharged) - but not 403
        assert response.status_code in [200, 400, 404], f"Doctor discharge request unexpected: {response.status_code}"
        assert response.status_code != 403, "Doctor should be authorized to request discharge"
        print("[PASS] Doctor can request discharge (authorized)")

    def test_31_nurse_cannot_request_discharge(self):
        """Test nurse CANNOT request discharge"""
        assert tokens["nurse"], "Nurse not logged in"

        response = requests.post(
            f"{BASE_URL}/api/v1/discharge/doctor-request",
            headers={"Authorization": f"Bearer {tokens['nurse']}"},
            json={
                "patientId": "PAT_TEST_002",
                "dischargeReason": "Treatment complete",
                "requestedBy": "NUR0001"
            }
        )

        assert response.status_code == 403, f"Nurse should not request discharge: {response.status_code}"
        print("[PASS] Nurse CANNOT request discharge (403 Forbidden)")

    def test_32_admin_can_approve_discharge(self):
        """Test admin can approve discharge"""
        assert tokens["admin"], "Admin not logged in"

        response = requests.post(
            f"{BASE_URL}/api/v1/discharge/admin-approval",
            headers={"Authorization": f"Bearer {tokens['admin']}"},
            json={
                "patientId": "PAT_TEST_001",
                "approvedBy": "ADM0001"
            }
        )

        # Should be authorized (not 403), might fail for other reasons (404, 400)
        assert response.status_code != 403, "Admin should be authorized to approve"
        print("[PASS] Admin can approve discharge (authorized)")

    def test_33_doctor_cannot_approve_discharge(self):
        """Test doctor CANNOT approve discharge"""
        assert tokens["doctor"], "Doctor not logged in"

        response = requests.post(
            f"{BASE_URL}/api/v1/discharge/admin-approval",
            headers={"Authorization": f"Bearer {tokens['doctor']}"},
            json={
                "patientId": "PAT_TEST_001",
                "approvedBy": "DOC0001"
            }
        )

        assert response.status_code == 403, f"Doctor should not approve discharge: {response.status_code}"
        print("[PASS] Doctor CANNOT approve discharge (403 Forbidden)")


class TestStaffManagementRBAC:
    """Test RBAC for staff management"""

    def test_40_admin_can_access_staff_list(self):
        """Test admin can view staff list"""
        assert tokens["admin"], "Admin not logged in"

        response = requests.get(
            f"{BASE_URL}/api/v1/staff/",
            headers={"Authorization": f"Bearer {tokens['admin']}"}
        )

        assert response.status_code == 200, f"Admin should access staff list: {response.status_code}"
        print("[PASS] Admin can view staff list")

    def test_41_doctor_cannot_access_staff_list(self):
        """Test doctor CANNOT view staff list (admin only)"""
        assert tokens["doctor"], "Doctor not logged in"

        response = requests.get(
            f"{BASE_URL}/api/v1/staff/",
            headers={"Authorization": f"Bearer {tokens['doctor']}"}
        )

        assert response.status_code == 403, f"Doctor should not access staff list: {response.status_code}"
        print("[PASS] Doctor CANNOT view staff list (403 Forbidden)")


class TestDeviceManagementRBAC:
    """Test RBAC for device management"""

    def test_50_admin_authorized_for_device_ops(self):
        """Test admin is authorized for device operations"""
        assert tokens["admin"], "Admin not logged in"

        # Try to create device (will fail validation but should be authorized)
        response = requests.post(
            f"{BASE_URL}/api/v1/devices/?createdBy=ADM0001",
            headers={"Authorization": f"Bearer {tokens['admin']}"},
            json={}  # Empty to trigger validation error, not auth error
        )

        # Should fail validation (400/422) but NOT authorization (403)
        assert response.status_code != 403, f"Admin should be authorized for devices: {response.status_code}"
        print("[PASS] Admin authorized for device operations")

    def test_51_nurse_cannot_manage_devices(self):
        """Test nurse CANNOT manage devices (admin only)"""
        assert tokens["nurse"], "Nurse not logged in"

        response = requests.post(
            f"{BASE_URL}/api/v1/devices/?createdBy=NUR0001",
            headers={"Authorization": f"Bearer {tokens['nurse']}"},
            json={"deviceType": "watch", "name": "Test Watch"}
        )

        assert response.status_code == 403, f"Nurse should not manage devices: {response.status_code}"
        print("[PASS] Nurse CANNOT manage devices (403 Forbidden)")


class TestWatchAssignmentRBAC:
    """Test RBAC for watch assignment"""

    def test_60_nurse_can_assign_watch(self):
        """Test nurse CAN assign watch (medical staff)"""
        assert tokens["nurse"], "Nurse not logged in"

        response = requests.post(
            f"{BASE_URL}/api/v1/watchmanagement/assign",
            headers={"Authorization": f"Bearer {tokens['nurse']}"},
            json={
                "patientId": "PAT_TEST_001",
                "deviceId": "WATCH001",
                "assignedBy": "NUR0001"
            }
        )

        # Should be authorized (not 403), might fail for other reasons
        assert response.status_code != 403, "Nurse should be authorized to assign watches"
        print("[PASS] Nurse can assign watches (medical staff)")

    def test_61_doctor_can_assign_watch(self):
        """Test doctor CAN assign watch (medical staff)"""
        assert tokens["doctor"], "Doctor not logged in"

        response = requests.post(
            f"{BASE_URL}/api/v1/watchmanagement/assign",
            headers={"Authorization": f"Bearer {tokens['doctor']}"},
            json={
                "patientId": "PAT_TEST_002",
                "deviceId": "WATCH002",
                "assignedBy": "DOC0001"
            }
        )

        # Should be authorized (not 403), might fail for other reasons
        assert response.status_code != 403, "Doctor should be authorized to assign watches"
        print("[PASS] Doctor can assign watches (medical staff)")


class TestSecurityFeatures:
    """Test security features and bug fixes"""

    def test_70_duplicate_discharge_endpoint_removed(self):
        """Test that duplicate /nurse-approve endpoint is removed"""
        # This endpoint should not exist anymore
        response = requests.post(
            f"{BASE_URL}/api/v1/discharge/nurse-approve",
            headers={"Authorization": f"Bearer {tokens['nurse']}"},
            params={"patientId": "PAT001", "nurseId": "NUR0001"}
        )

        # Should return 404 (not found) since endpoint was deleted
        assert response.status_code == 404, f"Duplicate endpoint should be deleted: {response.status_code}"
        print("[PASS] Duplicate /nurse-approve endpoint removed (404)")

    def test_71_swagger_ui_accessible(self):
        """Test Swagger UI is accessible"""
        response = requests.get(f"{BASE_URL}/docs")
        assert response.status_code == 200, "Swagger UI should be accessible"
        assert "swagger-ui" in response.text.lower(), "Should be Swagger UI page"
        print("[PASS] Swagger UI accessible")

    def test_72_openapi_schema_available(self):
        """Test OpenAPI schema is available"""
        response = requests.get(f"{BASE_URL}/openapi.json")
        assert response.status_code == 200, "OpenAPI schema should be available"
        schema = response.json()
        assert "paths" in schema, "Should have paths in OpenAPI schema"
        print(f"[PASS] OpenAPI schema available ({len(schema.get('paths', {}))} endpoints)")


def print_test_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("RBAC IMPLEMENTATION TEST SUMMARY")
    print("="*60)
    print("\nAll tests passed! RBAC is working correctly.")
    print("\nVerified:")
    print("  [PASS] Authentication (login/tokens)")
    print("  [PASS] Authorization (role-based access)")
    print("  [PASS] Doctor can prescribe medications")
    print("  [PASS] Nurse CANNOT prescribe medications")
    print("  [PASS] Impersonation prevention")
    print("  [PASS] Discharge workflow RBAC")
    print("  [PASS] Staff management RBAC")
    print("  [PASS] Device management RBAC")
    print("  [PASS] Watch assignment RBAC")
    print("  [PASS] Duplicate endpoint removed")
    print("\n" + "="*60)


if __name__ == "__main__":
    # Run with pytest
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s", "--tb=short"]))
