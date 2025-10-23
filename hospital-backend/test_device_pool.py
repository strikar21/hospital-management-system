"""
Device Pool Testing Script
Automated testing of ESP32 watches and device management system
"""
import requests
import json
from datetime import datetime
from typing import Optional, Dict, Any

# API Base URL
BASE_URL = "http://localhost:8001"

# Test configuration
ADMIN_STAFF_ID = "ADM0001"
ADMIN_PASSWORD = "admin123"

class DevicePoolTester:
    def __init__(self):
        self.token: Optional[str] = None
        self.results = []

    def log(self, message: str, status: str = "INFO"):
        """Log test result"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "[INFO]",
            "SUCCESS": "[OK]",
            "ERROR": "[ERROR]",
            "WARNING": "[WARN]"
        }.get(status, "[•]")
        print(f"[{timestamp}] {prefix} {message}")
        self.results.append({"timestamp": timestamp, "status": status, "message": message})

    def login(self) -> bool:
        """Authenticate with the API"""
        self.log("Attempting login as admin...")
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={"staffId": ADMIN_STAFF_ID, "password": ADMIN_PASSWORD},
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                data = response.json()
                # Check for both old format (success/token) and new format (accessToken)
                if data.get("success") and data.get("token"):
                    self.token = data.get("token")
                    user = data.get("user", {})
                    self.log(f"Login successful - {user.get('name')} ({user.get('role')})", "SUCCESS")
                    return True
                elif data.get("accessToken"):
                    self.token = data.get("accessToken")
                    name = f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
                    role = data.get('role', 'Unknown')
                    self.log(f"Login successful - {name} ({role})", "SUCCESS")
                    return True

            self.log(f"Login failed: {response.status_code} - {response.text}", "ERROR")
            return False

        except Exception as e:
            self.log(f"Login error: {str(e)}", "ERROR")
            return False

    def get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def test_health(self) -> bool:
        """Test backend health"""
        self.log("Testing backend health...")
        try:
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                self.log(f"Backend healthy - DB: {data.get('database')}, Version: {data.get('version')}", "SUCCESS")
                return True
            else:
                self.log(f"Health check failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Health check error: {str(e)}", "ERROR")
            return False

    def test_all_devices(self) -> Optional[Dict[str, Any]]:
        """Test: Get all devices"""
        self.log("\\nTEST: Getting all devices...")
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/devices/",
                headers=self.get_headers(),
                params={"limit": 100}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    devices = data.get("devices", [])
                    summary = data.get("summary", {})
                    self.log(f"Found {len(devices)} devices", "SUCCESS")

                    # Print summary
                    for device_type, statuses in summary.items():
                        total = sum(statuses.values())
                        self.log(f"  {device_type}: {total} total - {dict(statuses)}")

                    return data
                else:
                    self.log(f"API returned success=false", "ERROR")
            else:
                self.log(f"Failed: {response.status_code} - {response.text}", "ERROR")

        except Exception as e:
            self.log(f"Error: {str(e)}", "ERROR")
        return None

    def test_available_watches(self) -> Optional[Dict[str, Any]]:
        """Test: Get available watches"""
        self.log("\\nTEST: Getting available watches...")
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/watchmanagement/available",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    watches = data.get("availableWatches", [])
                    self.log(f"Found {len(watches)} available watches", "SUCCESS")

                    for i, watch in enumerate(watches, 1):
                        status = watch.get('connectionStatus', 'unknown')
                        battery = watch.get('batteryLevel', 'N/A')
                        self.log(f"  {i}. {watch.get('id')} - {watch.get('serialNumber')} - Battery: {battery}% - Status: {status}")

                    return data
                else:
                    self.log(f"API returned success=false", "ERROR")
            else:
                self.log(f"Failed: {response.status_code} - {response.text}", "ERROR")

        except Exception as e:
            self.log(f"Error: {str(e)}", "ERROR")
        return None

    def test_assigned_watches(self) -> Optional[Dict[str, Any]]:
        """Test: Get assigned watches"""
        self.log("\\nTEST: Getting assigned watches...")
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/watchmanagement/assigned",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    watches = data.get("assignedWatches", [])
                    self.log(f"Found {len(watches)} assigned watches", "SUCCESS")

                    for i, watch in enumerate(watches, 1):
                        patient = watch.get('patientName', 'Unknown')
                        location = watch.get('location', 'Unknown')
                        status = watch.get('connectionStatus', 'unknown')
                        self.log(f"  {i}. {watch.get('id')} → {patient} at {location} - Status: {status}")

                    return data
                else:
                    self.log(f"API returned success=false", "ERROR")
            else:
                self.log(f"Failed: {response.status_code} - {response.text}", "ERROR")

        except Exception as e:
            self.log(f"Error: {str(e)}", "ERROR")
        return None

    def test_watch_connection_status(self) -> Optional[Dict[str, Any]]:
        """Test: Get watch connection status"""
        self.log("\\nTEST: Getting watch connection status...")
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/watchmanagement/connection-status",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    summary = data.get("summary", {})
                    self.log(f"Watch Connection Summary:", "SUCCESS")
                    self.log(f"  Total: {summary.get('total', 0)}")
                    self.log(f"  Connected: {summary.get('connected', 0)}")
                    self.log(f"  Recently Seen: {summary.get('recentlySeen', 0)}")
                    self.log(f"  Offline: {summary.get('offline', 0)}")

                    return data
                else:
                    self.log(f"API returned success=false", "ERROR")
            else:
                self.log(f"Failed: {response.status_code} - {response.text}", "ERROR")

        except Exception as e:
            self.log(f"Error: {str(e)}", "ERROR")
        return None

    def test_watch_alerts(self) -> Optional[Dict[str, Any]]:
        """Test: Get watch alerts"""
        self.log("\\nTEST: Getting watch alerts...")
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/watchmanagement/alerts",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    alerts = data.get("alerts", [])
                    if alerts:
                        self.log(f"Found {len(alerts)} watch alerts", "WARNING")
                        for i, alert in enumerate(alerts, 1):
                            alert_type = alert.get('type', 'unknown')
                            severity = alert.get('severity', 'unknown')
                            message = alert.get('message', 'No message')
                            self.log(f"  {i}. [{severity.upper()}] {alert_type}: {message}")
                    else:
                        self.log(f"No watch alerts found", "SUCCESS")

                    return data
                else:
                    self.log(f"API returned success=false", "ERROR")
            else:
                self.log(f"Failed: {response.status_code} - {response.text}", "ERROR")

        except Exception as e:
            self.log(f"Error: {str(e)}", "ERROR")
        return None

    def test_device_health(self) -> Optional[Dict[str, Any]]:
        """Test: Get device health status"""
        self.log("\\nTEST: Getting device health status...")
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/devices/status/health",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    overall = data.get("overallHealth", {})
                    self.log(f"Overall Device Health:", "SUCCESS")
                    self.log(f"  Total Devices: {overall.get('totalDevices', 0)}")
                    self.log(f"  Online: {overall.get('onlineDevices', 0)}")
                    self.log(f"  Offline: {overall.get('offlineDevices', 0)}")
                    self.log(f"  Health %: {overall.get('healthPercentage', 0)}%")

                    by_type = data.get("byDeviceType", {})
                    for device_type, stats in by_type.items():
                        self.log(f"  {device_type}: {stats}")

                    return data
                else:
                    self.log(f"API returned success=false", "ERROR")
            else:
                self.log(f"Failed: {response.status_code} - {response.text}", "ERROR")

        except Exception as e:
            self.log(f"Error: {str(e)}", "ERROR")
        return None

    def run_all_tests(self):
        """Run all device pool tests"""
        print("=" * 80)
        print("DEVICE POOL TESTING")
        print("=" * 80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")

        # Test 1: Health check
        if not self.test_health():
            self.log("Backend not healthy - aborting tests", "ERROR")
            return

        # Test 2: Login
        if not self.login():
            self.log("Authentication failed - aborting tests", "ERROR")
            return

        # Test 3-8: Device pool tests
        self.test_all_devices()
        self.test_available_watches()
        self.test_assigned_watches()
        self.test_watch_connection_status()
        self.test_watch_alerts()
        self.test_device_health()

        # Summary
        print("\\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        success_count = len([r for r in self.results if r["status"] == "SUCCESS"])
        error_count = len([r for r in self.results if r["status"] == "ERROR"])
        warning_count = len([r for r in self.results if r["status"] == "WARNING"])

        print(f"Total Tests: {len(self.results)}")
        print(f"Success: {success_count}")
        print(f"Errors: {error_count}")
        print(f"Warnings: {warning_count}")
        print(f"\\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

if __name__ == "__main__":
    tester = DevicePoolTester()
    tester.run_all_tests()
