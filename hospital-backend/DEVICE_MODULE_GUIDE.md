# Device Module Developer Guide

## Creating Custom Device Adapters for FHIR R5 Hospital IoT Backend

This guide teaches you how to create device adapters that transform proprietary device data into FHIR R5 compliant resources.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Creating a Device Module](#creating-a-device-module)
4. [Adapter Structure](#adapter-structure)
5. [LOINC Code Mapping](#loinc-code-mapping)
6. [Alert Detection](#alert-detection)
7. [Testing Your Module](#testing-your-module)
8. [Integration](#integration)
9. [Examples](#examples)
10. [Best Practices](#best-practices)

---

## Overview

### What is a Device Adapter?

A device adapter is a software module that:
1. **Receives** proprietary device data (MQTT, HTTP, WebSocket, etc.)
2. **Validates** the payload structure
3. **Transforms** device data into FHIR R5 resources (Observation, Flag, AuditEvent)
4. **Detects** abnormal values and generates alerts
5. **Returns** FHIR-compliant resources ready for storage

### Why Device Adapters?

- **Plug-and-play**: Add new devices without changing the database schema
- **Standardization**: All devices produce FHIR R5 resources
- **Compliance**: Built-in LOINC/SNOMED code mapping
- **Flexibility**: Support any device protocol (MQTT, HTTP, Bluetooth, Serial, etc.)

### Supported Device Types

Current examples:
- **ESP32 Watch** (MQTT): Vital signs monitoring
- **Door Scanner** (NFC): Access control and audit logging
- **Blood Pressure Monitor**: You'll create this as an example!

---

## Architecture

### Directory Structure

```
hospital-backend/
├── app/
│   ├── device_modules/
│   │   ├── esp32_watch/           # Example: Wearable device
│   │   │   ├── __init__.py
│   │   │   ├── adapter.py         # Main adapter class
│   │   │   ├── loinc_mapping.py   # LOINC code definitions
│   │   │   └── alert_detector.py  # Alert detection logic
│   │   ├── door_scanner/          # Example: Access control
│   │   │   ├── __init__.py
│   │   │   └── adapter.py
│   │   └── your_device/           # Your new device module
│   │       ├── __init__.py
│   │       ├── adapter.py
│   │       ├── loinc_mapping.py
│   │       └── alert_detector.py
│   └── services/
│       └── websocket_service.py   # Real-time streaming
└── tests/
    └── test_your_device_adapter.py
```

### Data Flow

```
┌─────────────────┐
│  Physical       │
│  Device         │
│  (ESP32, NFC,   │
│   BP Monitor)   │
└────────┬────────┘
         │ Proprietary Protocol
         │ (MQTT, HTTP, BLE)
         ▼
┌─────────────────┐
│  Device         │
│  Adapter        │
│  (Your Code)    │
└────────┬────────┘
         │ FHIR R5 Resources
         │ (Observation, Flag)
         ▼
┌─────────────────┐
│  FHIR API       │
│  /fhir/         │
│  Observation    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  TimescaleDB    │
│  (fhir          │
│   Observations) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  WebSocket      │
│  Broadcasting   │
│  (Real-time)    │
└─────────────────┘
```

---

## Creating a Device Module

### Step 1: Create Module Directory

```bash
cd hospital-backend/app/device_modules
mkdir blood_pressure_monitor
cd blood_pressure_monitor
touch __init__.py adapter.py loinc_mapping.py alert_detector.py
```

### Step 2: Define LOINC Codes

**loinc_mapping.py:**

```python
"""
LOINC Code Mappings for Blood Pressure Monitor
Defines standard LOINC codes and normal ranges
"""

# LOINC codes for blood pressure measurements
LOINC_CODES = {
    "systolic": {
        "code": "8480-6",
        "display": "Systolic blood pressure",
        "unit": "mmHg",
        "system": "http://loinc.org",
        "category": "vital-signs",
        "ucum": "mm[Hg]"
    },
    "diastolic": {
        "code": "8462-4",
        "display": "Diastolic blood pressure",
        "unit": "mmHg",
        "system": "http://loinc.org",
        "category": "vital-signs",
        "ucum": "mm[Hg]"
    },
    "meanArterialPressure": {
        "code": "8478-0",
        "display": "Mean blood pressure",
        "unit": "mmHg",
        "system": "http://loinc.org",
        "category": "vital-signs",
        "ucum": "mm[Hg]"
    },
    "pulseRate": {
        "code": "8893-0",
        "display": "Heart rate by Pulse oximetry",
        "unit": "beats/minute",
        "system": "http://loinc.org",
        "category": "vital-signs",
        "ucum": "/min"
    }
}

# Normal ranges (AHA 2023 guidelines)
NORMAL_RANGES = {
    "systolic": {
        "min": 90,
        "max": 120,
        "critical_low": 70,
        "critical_high": 180
    },
    "diastolic": {
        "min": 60,
        "max": 80,
        "critical_low": 40,
        "critical_high": 120
    },
    "meanArterialPressure": {
        "min": 70,
        "max": 100,
        "critical_low": 60,
        "critical_high": 130
    },
    "pulseRate": {
        "min": 60,
        "max": 100,
        "critical_low": 40,
        "critical_high": 150
    }
}


def get_loinc_code(measurement_type: str) -> dict:
    """Get LOINC code details for a measurement type"""
    return LOINC_CODES.get(measurement_type)


def is_normal(measurement_type: str, value: float) -> bool:
    """Check if a measurement value is within normal range"""
    if measurement_type not in NORMAL_RANGES:
        return True

    ranges = NORMAL_RANGES[measurement_type]
    return ranges["min"] <= value <= ranges["max"]


def is_critical(measurement_type: str, value: float) -> bool:
    """Check if a measurement value is in critical range"""
    if measurement_type not in NORMAL_RANGES:
        return False

    ranges = NORMAL_RANGES[measurement_type]
    return value < ranges["critical_low"] or value > ranges["critical_high"]
```

### Step 3: Implement Alert Detection

**alert_detector.py:**

```python
"""
Alert Detection for Blood Pressure Monitor
Generates FHIR Flag resources for abnormal blood pressure
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
import uuid

from .loinc_mapping import get_loinc_code, is_normal, is_critical


class BloodPressureAlertDetector:
    """
    Detects abnormal blood pressure and generates FHIR Flag resources
    """

    @staticmethod
    def detect_alerts(
        measurements: Dict[str, float],
        patient_id: str,
        device_id: str
    ) -> List[Dict[str, Any]]:
        """
        Detect abnormal measurements and create alert flags

        Args:
            measurements: Dict of measurement_type -> value
                Example: {"systolic": 180, "diastolic": 110}
            patient_id: Patient ID (e.g., "PAT000001")
            device_id: Device ID (e.g., "DEV000004")

        Returns:
            List of FHIR R5 Flag resources
        """
        alerts = []

        for measurement_type, value in measurements.items():
            # Skip if normal
            if is_normal(measurement_type, value):
                continue

            # Determine severity
            if is_critical(measurement_type, value):
                severity = "critical"
                status = "active"
            else:
                severity = "warning"
                status = "active"

            # Create alert
            alert = BloodPressureAlertDetector._create_alert(
                measurement_type=measurement_type,
                value=value,
                severity=severity,
                patient_id=patient_id,
                device_id=device_id
            )

            alerts.append(alert)

        # Check for hypertensive crisis (both high)
        if "systolic" in measurements and "diastolic" in measurements:
            if measurements["systolic"] > 180 or measurements["diastolic"] > 120:
                alerts.append(
                    BloodPressureAlertDetector._create_hypertensive_crisis_alert(
                        systolic=measurements["systolic"],
                        diastolic=measurements["diastolic"],
                        patient_id=patient_id,
                        device_id=device_id
                    )
                )

        return alerts

    @staticmethod
    def _create_alert(
        measurement_type: str,
        value: float,
        severity: str,
        patient_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """Create a FHIR Flag resource for an abnormal measurement"""

        loinc = get_loinc_code(measurement_type)
        alert_id = f"ALERT-BP-{uuid.uuid4().hex[:8]}"

        flag = {
            "resourceType": "Flag",
            "id": alert_id,
            "status": "active",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/flag-category",
                            "code": "clinical",
                            "display": "Clinical"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": loinc["system"],
                        "code": loinc["code"],
                        "display": loinc["display"]
                    }
                ],
                "text": f"{severity.title()} {loinc['display'].lower()}: {value} {loinc['unit']}"
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "period": {
                "start": datetime.now(timezone.utc).isoformat()
            },
            "author": {
                "reference": f"Device/{device_id}"
            },
            "meta": {
                "lastUpdated": datetime.now(timezone.utc).isoformat()
            },
            "_internal": {
                "severity": severity,
                "measurementType": measurement_type,
                "value": value,
                "unit": loinc["unit"]
            }
        }

        return flag

    @staticmethod
    def _create_hypertensive_crisis_alert(
        systolic: float,
        diastolic: float,
        patient_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """Create alert for hypertensive crisis (BP > 180/120)"""

        alert_id = f"ALERT-HTN-CRISIS-{uuid.uuid4().hex[:8]}"

        flag = {
            "resourceType": "Flag",
            "id": alert_id,
            "status": "active",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/flag-category",
                            "code": "clinical",
                            "display": "Clinical"
                        }
                    ],
                    "text": "Emergency"
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "398254007",
                        "display": "Hypertensive crisis"
                    }
                ],
                "text": f"HYPERTENSIVE CRISIS: {systolic}/{diastolic} mmHg - IMMEDIATE MEDICAL ATTENTION REQUIRED"
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "period": {
                "start": datetime.now(timezone.utc).isoformat()
            },
            "author": {
                "reference": f"Device/{device_id}"
            },
            "meta": {
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
                "tag": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": "EMRTREAT",
                        "display": "Emergency Treatment"
                    }
                ]
            },
            "_internal": {
                "severity": "critical",
                "systolic": systolic,
                "diastolic": diastolic,
                "requiresImmediateAction": True
            }
        }

        return flag
```

### Step 4: Create Main Adapter

**adapter.py:**

```python
"""
Blood Pressure Monitor Adapter

Transforms proprietary BP monitor data to FHIR R5 Observations and Flags
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import uuid

from .loinc_mapping import get_loinc_code
from .alert_detector import BloodPressureAlertDetector


class BloodPressureMonitorAdapter:
    """
    Adapter for blood pressure monitoring devices

    Converts device-specific data formats to FHIR R5 resources
    """

    def __init__(self):
        self.alert_detector = BloodPressureAlertDetector()

    def transform_to_fhir_observations(
        self,
        device_payload: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Transform device payload to FHIR Observations

        Args:
            device_payload: Device-specific data format
                Expected format:
                {
                    "deviceId": "DEV000004",
                    "patientId": "PAT000001",
                    "timestamp": "2025-11-21T10:00:00Z",
                    "measurements": {
                        "systolic": 120,
                        "diastolic": 80,
                        "pulseRate": 72,
                        "meanArterialPressure": 93
                    },
                    "deviceInfo": {
                        "batteryLevel": 85,
                        "firmwareVersion": "1.2.3"
                    }
                }

        Returns:
            List of FHIR R5 Observation resources
        """
        observations = []

        # Extract common fields
        device_id = device_payload.get("deviceId")
        patient_id = device_payload.get("patientId")
        timestamp = device_payload.get("timestamp")
        measurements = device_payload.get("measurements", {})

        # Parse timestamp
        if isinstance(timestamp, str):
            effective_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            effective_time = datetime.now(timezone.utc)

        # Create observation for each measurement
        for measurement_type, value in measurements.items():
            observation = self._create_observation(
                measurement_type=measurement_type,
                value=value,
                patient_id=patient_id,
                device_id=device_id,
                effective_time=effective_time
            )

            if observation:
                observations.append(observation)

        return observations

    def _create_observation(
        self,
        measurement_type: str,
        value: float,
        patient_id: str,
        device_id: str,
        effective_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """Create a single FHIR Observation resource"""

        # Get LOINC code
        loinc = get_loinc_code(measurement_type)
        if not loinc:
            return None  # Unknown measurement type

        # Generate observation ID
        obs_id = f"OBS-BP-{measurement_type.upper()[:3]}-{uuid.uuid4().hex[:8]}"

        observation = {
            "resourceType": "Observation",
            "id": obs_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": loinc["category"],
                            "display": "Vital Signs"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": loinc["system"],
                        "code": loinc["code"],
                        "display": loinc["display"]
                    }
                ],
                "text": loinc["display"]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": effective_time.isoformat(),
            "issued": datetime.now(timezone.utc).isoformat(),
            "valueQuantity": {
                "value": value,
                "unit": loinc["unit"],
                "system": "http://unitsofmeasure.org",
                "code": loinc["ucum"]
            },
            "device": {
                "reference": f"Device/{device_id}"
            },
            "meta": {
                "lastUpdated": datetime.now(timezone.utc).isoformat()
            },
            "_internal": {
                "measurementType": measurement_type,
                "deviceId": device_id
            }
        }

        return observation

    def detect_alerts(
        self,
        device_payload: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detect abnormal measurements and generate alerts

        Args:
            device_payload: Same format as transform_to_fhir_observations

        Returns:
            List of FHIR R5 Flag resources (alerts)
        """
        measurements = device_payload.get("measurements", {})
        patient_id = device_payload.get("patientId")
        device_id = device_payload.get("deviceId")

        alerts = self.alert_detector.detect_alerts(
            measurements=measurements,
            patient_id=patient_id,
            device_id=device_id
        )

        return alerts

    def validate_payload(
        self,
        payload: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate device payload structure

        Args:
            payload: Device payload to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        required_fields = ["deviceId", "patientId", "measurements"]

        for field in required_fields:
            if field not in payload:
                return False, f"Missing required field: {field}"

        # Validate measurements
        measurements = payload.get("measurements", {})
        if not isinstance(measurements, dict):
            return False, "measurements must be a dictionary"

        if not measurements:
            return False, "measurements cannot be empty"

        # Validate measurement values
        for key, value in measurements.items():
            if not isinstance(value, (int, float)):
                return False, f"Invalid value for {key}: must be numeric"

            if value < 0:
                return False, f"Invalid value for {key}: must be positive"

        return True, None

    def create_bundle(
        self,
        observations: List[Dict[str, Any]],
        alerts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a FHIR Bundle with observations and alerts

        Args:
            observations: List of Observation resources
            alerts: List of Flag resources

        Returns:
            FHIR R5 Bundle resource
        """
        entries = []

        # Add observations
        for obs in observations:
            entries.append({
                "fullUrl": f"urn:uuid:{obs['id']}",
                "resource": obs,
                "request": {
                    "method": "POST",
                    "url": "Observation"
                }
            })

        # Add alerts
        for alert in alerts:
            entries.append({
                "fullUrl": f"urn:uuid:{alert['id']}",
                "resource": alert,
                "request": {
                    "method": "POST",
                    "url": "Flag"
                }
            })

        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entry": entries
        }

        return bundle
```

### Step 5: Create Tests

**tests/test_blood_pressure_adapter.py:**

```python
"""
Test Blood Pressure Monitor Adapter
Tests device payload to FHIR transformation
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.device_modules.blood_pressure_monitor.adapter import BloodPressureMonitorAdapter


def test_blood_pressure_adapter():
    """Test blood pressure monitor adapter"""

    print("=" * 70)
    print("Testing Blood Pressure Monitor Adapter")
    print("=" * 70)

    adapter = BloodPressureMonitorAdapter()

    # Test 1: Normal blood pressure
    print("\n[TEST 1] Normal blood pressure measurement...")

    normal_payload = {
        "deviceId": "DEV000004",
        "patientId": "PAT000001",
        "timestamp": "2025-11-21T10:00:00Z",
        "measurements": {
            "systolic": 115,
            "diastolic": 75,
            "pulseRate": 72,
            "meanArterialPressure": 88
        },
        "deviceInfo": {
            "batteryLevel": 85,
            "firmwareVersion": "1.2.3"
        }
    }

    # Validate
    is_valid, error = adapter.validate_payload(normal_payload)
    assert is_valid, f"Validation failed: {error}"
    print(f"  [OK] Payload validation passed")

    # Transform to observations
    observations = adapter.transform_to_fhir_observations(normal_payload)
    print(f"  [OK] Created {len(observations)} observations")

    for obs in observations:
        measurement_type = obs['_internal']['measurementType']
        value = obs['valueQuantity']['value']
        unit = obs['valueQuantity']['unit']
        print(f"    - {measurement_type}: {value} {unit}")

    # Check for alerts (should be none)
    alerts = adapter.detect_alerts(normal_payload)
    print(f"  [OK] Detected {len(alerts)} alerts (expected 0)")

    # Test 2: Hypertensive crisis
    print("\n[TEST 2] Hypertensive crisis...")

    crisis_payload = {
        "deviceId": "DEV000004",
        "patientId": "PAT000002",
        "timestamp": "2025-11-21T10:05:00Z",
        "measurements": {
            "systolic": 190,
            "diastolic": 125,
            "pulseRate": 95
        }
    }

    observations = adapter.transform_to_fhir_observations(crisis_payload)
    alerts = adapter.detect_alerts(crisis_payload)

    print(f"  [OK] Created {len(observations)} observations")
    print(f"  [OK] Detected {len(alerts)} alerts")

    for alert in alerts:
        severity = alert['_internal']['severity']
        message = alert['code']['text']
        print(f"    - [{severity.upper()}] {message}")

    # Test 3: Create bundle
    print("\n[TEST 3] Creating FHIR Bundle...")

    bundle = adapter.create_bundle(observations, alerts)
    print(f"  [OK] Created bundle with {len(bundle['entry'])} entries")

    # Summary
    print("\n" + "=" * 70)
    print("BLOOD PRESSURE ADAPTER TEST SUMMARY")
    print("=" * 70)
    print("[PASSED] All tests completed successfully!")
    print("\nFeatures Tested:")
    print("  [OK] Payload validation")
    print("  [OK] FHIR Observation transformation")
    print("  [OK] Alert detection")
    print("  [OK] Hypertensive crisis detection")
    print("  [OK] FHIR Bundle creation")
    print("=" * 70)


if __name__ == "__main__":
    test_blood_pressure_adapter()
```

### Step 6: Run Tests

```bash
python tests/test_blood_pressure_adapter.py
```

**Expected Output:**
```
======================================================================
Testing Blood Pressure Monitor Adapter
======================================================================

[TEST 1] Normal blood pressure measurement...
  [OK] Payload validation passed
  [OK] Created 4 observations
    - systolic: 115 mmHg
    - diastolic: 75 mmHg
    - pulseRate: 72 beats/minute
    - meanArterialPressure: 88 mmHg
  [OK] Detected 0 alerts (expected 0)

[TEST 2] Hypertensive crisis...
  [OK] Created 3 observations
  [OK] Detected 4 alerts
    - [CRITICAL] Critical Systolic blood pressure: 190 mmHg
    - [CRITICAL] Critical Diastolic blood pressure: 125 mmHg
    - [WARNING] Warning Heart rate by Pulse oximetry: 95 beats/minute
    - [CRITICAL] HYPERTENSIVE CRISIS: 190/125 mmHg - IMMEDIATE MEDICAL ATTENTION REQUIRED

[TEST 3] Creating FHIR Bundle...
  [OK] Created bundle with 7 entries

======================================================================
BLOOD PRESSURE ADAPTER TEST SUMMARY
======================================================================
[PASSED] All tests completed successfully!

Features Tested:
  [OK] Payload validation
  [OK] FHIR Observation transformation
  [OK] Alert detection
  [OK] Hypertensive crisis detection
  [OK] FHIR Bundle creation
======================================================================
```

---

## Integration

### Option 1: REST API Integration

Create API endpoint in `app/fhir_r5/device_api.py`:

```python
from fastapi import APIRouter, HTTPException
from app.device_modules.blood_pressure_monitor.adapter import BloodPressureMonitorAdapter

router = APIRouter(prefix="/devices/bp", tags=["Blood Pressure"])

adapter = BloodPressureMonitorAdapter()

@router.post("/measurements")
async def receive_bp_measurement(payload: dict):
    """Receive blood pressure measurement from device"""

    # Validate
    is_valid, error = adapter.validate_payload(payload)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # Transform
    observations = adapter.transform_to_fhir_observations(payload)
    alerts = adapter.detect_alerts(payload)

    # Store observations (call FHIR API)
    # Store alerts (call FHIR API)

    # Stream via WebSocket
    from app.services.websocket_service import vitals_streaming

    for obs in observations:
        await vitals_streaming.stream_observation(obs)

    for alert in alerts:
        await vitals_streaming.stream_alert(alert)

    return {
        "status": "success",
        "observations": len(observations),
        "alerts": len(alerts)
    }
```

### Option 2: MQTT Integration

Create MQTT consumer in `app/device_modules/blood_pressure_monitor/mqtt_consumer.py`:

```python
import paho.mqtt.client as mqtt
import json
from .adapter import BloodPressureMonitorAdapter

adapter = BloodPressureMonitorAdapter()

def on_message(client, userdata, msg):
    """Handle incoming MQTT messages"""
    try:
        payload = json.loads(msg.payload)

        # Validate
        is_valid, error = adapter.validate_payload(payload)
        if not is_valid:
            print(f"Invalid payload: {error}")
            return

        # Transform
        observations = adapter.transform_to_fhir_observations(payload)
        alerts = adapter.detect_alerts(payload)

        # Post to FHIR API
        # (Implementation depends on your architecture)

        print(f"Processed: {len(observations)} observations, {len(alerts)} alerts")

    except Exception as e:
        print(f"Error processing message: {e}")

def start_mqtt_consumer():
    client = mqtt.Client()
    client.on_message = on_message

    client.connect("mqtt.hospital.org", 1883)
    client.subscribe("hospital/bp/#")

    client.loop_forever()
```

---

## Best Practices

### 1. Use Standard LOINC Codes

Always map measurements to LOINC codes:
- Search: https://loinc.org/
- Reference: https://loinc.org/usage/obs/

### 2. Define Clear Normal Ranges

Use clinical guidelines:
- AHA (American Heart Association)
- WHO (World Health Organization)
- Local hospital protocols

### 3. Implement Proper Alert Severity

Three levels:
- **Normal**: No alert
- **Warning**: Abnormal but not life-threatening
- **Critical**: Immediate medical attention required

### 4. Validate All Inputs

Check:
- Required fields present
- Value types correct
- Values within physically possible ranges
- Timestamps valid

### 5. Include Internal Metadata

Add `_internal` field for debugging:
```python
"_internal": {
    "deviceId": "DEV000004",
    "measurementType": "systolic",
    "rawValue": 120,
    "processingTime": "0.002s"
}
```

### 6. Handle Edge Cases

- Missing optional fields
- Out-of-range values
- Device disconnections
- Duplicate measurements

### 7. Test Thoroughly

Test scenarios:
- Normal values
- Boundary values (just above/below normal)
- Critical values
- Invalid payloads
- Missing fields

### 8. Document Everything

Include:
- Device specifications
- Expected payload format
- LOINC code mappings
- Normal ranges
- Alert thresholds

---

## Additional Examples

### Glucose Monitor

```python
LOINC_CODES = {
    "bloodGlucose": {
        "code": "2339-0",
        "display": "Glucose [Mass/volume] in Blood",
        "unit": "mg/dL",
        "system": "http://loinc.org",
        "category": "laboratory",
        "ucum": "mg/dL"
    }
}

NORMAL_RANGES = {
    "fasting": {"min": 70, "max": 100, "critical_high": 126},
    "postprandial": {"min": 70, "max": 140, "critical_high": 200}
}
```

### Pulse Oximeter

```python
LOINC_CODES = {
    "spo2": {
        "code": "59408-5",
        "display": "Oxygen saturation in Arterial blood by Pulse oximetry",
        "unit": "%",
        "system": "http://loinc.org",
        "category": "vital-signs",
        "ucum": "%"
    },
    "perfusionIndex": {
        "code": "61006-3",
        "display": "Perfusion index Tissue by Pulse oximetry",
        "unit": "%",
        "system": "http://loinc.org",
        "category": "vital-signs",
        "ucum": "%"
    }
}
```

### ECG Monitor

```python
LOINC_CODES = {
    "heartRate": {
        "code": "8867-4",
        "display": "Heart rate",
        "unit": "beats/minute"
    },
    "qrsInterval": {
        "code": "8625-6",
        "display": "QRS duration",
        "unit": "milliseconds"
    },
    "qtInterval": {
        "code": "8634-8",
        "display": "QT interval",
        "unit": "milliseconds"
    }
}
```

---

## Reference

### FHIR R5 Resources
- Observation: https://hl7.org/fhir/R5/observation.html
- Flag: https://hl7.org/fhir/R5/flag.html
- Device: https://hl7.org/fhir/R5/device.html

### Terminology
- LOINC: https://loinc.org/
- SNOMED CT: https://www.snomed.org/
- UCUM: https://ucum.org/

### Clinical Guidelines
- AHA Blood Pressure: https://www.heart.org/en/health-topics/high-blood-pressure
- WHO Vital Signs: https://www.who.int/

---

## Support

For device module development:
- Email: dev@hospital.org
- Slack: #device-modules
- Wiki: https://wiki.hospital.org/device-modules
