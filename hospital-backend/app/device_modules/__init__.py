"""
Device Modules - Pluggable Device Adapters

This package contains adapters for different medical devices.
Each adapter converts device-specific data to FHIR R5 Observations.

Supported Devices:
- ESP32 Hospital Watch (MQTT → FHIR Observations)
- Door Scanner (NFC → FHIR AuditEvents)

Architecture:
Each device module implements a common interface:
- receive_data() - Receives raw device data
- transform_to_fhir() - Converts to FHIR R5 resources
- validate() - Validates data quality
- detect_alerts() - Identifies threshold violations
"""

__version__ = "1.0.0"
