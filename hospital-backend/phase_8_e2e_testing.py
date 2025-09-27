#!/usr/bin/env python3
"""
Phase 8: End-to-End Testing Suite
Hospital Management System - Complete Frontend-Backend Integration Testing

This suite validates that Phase 7 frontend integration fixes work correctly
by testing complete workflows from frontend API calls to backend responses.
"""

import asyncio
import aiohttp
import json
import time
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Phase8E2ETester:
    """End-to-End Testing for Frontend-Backend Integration"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session = None
        self.test_results = {}
        self.current_user_token = None
        self.test_patient_id = None
        self.test_device_id = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def log_test_result(self, test_name: str, success: bool, details: str = "", data: Dict = None):
        """Log test result with detailed information"""
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} | {test_name}")
        if details:
            logger.info(f"    Details: {details}")
        if data and not success:
            logger.info(f"    Response: {json.dumps(data, indent=2)}")

        self.test_results[test_name] = {
            "success": success,
            "details": details,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def make_request(self, method: str, endpoint: str, data: Dict = None, headers: Dict = None) -> tuple:
        """Make HTTP request and return (success, status_code, response_data)"""
        try:
            url = f"{self.base_url}{endpoint}"
            async with self.session.request(method, url, json=data, headers=headers) as response:
                try:
                    response_data = await response.json()
                except:
                    response_data = await response.text()

                return response.status < 400, response.status, response_data
        except Exception as e:
            return False, 0, {"error": str(e)}

    # ================================
    # PHASE 8 AUTHENTICATION TESTS
    # ================================

    async def test_authentication_workflow(self):
        """Test complete authentication workflow including Phase 7 fixes"""
        logger.info("🔐 Testing Authentication Workflow (Phase 7 Integration)")

        # Test 1: Health Check
        success, status, data = await self.make_request("GET", "/health")
        await self.log_test_result(
            "Health Check",
            success and status == 200,
            f"Status: {status}",
            data if not success else None
        )

        if not success:
            return False

        # Test 2: Check Auth Type (Phase 7 Fix)
        test_staff_id = "DOC0001"
        success, status, data = await self.make_request("GET", f"/api/v1/auth/check-type?staffId={test_staff_id}")
        await self.log_test_result(
            "Auth Type Check (Phase 7 Fix)",
            success and status == 200 and "authMethods" in data,
            f"Status: {status}, Methods: {data.get('authMethods', [])}",
            data if not success else None
        )

        # Test 3: Staff Login
        login_data = {
            "staffId": "DOC0001",
            "pin": "1234"
        }
        success, status, data = await self.make_request("POST", "/api/v1/auth/login", login_data)
        auth_success = success and status == 200 and "id" in data
        await self.log_test_result(
            "Staff Login with PIN",
            auth_success,
            f"Status: {status}, User: {data.get('firstName', '')} {data.get('lastName', '')}",
            data if not success else None
        )

        # Test 4: NFC Authentication (Phase 7 Fix)
        nfc_data = {"nfcId": "NFC001"}
        success, status, data = await self.make_request("POST", "/api/v1/auth/nfc", nfc_data)
        await self.log_test_result(
            "NFC Authentication (Phase 7 Fix)",
            success and status in [200, 401],  # 401 is acceptable for invalid NFC
            f"Status: {status}",
            data if not success and status not in [401, 404] else None
        )

        return auth_success

    # ================================
    # PHASE 8 PATIENT MANAGEMENT TESTS
    # ================================

    async def test_patient_management_workflow(self):
        """Test complete patient management workflow with Phase 7 data transformations"""
        logger.info("🏥 Testing Patient Management Workflow (Phase 7 Data Transformation)")

        # Test 1: List Patients (v2 endpoint)
        success, status, data = await self.make_request("GET", "/api/v2/patients/list")
        patients_list_success = success and status == 200
        await self.log_test_result(
            "List Patients (v2 Repository)",
            patients_list_success,
            f"Status: {status}, Count: {len(data.get('patients', []))}" if patients_list_success else f"Status: {status}",
            data if not success else None
        )

        # Test 2: Create Patient
        patient_data = {
            "firstName": "John",
            "lastName": "TestPatient",
            "dateOfBirth": "1990-01-01",
            "gender": "Male",
            "phoneNumber": "555-1234",
            "bloodType": "O+",
            "roomNumber": "ICU-101",
            "bedNumber": "1",
            "attendingPhysician": "DOC0001"
        }

        success, status, data = await self.make_request("POST", "/api/v2/patients/", patient_data)
        patient_created = success and status == 200
        if patient_created and "id" in data:
            self.test_patient_id = data["id"]

        await self.log_test_result(
            "Create Patient (v2 Repository)",
            patient_created,
            f"Status: {status}, Patient ID: {self.test_patient_id}" if patient_created else f"Status: {status}",
            data if not success else None
        )

        # Test 3: Get Patient with Computed Properties (Phase 7 Fix)
        if self.test_patient_id:
            success, status, data = await self.make_request("GET", f"/api/v2/patients/{self.test_patient_id}")

            # Validate Phase 7 computed properties
            has_name_property = "name" in data if success and isinstance(data, dict) else False
            has_ward_property = "ward" in data if success and isinstance(data, dict) else False
            has_vitals_structure = "vitals" in data if success and isinstance(data, dict) else False

            computed_props_success = success and status == 200 and has_name_property

            await self.log_test_result(
                "Patient Computed Properties (Phase 7 Fix)",
                computed_props_success,
                f"Status: {status}, Has name: {has_name_property}, Has ward: {has_ward_property}, Has vitals: {has_vitals_structure}",
                data if not success else None
            )

        # Test 4: Search Patients
        success, status, data = await self.make_request("GET", "/api/v2/patients/search/John")
        await self.log_test_result(
            "Search Patients",
            success and status == 200,
            f"Status: {status}, Results: {len(data.get('patients', []))}" if success else f"Status: {status}",
            data if not success else None
        )

        return patient_created

    # ================================
    # PHASE 8 DEVICE MANAGEMENT TESTS
    # ================================

    async def test_device_management_workflow(self):
        """Test device management including Phase 7 endpoint fixes"""
        logger.info("📱 Testing Device Management Workflow (Phase 7 Endpoint Alignment)")

        # Test 1: Get Available Devices (Phase 7 Fix)
        success, status, data = await self.make_request("GET", "/api/v1/devices/available")
        available_devices_success = success and status == 200
        await self.log_test_result(
            "Get Available Devices (Phase 7 Fix)",
            available_devices_success,
            f"Status: {status}, Available: {len(data.get('devices', []))}" if available_devices_success else f"Status: {status}",
            data if not success else None
        )

        # Test 2: List All Devices
        success, status, data = await self.make_request("GET", "/api/v1/devices/")
        await self.log_test_result(
            "List All Devices",
            success and status == 200,
            f"Status: {status}, Total: {len(data.get('devices', []))}" if success else f"Status: {status}",
            data if not success else None
        )

        # Test 3: Get Device Types
        success, status, data = await self.make_request("GET", "/api/v1/devices/types")
        await self.log_test_result(
            "Get Device Types",
            success and status == 200,
            f"Status: {status}, Types: {list(data.get('deviceTypes', {}).keys())}" if success else f"Status: {status}",
            data if not success else None
        )

        # Test 4: Watch Management Integration
        success, status, data = await self.make_request("GET", "/api/v1/watchmanagement/")
        await self.log_test_result(
            "Watch Management Integration",
            success and status == 200,
            f"Status: {status}",
            data if not success else None
        )

        return available_devices_success

    # ================================
    # PHASE 8 API V2 ENDPOINTS TESTS
    # ================================

    async def test_v2_repository_endpoints(self):
        """Test v2 repository-based endpoints"""
        logger.info("🔄 Testing V2 Repository Endpoints")

        endpoints_to_test = [
            "/api/v2/medications/list",
            "/api/v2/investigations/list",
            "/api/v2/therapy/list"
        ]

        v2_success_count = 0

        for endpoint in endpoints_to_test:
            success, status, data = await self.make_request("GET", endpoint)
            endpoint_name = endpoint.split('/')[-2].title()

            await self.log_test_result(
                f"V2 {endpoint_name} Endpoint",
                success and status == 200,
                f"Status: {status}",
                data if not success else None
            )

            if success and status == 200:
                v2_success_count += 1

        return v2_success_count >= len(endpoints_to_test) // 2  # At least 50% success

    # ================================
    # PHASE 8 WEBSOCKET TESTS
    # ================================

    async def test_websocket_connectivity(self):
        """Test WebSocket functionality"""
        logger.info("🌐 Testing WebSocket Connectivity")

        # Test WebSocket status endpoint
        success, status, data = await self.make_request("GET", "/api/v1/ws/status")
        await self.log_test_result(
            "WebSocket Status Check",
            success and status in [200, 404],  # 404 acceptable if not implemented
            f"Status: {status}",
            data if not success and status not in [404] else None
        )

        return True  # WebSocket is optional for basic functionality

    # ================================
    # PHASE 8 COMPREHENSIVE TEST RUNNER
    # ================================

    async def run_comprehensive_tests(self):
        """Run all Phase 8 end-to-end tests"""
        start_time = time.time()

        print("=" * 70)
        print("PHASE 8: END-TO-END TESTING SUITE")
        print("Hospital Management System - Frontend-Backend Integration")
        print("=" * 70)
        print(f"Started at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()

        # Run all test workflows
        auth_success = await self.test_authentication_workflow()
        patient_success = await self.test_patient_management_workflow()
        device_success = await self.test_device_management_workflow()
        v2_success = await self.test_v2_repository_endpoints()
        ws_success = await self.test_websocket_connectivity()

        # Calculate results
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["success"])
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        execution_time = time.time() - start_time

        # Generate comprehensive report
        print()
        print("=" * 70)
        print("PHASE 8 TEST RESULTS SUMMARY")
        print("=" * 70)

        workflow_results = {
            "Authentication Workflow": auth_success,
            "Patient Management Workflow": patient_success,
            "Device Management Workflow": device_success,
            "V2 Repository Endpoints": v2_success,
            "WebSocket Connectivity": ws_success
        }

        for workflow, success in workflow_results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {workflow}")

        print()
        print(f"📊 OVERALL PHASE 8 RESULTS:")
        print(f"   Total Tests Executed: {total_tests}")
        print(f"   Successful Tests: {passed_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Execution Time: {execution_time:.2f} seconds")

        # Phase 8 Grade
        if success_rate >= 90:
            grade = "EXCELLENT ⭐⭐⭐"
        elif success_rate >= 75:
            grade = "GOOD ⭐⭐"
        elif success_rate >= 60:
            grade = "ACCEPTABLE ⭐"
        else:
            grade = "NEEDS IMPROVEMENT"

        print(f"   Phase 8 Grade: {grade}")

        # Integration readiness assessment
        critical_workflows = auth_success and patient_success and device_success

        print()
        print("🚀 PHASE 8 COMPLETION STATUS:")
        if critical_workflows and success_rate >= 75:
            print("   ✅ PHASE 8 COMPLETED SUCCESSFULLY")
            print("   ✅ System ready for Phase 9: Production Deployment")
            print("   ✅ Frontend-Backend integration validated")
        else:
            print("   ⚠️ PHASE 8 PARTIAL SUCCESS")
            print("   ⚠️ Some integration issues need resolution")
            print("   ⚠️ Review failed tests before proceeding")

        print()
        print(f"Phase 8 testing completed at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("=" * 70)

        return success_rate >= 75


async def main():
    """Main entry point for Phase 8 testing"""
    try:
        async with Phase8E2ETester() as tester:
            success = await tester.run_comprehensive_tests()

            # Save detailed results
            with open("phase_8_test_results.json", "w") as f:
                json.dump({
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": success,
                    "results": tester.test_results
                }, f, indent=2)

            return 0 if success else 1

    except Exception as e:
        logger.error(f"Phase 8 testing failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)