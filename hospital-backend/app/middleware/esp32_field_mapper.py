"""
ESP32 Field Mapper Middleware
Centralized field name transformation between ESP32 devices and backend

Purpose:
- ESP32 devices send lowercase field names
- Backend expects camelCase field names
- This middleware provides automatic transformation in both directions

Usage:
    from app.middleware.esp32_field_mapper import ESP32FieldMapper

    # Transform ESP32 request to backend format
    backend_data = ESP32FieldMapper.transform_request(esp32_data)

    # Transform backend response to ESP32 format (if needed)
    esp32_data = ESP32FieldMapper.transform_response(backend_data)
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ESP32FieldMapper:
    """
    Centralized field mapping for ESP32 devices
    Single source of truth for field name transformations
    """

    # ========================================================================
    # FIELD MAPPING DICTIONARY
    # ========================================================================
    # Maps lowercase ESP32 field names to camelCase backend field names

    FIELD_MAPPING = {
        # Vital Signs
        "heartrate": "heartRate",
        "oxygensat": "oxygenSaturation",
        "bloodpressurevalue": "bloodPressureSystolic",
        "bloodpressuresystolic": "bloodPressureSystolic",
        "bloodpressurediastolic": "bloodPressureDiastolic",
        "temperature": "bodyTemperature",
        "bodytemperature": "bodyTemperature",
        "respiratoryrate": "respiratoryRate",
        "ecgdata": "ecgData",

        # Device Identification
        "deviceid": "deviceId",
        "patientid": "patientId",
        "macaddress": "macAddress",
        "serialnumber": "serialNumber",
        "firmwareversion": "firmwareVersion",

        # Device Status
        "batterylevel": "batteryLevel",
        "devicebattery": "deviceBattery",
        "lastseen": "lastSeen",
        "signalstrength": "signalStrength",
        "connectionstatus": "connectionStatus",

        # Assignment
        "assignedby": "assignedBy",
        "assignedat": "assignedAt",
        "unassignedby": "unassignedBy",
        "unassignedat": "unassignedAt",
        "assignmentrea son": "assignmentReason",

        # Location/Room Tracking
        "roomnumber": "roomNumber",
        "roomid": "roomId",
        "bednumber": "bedNumber",
        "location": "location",
        "scannerid": "scannerId",
        "detecteddevices": "detectedDevices",

        # Timestamps
        "timestamp": "timestamp",
        "createdat": "createdAt",
        "updatedat": "updatedAt",

        # Patient Info
        "firstname": "firstName",
        "lastname": "lastName",
        "patientname": "patientName",

        # Alert/Medical
        "alerttype": "alertType",
        "alertseverity": "alertSeverity",
        "vitaltype": "vitalType",
        "vitalvalue": "vitalValue",

        # Provisioning
        "devicetype": "deviceType",
        "ipaddress": "ipAddress",
        "provisionedby": "provisionedBy",
        "provisionerid": "provisionerId",
        "provisionerpassword": "provisionerPassword",
    }

    # Reverse mapping for backend → ESP32 transformation
    REVERSE_MAPPING = {v: k for k, v in FIELD_MAPPING.items()}

    # ========================================================================
    # TRANSFORMATION METHODS
    # ========================================================================

    @classmethod
    def transform_request(cls, data: Dict[str, Any], recursive: bool = True) -> Dict[str, Any]:
        """
        Transform ESP32 request data to backend camelCase format

        Args:
            data: Dictionary with ESP32 lowercase field names
            recursive: If True, transform nested dictionaries and lists

        Returns:
            Dictionary with backend camelCase field names

        Example:
            >>> esp32_data = {"heartrate": 75, "oxygensat": 98}
            >>> backend_data = ESP32FieldMapper.transform_request(esp32_data)
            >>> print(backend_data)
            {'heartRate': 75, 'oxygenSaturation': 98}
        """
        if not isinstance(data, dict):
            return data

        transformed = {}

        for key, value in data.items():
            # Get backend field name (or keep original if not in mapping)
            backend_key = cls.FIELD_MAPPING.get(key.lower(), key)

            # Recursively transform nested structures if enabled
            if recursive and isinstance(value, dict):
                transformed[backend_key] = cls.transform_request(value, recursive=True)
            elif recursive and isinstance(value, list):
                transformed[backend_key] = [
                    cls.transform_request(item, recursive=True) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                transformed[backend_key] = value

        logger.debug(f"Transformed ESP32 request: {len(data)} fields → {len(transformed)} fields")
        return transformed

    @classmethod
    def transform_response(cls, data: Dict[str, Any], recursive: bool = True) -> Dict[str, Any]:
        """
        Transform backend response to ESP32 lowercase format

        Args:
            data: Dictionary with backend camelCase field names
            recursive: If True, transform nested dictionaries and lists

        Returns:
            Dictionary with ESP32 lowercase field names

        Example:
            >>> backend_data = {"heartRate": 75, "oxygenSaturation": 98}
            >>> esp32_data = ESP32FieldMapper.transform_response(backend_data)
            >>> print(esp32_data)
            {'heartrate': 75, 'oxygensat': 98}

        Note:
            This is typically only needed when ESP32 expects lowercase responses.
            Most ESP32 devices can handle camelCase responses.
        """
        if not isinstance(data, dict):
            return data

        transformed = {}

        for key, value in data.items():
            # Get ESP32 field name (or keep original if not in reverse mapping)
            esp32_key = cls.REVERSE_MAPPING.get(key, key.lower())

            # Recursively transform nested structures if enabled
            if recursive and isinstance(value, dict):
                transformed[esp32_key] = cls.transform_response(value, recursive=True)
            elif recursive and isinstance(value, list):
                transformed[esp32_key] = [
                    cls.transform_response(item, recursive=True) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                transformed[esp32_key] = value

        logger.debug(f"Transformed backend response: {len(data)} fields → {len(transformed)} fields")
        return transformed

    @classmethod
    def transform_field_name(cls, field_name: str, to_backend: bool = True) -> str:
        """
        Transform a single field name

        Args:
            field_name: Field name to transform
            to_backend: If True, transform ESP32 → backend, else backend → ESP32

        Returns:
            Transformed field name

        Example:
            >>> ESP32FieldMapper.transform_field_name("heartrate", to_backend=True)
            'heartRate'
            >>> ESP32FieldMapper.transform_field_name("heartRate", to_backend=False)
            'heartrate'
        """
        if to_backend:
            return cls.FIELD_MAPPING.get(field_name.lower(), field_name)
        else:
            return cls.REVERSE_MAPPING.get(field_name, field_name.lower())

    @classmethod
    def get_mapped_fields(cls) -> List[str]:
        """
        Get list of all ESP32 fields that have mappings

        Returns:
            List of ESP32 field names that will be transformed
        """
        return list(cls.FIELD_MAPPING.keys())

    @classmethod
    def get_backend_fields(cls) -> List[str]:
        """
        Get list of all backend field names in mappings

        Returns:
            List of backend camelCase field names
        """
        return list(cls.FIELD_MAPPING.values())

    @classmethod
    def is_mapped(cls, field_name: str) -> bool:
        """
        Check if a field name has a mapping

        Args:
            field_name: Field name to check

        Returns:
            True if field has a mapping, False otherwise
        """
        return field_name.lower() in cls.FIELD_MAPPING

    @classmethod
    def add_mapping(cls, esp32_field: str, backend_field: str) -> None:
        """
        Dynamically add a new field mapping

        Args:
            esp32_field: ESP32 lowercase field name
            backend_field: Backend camelCase field name

        Note:
            Use sparingly - prefer updating FIELD_MAPPING dictionary
        """
        cls.FIELD_MAPPING[esp32_field.lower()] = backend_field
        cls.REVERSE_MAPPING[backend_field] = esp32_field.lower()
        logger.info(f"Added field mapping: {esp32_field} → {backend_field}")

    # ========================================================================
    # VALIDATION METHODS
    # ========================================================================

    @classmethod
    def validate_esp32_data(cls, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate ESP32 data structure

        Args:
            data: ESP32 data dictionary

        Returns:
            Tuple of (is_valid, list_of_issues)

        Example:
            >>> is_valid, issues = ESP32FieldMapper.validate_esp32_data(esp32_data)
            >>> if not is_valid:
            ...     print(f"Validation failed: {issues}")
        """
        issues = []

        if not isinstance(data, dict):
            issues.append("Data must be a dictionary")
            return False, issues

        # Check for common required fields
        required_esp32_fields = ["deviceid"]
        for field in required_esp32_fields:
            if field not in data and field.lower() not in data:
                issues.append(f"Missing required field: {field}")

        # Check for unknown fields (optional warning)
        unknown_fields = [
            key for key in data.keys()
            if key.lower() not in cls.FIELD_MAPPING and key not in cls.REVERSE_MAPPING
        ]
        if unknown_fields:
            logger.warning(f"Unknown fields in ESP32 data: {unknown_fields}")

        return len(issues) == 0, issues


