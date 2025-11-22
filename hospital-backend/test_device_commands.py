"""
Test Device Commands

Simple script to test sending commands to ESP32 devices
"""

import httpx
import json
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8000"
DEVICE_ID = "DEV000001"
PATIENT_ID = "PAT000001"


def test_assign_device():
    """Test assigning device to patient"""
    print("\n" + "=" * 70)
    print("TEST 1: Assign Device to Patient")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/assign",
            json={
                "device_id": DEVICE_ID,
                "patient_id": PATIENT_ID
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("[OK] Device assigned successfully!")
        else:
            print("[ERROR] Failed to assign device")


def test_ping_device():
    """Test pinging device"""
    print("\n" + "=" * 70)
    print("TEST 2: Ping Device (Health Check)")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/ping",
            json={
                "device_id": DEVICE_ID
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            result = response.json()
            print(f"[OK] Ping command sent! Command ID: {result.get('command_id')}")
            print("\n💡 TIP: Subscribe to acknowledgments:")
            print(f"   mosquitto_sub -h localhost -t 'hospital/devices/{DEVICE_ID}/ack' -v")
        else:
            print("[ERROR] Failed to send ping")


def test_calibrate_device():
    """Test calibrating device waveform"""
    print("\n" + "=" * 70)
    print("TEST 3: Calibrate Device Waveform (ECG/EEG)")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/calibrate",
            json={
                "device_id": DEVICE_ID
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            result = response.json()
            print(f"[OK] Calibration command sent! Command ID: {result.get('command_id')}")
            print("\n💡 TIP: Device will:")
            print("   - Generate 3-second 100μV calibration pulse")
            print("   - Send acknowledgment when complete")
        else:
            print("[ERROR] Failed to send calibration command")


def test_unassign_device():
    """Test unassigning device from patient"""
    print("\n" + "=" * 70)
    print("TEST 4: Unassign Device from Patient")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/unassign",
            json={
                "device_id": DEVICE_ID
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("[OK] Device unassigned successfully!")
        else:
            print("[ERROR] Failed to unassign device")


def test_custom_command():
    """Test sending custom command"""
    print("\n" + "=" * 70)
    print("TEST 5: Send Custom Command (Set Display Brightness)")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/command",
            json={
                "device_id": DEVICE_ID,
                "command_type": "setDisplayBrightness",
                "parameters": {
                    "brightness": 75
                }
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            result = response.json()
            print(f"[OK] Custom command sent! Command ID: {result.get('command_id')}")
        else:
            print("[ERROR] Failed to send custom command")


# ====================================
# CONFIGURATION COMMANDS
# ====================================

def test_display_brightness():
    """Test setting display brightness"""
    print("\n" + "=" * 70)
    print("TEST 6: Set Display Brightness")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/display-brightness",
            json={
                "device_id": DEVICE_ID,
                "brightness": 50
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("[OK] Display brightness command sent!")
        else:
            print("[ERROR] Failed to set brightness")


def test_waveform_streaming():
    """Test enabling waveform streaming"""
    print("\n" + "=" * 70)
    print("TEST 7: Enable Waveform Streaming")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/waveform-streaming",
            json={
                "device_id": DEVICE_ID,
                "enabled": True
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("[OK] Waveform streaming enabled!")
            print("\n💡 TIP: Subscribe to waveform data:")
            print(f"   mosquitto_sub -h localhost -t 'hospital/devices/{DEVICE_ID}/stream' -v")
        else:
            print("[ERROR] Failed to enable waveform streaming")


def test_sampling_rate():
    """Test setting sampling rate"""
    print("\n" + "=" * 70)
    print("TEST 8: Set Sampling Rate")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/sampling-rate",
            json={
                "device_id": DEVICE_ID,
                "sampling_rate_hz": 500
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("[OK] Sampling rate set to 500 Hz!")
        else:
            print("[ERROR] Failed to set sampling rate")


def test_vitals_interval():
    """Test setting vitals interval"""
    print("\n" + "=" * 70)
    print("TEST 9: Set Vitals Transmission Interval")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/vitals-interval",
            json={
                "device_id": DEVICE_ID,
                "interval_seconds": 5
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("[OK] Vitals interval set to 5 seconds!")
        else:
            print("[ERROR] Failed to set vitals interval")


def test_debug_mode():
    """Test enabling debug mode"""
    print("\n" + "=" * 70)
    print("TEST 10: Enable Debug Mode")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/debug-mode",
            json={
                "device_id": DEVICE_ID,
                "enabled": True
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("[OK] Debug mode enabled!")
            print("\n💡 TIP: Check ESP32 serial monitor for verbose logs")
        else:
            print("[ERROR] Failed to enable debug mode")


def test_alert_threshold():
    """Test setting alert threshold"""
    print("\n" + "=" * 70)
    print("TEST 11: Set Alert Threshold (Heart Rate)")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/alert-threshold",
            json={
                "device_id": DEVICE_ID,
                "vital_type": "heartRate",
                "threshold_high": 120.0,
                "threshold_low": 50.0
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("[OK] Heart rate alert threshold set!")
            print("   - High: 120 bpm")
            print("   - Low: 50 bpm")
        else:
            print("[ERROR] Failed to set alert threshold")


def test_led_alerts():
    """Test enabling LED alerts"""
    print("\n" + "=" * 70)
    print("TEST 12: Enable LED Alerts")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/led-alerts",
            json={
                "device_id": DEVICE_ID,
                "enabled": True
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("[OK] LED alerts enabled!")
        else:
            print("[ERROR] Failed to enable LED alerts")


# ====================================
# MANAGEMENT COMMANDS
# ====================================

def test_device_status():
    """Test requesting device status"""
    print("\n" + "=" * 70)
    print("TEST 13: Get Device Status")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/status",
            json={
                "device_id": DEVICE_ID
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("[OK] Status request sent!")
            print("\n💡 TIP: Subscribe to device status:")
            print(f"   mosquitto_sub -h localhost -t 'hospital/devices/{DEVICE_ID}/status' -v")
        else:
            print("[ERROR] Failed to request device status")


def test_clear_offline_queue():
    """Test clearing offline queue"""
    print("\n" + "=" * 70)
    print("TEST 14: Clear Offline Queue")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/clear-offline-queue",
            json={
                "device_id": DEVICE_ID
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("[OK] Clear offline queue command sent!")
        else:
            print("[ERROR] Failed to clear offline queue")


def test_sync_time():
    """Test syncing device time"""
    print("\n" + "=" * 70)
    print("TEST 15: Sync Device Time (NTP)")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/sync-time",
            json={
                "device_id": DEVICE_ID
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("[OK] Time sync command sent!")
        else:
            print("[ERROR] Failed to sync time")


def test_waveform_mode():
    """Test setting waveform mode"""
    print("\n" + "=" * 70)
    print("TEST 16: Set Waveform Mode (ECG)")
    print("=" * 70)

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/waveform-mode",
            json={
                "device_id": DEVICE_ID,
                "mode": "ECG"
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("[OK] Waveform mode set to ECG!")
        else:
            print("[ERROR] Failed to set waveform mode")


def test_reboot_device():
    """Test rebooting device"""
    print("\n" + "=" * 70)
    print("TEST 17: Reboot Device (ESP32 Restart)")
    print("=" * 70)
    print("⚠️  WARNING: This will reboot the device!")
    confirm = input("Type 'yes' to proceed: ")

    if confirm.lower() != 'yes':
        print("[SKIPPED] Reboot test cancelled")
        return

    with httpx.Client() as client:
        response = client.post(
            f"{API_BASE}/devices/reboot",
            json={
                "device_id": DEVICE_ID
            }
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("[OK] Reboot command sent!")
            print("\n💡 TIP: Device will restart in a few seconds")
        else:
            print("[ERROR] Failed to send reboot command")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("DEVICE COMMAND TESTING - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print(f"API Base URL: {API_BASE}")
    print(f"Device ID: {DEVICE_ID}")
    print(f"Patient ID: {PATIENT_ID}")
    print()

    print("📋 Prerequisites:")
    print("   1. FHIR API running: uvicorn app.main:app --reload")
    print("   2. Mosquitto broker running")
    print("   3. ESP32 watch connected (optional)")
    print()

    print("📝 Test Categories:")
    print("   - Basic Commands: Assign, Ping, Calibrate, Unassign")
    print("   - Configuration Commands: Display, Streaming, Sampling, Intervals, Debug")
    print("   - Alert Commands: Thresholds, LED Alerts")
    print("   - Management Commands: Status, Queue, Time Sync, Mode, Reboot")
    print()

    choice = input("Run [A]ll tests, [B]asic only, or [C]ustom? (A/B/C): ").upper()

    try:
        if choice == 'B':
            # Basic tests only
            test_assign_device()
            input("\nPress Enter for next test...")
            test_ping_device()
            input("\nPress Enter for next test...")
            test_calibrate_device()
            input("\nPress Enter for next test...")
            test_custom_command()
            input("\nPress Enter for next test...")
            test_unassign_device()

        elif choice == 'C':
            # Custom test selection
            print("\nSelect tests to run:")
            print("1. Assign Device")
            print("2. Ping Device")
            print("3. Calibrate Device")
            print("4. Unassign Device")
            print("5. Custom Command")
            print("6. Display Brightness")
            print("7. Waveform Streaming")
            print("8. Sampling Rate")
            print("9. Vitals Interval")
            print("10. Debug Mode")
            print("11. Alert Threshold")
            print("12. LED Alerts")
            print("13. Device Status")
            print("14. Clear Offline Queue")
            print("15. Sync Time")
            print("16. Waveform Mode")
            print("17. Reboot Device")
            tests = input("\nEnter test numbers (comma-separated, e.g., 1,2,3): ")

            test_map = {
                '1': test_assign_device,
                '2': test_ping_device,
                '3': test_calibrate_device,
                '4': test_unassign_device,
                '5': test_custom_command,
                '6': test_display_brightness,
                '7': test_waveform_streaming,
                '8': test_sampling_rate,
                '9': test_vitals_interval,
                '10': test_debug_mode,
                '11': test_alert_threshold,
                '12': test_led_alerts,
                '13': test_device_status,
                '14': test_clear_offline_queue,
                '15': test_sync_time,
                '16': test_waveform_mode,
                '17': test_reboot_device
            }

            for test_num in tests.split(','):
                test_num = test_num.strip()
                if test_num in test_map:
                    test_map[test_num]()
                    if test_num != tests.split(',')[-1].strip():
                        input("\nPress Enter for next test...")

        else:  # 'A' or default - run all tests
            print("\n🚀 Running ALL tests...")
            input("Press Enter to start...")

            # Basic commands
            test_assign_device()
            input("\nPress Enter for next test...")

            test_ping_device()
            input("\nPress Enter for next test...")

            test_calibrate_device()
            input("\nPress Enter for next test...")

            test_custom_command()
            input("\nPress Enter for next test...")

            # Configuration commands
            test_display_brightness()
            input("\nPress Enter for next test...")

            test_waveform_streaming()
            input("\nPress Enter for next test...")

            test_sampling_rate()
            input("\nPress Enter for next test...")

            test_vitals_interval()
            input("\nPress Enter for next test...")

            test_debug_mode()
            input("\nPress Enter for next test...")

            test_alert_threshold()
            input("\nPress Enter for next test...")

            test_led_alerts()
            input("\nPress Enter for next test...")

            # Management commands
            test_device_status()
            input("\nPress Enter for next test...")

            test_clear_offline_queue()
            input("\nPress Enter for next test...")

            test_sync_time()
            input("\nPress Enter for next test...")

            test_waveform_mode()
            input("\nPress Enter for next test...")

            test_reboot_device()
            input("\nPress Enter for next test...")

            test_unassign_device()

        print("\n" + "=" * 70)
        print("ALL TESTS COMPLETE!")
        print("=" * 70)
        print()
        print("📊 Summary of Available Commands:")
        print("   ✓ Device Assignment/Unassignment")
        print("   ✓ Health Check (Ping)")
        print("   ✓ Waveform Calibration")
        print("   ✓ Display Brightness Control")
        print("   ✓ Waveform Streaming Control")
        print("   ✓ Sampling Rate Configuration")
        print("   ✓ Vitals Transmission Interval")
        print("   ✓ Debug Mode Toggle")
        print("   ✓ Alert Threshold Configuration")
        print("   ✓ LED Alert Control")
        print("   ✓ Device Status Request")
        print("   ✓ Offline Queue Management")
        print("   ✓ Time Synchronization")
        print("   ✓ Waveform Mode (ECG/EEG)")
        print("   ✓ Device Reboot")
        print()
        print("💡 Next Steps:")
        print("   1. Check ESP32 serial monitor for command reception")
        print("   2. Monitor MQTT broker: mosquitto_sub -h localhost -t '#' -v")
        print("   3. Check device acknowledgments: mosquitto_sub -h localhost -t 'hospital/devices/+/ack' -v")
        print("   4. View API documentation: http://localhost:8000/docs")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Is the FHIR API running?")
        print("   - Is Mosquitto running?")
        print("   - Check the API base URL")
        print("   - Verify device ID exists in database")


if __name__ == "__main__":
    main()
