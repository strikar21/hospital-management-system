"""
Door Scanner Module

Converts NFC tap events to FHIR AuditEvent resources
Tracks staff-patient interactions for DPDP Act 2023 compliance
"""

from .adapter import DoorScannerAdapter

__all__ = ['DoorScannerAdapter']