# ========================================================================
# CONVENIENCE FUNCTIONS
# ========================================================================

def esp32_to_backend(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function: Transform ESP32 data to backend format

    Args:
        data: ESP32 data dictionary

    Returns:
        Backend-formatted dictionary
    """
    return ESP32FieldMapper.transform_request(data)


def backend_to_esp32(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function: Transform backend data to ESP32 format

    Args:
        data: Backend data dictionary

    Returns:
        ESP32-formatted dictionary
    """
    return ESP32FieldMapper.transform_response(data)


# ========================================================================
# USAGE EXAMPLES (for documentation)
# ========================================================================

if __name__ == "__main__":
    # Example 1: Transform vitals data from ESP32
    esp32_vitals = {
        "deviceid": "ESP32-001",
        "patientid": "PAT-001",
        "heartrate": 75,
        "oxygensat": 98,
        "bloodpressurevalue": 120,
        "temperature": 98.6,
        "timestamp": "2025-10-13T10:30:00Z"
    }

    backend_vitals = ESP32FieldMapper.transform_request(esp32_vitals)
    print("ESP32 → Backend:")
    print(f"  Input:  {esp32_vitals}")
    print(f"  Output: {backend_vitals}")

    # Example 2: Transform response back to ESP32 format
    backend_response = {
        "deviceId": "ESP32-001",
        "status": "assigned",
        "batteryLevel": 85,
        "lastSeen": "2025-10-13T10:30:00Z"
    }

    esp32_response = ESP32FieldMapper.transform_response(backend_response)
    print("\nBackend → ESP32:")
    print(f"  Input:  {backend_response}")
    print(f"  Output: {esp32_response}")

    # Example 3: Validate ESP32 data
    is_valid, issues = ESP32FieldMapper.validate_esp32_data(esp32_vitals)
    print(f"\nValidation: {is_valid}")
    if issues:
        print(f"Issues: {issues}")
