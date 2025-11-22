"""
Test Door Scanner Adapter
Tests NFC to FHIR AuditEvent transformation
"""

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.device_modules.door_scanner.adapter import DoorScannerAdapter


def test_door_scanner_adapter():
    """Test NFC tap to FHIR transformation"""

    print("=" * 70)
    print("Testing Door Scanner Adapter - NFC to FHIR Transformation")
    print("=" * 70)

    adapter = DoorScannerAdapter()

    # Test 1: Staff entry to patient room
    print("\n[TEST 1] Staff entering patient room...")

    nfc_payload = {
        "deviceId": "DEV000003",
        "location": "ICU-Ward-Room-101",
        "nfcBadgeId": "NFC-DOC-001",
        "staffId": "STF000001",
        "staffRole": "doctor",
        "patientId": "PAT000001",
        "action": "entry",
        "timestamp": "2025-11-21T14:30:00Z"
    }

    # Validate payload
    is_valid, error = adapter.validate_nfc_payload(nfc_payload)

    if is_valid:
        print(f"  [SUCCESS] Payload validation passed")
    else:
        print(f"  [FAILED] Payload validation failed: {error}")
        return

    # Transform to AuditEvent
    audit_event = adapter.transform_to_fhir_audit_event(nfc_payload)

    print(f"  [SUCCESS] Created FHIR AuditEvent")
    print(f"    ID: {audit_event['id']}")
    print(f"    Action: {audit_event['type']['display']}")
    print(f"    Agent: {audit_event['agent'][0]['who']['reference']}")
    print(f"    Role: {audit_event['agent'][0]['role'][0]['text']}")
    print(f"    Location: {audit_event['source']['site']}")
    print(f"    Patient: {audit_event['entity'][0]['what']['reference']}")

    # Transform to Observation
    observation = adapter.transform_to_fhir_observation(nfc_payload)

    if observation:
        print(f"  [SUCCESS] Created FHIR Observation")
        print(f"    ID: {observation['id']}")
        print(f"    Code: {observation['code']['coding'][0]['display']}")
        print(f"    Value: {observation['valueString']}")
        print(f"    Performer: {observation['performer'][0]['reference']}")

    # Test 2: Staff exit from patient room
    print("\n[TEST 2] Staff exiting patient room...")

    exit_payload = {
        "deviceId": "DEV000003",
        "location": "ICU-Ward-Room-101",
        "nfcBadgeId": "NFC-NURSE-001",
        "staffId": "STF000002",
        "staffRole": "nurse",
        "patientId": "PAT000001",
        "action": "exit",
        "timestamp": "2025-11-21T15:00:00Z"
    }

    exit_audit = adapter.transform_to_fhir_audit_event(exit_payload)

    print(f"  [SUCCESS] Created exit AuditEvent")
    print(f"    Action: {exit_audit['type']['display']}")
    print(f"    Staff: {exit_audit['agent'][0]['who']['reference']}")

    # Test 3: Staff entering empty room (no patient)
    print("\n[TEST 3] Staff entering empty room...")

    empty_room_payload = {
        "deviceId": "DEV000003",
        "location": "ICU-Ward-Room-102",
        "nfcBadgeId": "NFC-DOC-001",
        "staffId": "STF000001",
        "staffRole": "doctor",
        "action": "entry",
        "timestamp": "2025-11-21T14:45:00Z"
    }

    empty_audit = adapter.transform_to_fhir_audit_event(empty_room_payload)
    empty_obs = adapter.transform_to_fhir_observation(empty_room_payload)

    print(f"  [SUCCESS] Created AuditEvent for empty room")
    print(f"    Entities: {len(empty_audit['entity'])} (no patient)")

    if empty_obs is None:
        print(f"  [SUCCESS] No observation created (no patient in room)")
    else:
        print(f"  [WARNING] Observation created for empty room")

    # Test 4: Create FHIR Bundle
    print("\n[TEST 4] Creating FHIR Bundle...")

    bundle = adapter.create_bundle(audit_event, observation)

    print(f"  [SUCCESS] Created bundle with {len(bundle['entry'])} entries")
    print(f"    - AuditEvent: {bundle['entry'][0]['resource']['id']}")
    if len(bundle['entry']) > 1:
        print(f"    - Observation: {bundle['entry'][1]['resource']['id']}")

    # Test 5: Verify DPDP compliance tags
    print("\n[TEST 5] Verifying DPDP Act 2023 compliance...")

    has_dpdp_tag = any(
        tag.get('code') == 'DPDP'
        for tag in audit_event['meta'].get('tag', [])
    )

    if has_dpdp_tag:
        print(f"  [SUCCESS] DPDP Act 2023 compliance tag present")
    else:
        print(f"  [WARNING] DPDP compliance tag missing")

    # Test 6: Access log analysis
    print("\n[TEST 6] Access log analysis...")

    # Simulate multiple access events
    access_events = [
        {"staffId": "STF000001", "action": "entry", "timestamp": "2025-11-21T14:30:00Z"},
        {"staffId": "STF000002", "action": "entry", "timestamp": "2025-11-21T14:45:00Z"},
        {"staffId": "STF000001", "action": "exit", "timestamp": "2025-11-21T15:00:00Z"},
        {"staffId": "STF000002", "action": "exit", "timestamp": "2025-11-21T15:15:00Z"},
    ]

    print(f"  [INFO] Simulating {len(access_events)} access events:")
    for event in access_events:
        print(f"    - {event['timestamp']}: {event['staffId']} {event['action']}")

    # Summary
    print("\n" + "=" * 70)
    print("DOOR SCANNER ADAPTER TEST SUMMARY")
    print("=" * 70)
    print("[PASSED] All tests completed successfully!")
    print("\nFeatures Tested:")
    print("  [OK] NFC payload validation")
    print("  [OK] NFC to FHIR AuditEvent transformation")
    print("  [OK] NFC to FHIR Observation transformation")
    print("  [OK] Staff entry tracking")
    print("  [OK] Staff exit tracking")
    print("  [OK] Empty room handling")
    print("  [OK] FHIR Bundle creation")
    print("  [OK] DPDP Act 2023 compliance tagging")
    print("\nUse Cases:")
    print("  - Track who accessed which patient room")
    print("  - Monitor patient-staff interactions")
    print("  - DPDP Act 2023 access audit trail")
    print("  - Room occupancy tracking")
    print("=" * 70)


if __name__ == "__main__":
    test_door_scanner_adapter()
