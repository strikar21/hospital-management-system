"""
ESP32 Hospital Watch Module

Converts MQTT vitals data to FHIR R5 Observations
Supports: Heart Rate, SpO2, Temperature, Blood Pressure, Respiratory Rate
"""

from .adapter import ESP32WatchAdapter
from .loinc_mapping import LOINC_CODES
from .alert_detector import VitalsAlertDetector

__all__ = ['ESP32WatchAdapter', 'LOINC_CODES', 'VitalsAlertDetector']
