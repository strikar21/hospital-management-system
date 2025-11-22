"""
HMS (Hospital Management System) Adapter
Integrates with external HMS to pull patient data with ABHA information

Supports multiple HMS types:
- CSV File (for testing/migration)
- Database Direct (PostgreSQL/MySQL)
- REST API (for cloud HMS systems)
"""

import csv
import logging
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class HmsPatient:
    """Patient data from HMS with complete clinical information"""
    def __init__(self, data: Dict):
        # Demographics
        self.hmsPatientId = data.get('hmsPatientId')
        self.mrn = data.get('mrn')
        self.firstName = data.get('firstName')
        self.lastName = data.get('lastName')
        self.dateOfBirth = data.get('dateOfBirth')
        self.gender = data.get('gender')
        self.phoneNumber = data.get('phoneNumber')

        # ABHA Information
        self.abhaNumber = data.get('abhaNumber')
        self.abhaAddress = data.get('abhaAddress')
        self.hasAbha = bool(self.abhaNumber or self.abhaAddress)

        # Admission Details
        self.admissionDate = data.get('admissionDate')
        self.roomNumber = data.get('roomNumber')
        self.bedNumber = data.get('bedNumber')

        # Staff Assignments
        self.attendingPhysician = data.get('attendingPhysician')
        self.nurseInCharge = data.get('nurseInCharge')

        # Medical Information
        self.diagnosis = data.get('diagnosis')
        self.bloodType = data.get('bloodType')
        self.allergies = data.get('allergies')
        self.weight = data.get('weight')
        self.emergencyContactName = data.get('emergencyContactName')
        self.emergencyContactPhone = data.get('emergencyContactPhone')

        # Legacy fields (pipe-separated in CSV, needs parsing)
        self.currentMedications = data.get('currentMedications')
        self.medicalHistory = data.get('medicalHistory')

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            'hmsPatientId': self.hmsPatientId,
            'mrn': self.mrn,
            'firstName': self.firstName,
            'lastName': self.lastName,
            'dateOfBirth': self.dateOfBirth,
            'gender': self.gender,
            'phoneNumber': self.phoneNumber,
            'abhaNumber': self.abhaNumber,
            'abhaAddress': self.abhaAddress,
            'hasAbha': self.hasAbha,
            'admissionDate': self.admissionDate,
            'roomNumber': self.roomNumber,
            'bedNumber': self.bedNumber,
            'attendingPhysician': self.attendingPhysician,
            'nurseInCharge': self.nurseInCharge,
            'diagnosis': self.diagnosis,
            'bloodType': self.bloodType,
            'allergies': self.allergies,
            'weight': self.weight,
            'emergencyContactName': self.emergencyContactName,
            'emergencyContactPhone': self.emergencyContactPhone,
            'currentMedications': self.currentMedications,
            'medicalHistory': self.medicalHistory
        }


class HmsMedication:
    """Medication from HMS"""
    def __init__(self, data: Dict):
        self.hmsMedicationId = data.get('hmsMedicationId')
        self.hmsPatientId = data.get('hmsPatientId')
        self.mrn = data.get('mrn')
        self.medicationName = data.get('medicationName')
        self.dosage = data.get('dosage')
        self.frequency = data.get('frequency')
        self.route = data.get('route')
        self.startDate = data.get('startDate')
        self.duration = data.get('duration')
        self.prescribedBy = data.get('prescribedBy')
        self.status = data.get('status', 'active')

    def to_dict(self) -> Dict:
        return {
            'hmsMedicationId': self.hmsMedicationId,
            'hmsPatientId': self.hmsPatientId,
            'mrn': self.mrn,
            'medicationName': self.medicationName,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'route': self.route,
            'startDate': self.startDate,
            'duration': self.duration,
            'prescribedBy': self.prescribedBy,
            'status': self.status
        }


class HmsCaseEntry:
    """Case entry/clinical note from HMS"""
    def __init__(self, data: Dict):
        self.hmsCaseEntryId = data.get('hmsCaseEntryId')
        self.hmsPatientId = data.get('hmsPatientId')
        self.mrn = data.get('mrn')
        self.entryType = data.get('entryType')
        self.description = data.get('description')
        self.findings = data.get('findings')
        self.recommendations = data.get('recommendations')
        self.severity = data.get('severity')
        self.category = data.get('category')
        self.performedBy = data.get('performedBy')
        self.timestamp = data.get('timestamp')

    def to_dict(self) -> Dict:
        return {
            'hmsCaseEntryId': self.hmsCaseEntryId,
            'hmsPatientId': self.hmsPatientId,
            'mrn': self.mrn,
            'entryType': self.entryType,
            'description': self.description,
            'findings': self.findings,
            'recommendations': self.recommendations,
            'severity': self.severity,
            'category': self.category,
            'performedBy': self.performedBy,
            'timestamp': self.timestamp
        }


class CsvHmsAdapter:
    """
    CSV-based HMS adapter
    Reads patient data from CSV file (for testing or one-time migration)
    """

    def __init__(self, csv_path: str = None):
        if csv_path is None:
            # Default path - use extended version
            base_dir = Path(__file__).parent.parent.parent
            csv_path = base_dir / "data" / "hms_patients_extended.csv"

        self.csv_path = Path(csv_path)

        # Paths for related data
        self.medications_csv_path = self.csv_path.parent / "hms_medications.csv"
        self.case_entries_csv_path = self.csv_path.parent / "hms_case_entries.csv"

        logger.info(f"CSV HMS Adapter initialized with path: {self.csv_path}")

    def get_patients(self, search: str = None, has_abha: bool = None) -> List[HmsPatient]:
        """
        Get all patients from CSV file

        Args:
            search: Optional search term (firstName, lastName, MRN)
            has_abha: Optional filter - True (only with ABHA), False (only without), None (all)

        Returns:
            List of HmsPatient objects
        """
        if not self.csv_path.exists():
            logger.warning(f"HMS CSV file not found: {self.csv_path}")
            return []

        patients = []

        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Convert empty strings to None
                    for key in row:
                        if row[key] == '':
                            row[key] = None

                    patient = HmsPatient(row)

                    # Apply filters
                    if search:
                        search_lower = search.lower()
                        if not (
                            search_lower in (patient.firstName or '').lower() or
                            search_lower in (patient.lastName or '').lower() or
                            search_lower in (patient.mrn or '').lower()
                        ):
                            continue

                    if has_abha is not None:
                        if has_abha != patient.hasAbha:
                            continue

                    patients.append(patient)

            logger.info(f"Loaded {len(patients)} patients from HMS CSV")
            return patients

        except Exception as e:
            logger.error(f"Error reading HMS CSV: {e}")
            raise

    def get_patient_by_id(self, hms_patient_id: str) -> Optional[HmsPatient]:
        """Get single patient by HMS patient ID"""
        patients = self.get_patients()
        for patient in patients:
            if patient.hmsPatientId == hms_patient_id:
                return patient
        return None

    def get_patient_by_mrn(self, mrn: str) -> Optional[HmsPatient]:
        """Get single patient by MRN"""
        patients = self.get_patients()
        for patient in patients:
            if patient.mrn == mrn:
                return patient
        return None

    def get_medications_for_patient(self, hms_patient_id: str = None, mrn: str = None) -> List[HmsMedication]:
        """
        Get medications for a patient

        Args:
            hms_patient_id: HMS patient ID
            mrn: Medical Record Number

        Returns:
            List of HmsMedication objects
        """
        if not self.medications_csv_path.exists():
            logger.warning(f"HMS medications CSV not found: {self.medications_csv_path}")
            return []

        medications = []

        try:
            with open(self.medications_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Convert empty strings to None
                    for key in row:
                        if row[key] == '':
                            row[key] = None

                    medication = HmsMedication(row)

                    # Filter by patient
                    if hms_patient_id and medication.hmsPatientId != hms_patient_id:
                        continue
                    if mrn and medication.mrn != mrn:
                        continue

                    medications.append(medication)

            logger.info(f"Loaded {len(medications)} medications for patient")
            return medications

        except Exception as e:
            logger.error(f"Error reading medications CSV: {e}")
            return []

    def get_case_entries_for_patient(self, hms_patient_id: str = None, mrn: str = None) -> List[HmsCaseEntry]:
        """
        Get case entries for a patient

        Args:
            hms_patient_id: HMS patient ID
            mrn: Medical Record Number

        Returns:
            List of HmsCaseEntry objects
        """
        if not self.case_entries_csv_path.exists():
            logger.warning(f"HMS case entries CSV not found: {self.case_entries_csv_path}")
            return []

        case_entries = []

        try:
            with open(self.case_entries_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Convert empty strings to None
                    for key in row:
                        if row[key] == '':
                            row[key] = None

                    case_entry = HmsCaseEntry(row)

                    # Filter by patient
                    if hms_patient_id and case_entry.hmsPatientId != hms_patient_id:
                        continue
                    if mrn and case_entry.mrn != mrn:
                        continue

                    case_entries.append(case_entry)

            logger.info(f"Loaded {len(case_entries)} case entries for patient")
            return case_entries

        except Exception as e:
            logger.error(f"Error reading case entries CSV: {e}")
            return []


class HmsAdapterFactory:
    """
    Factory to create appropriate HMS adapter based on configuration
    """

    @staticmethod
    def create_adapter(adapter_type: str = "csv", **kwargs):
        """
        Create HMS adapter

        Args:
            adapter_type: Type of adapter (csv, database, api)
            **kwargs: Adapter-specific configuration

        Returns:
            HMS adapter instance
        """
        if adapter_type == "csv":
            return CsvHmsAdapter(csv_path=kwargs.get('csv_path'))
        elif adapter_type == "database":
            # TODO: Implement database adapter
            raise NotImplementedError("Database HMS adapter not yet implemented")
        elif adapter_type == "api":
            # TODO: Implement REST API adapter
            raise NotImplementedError("API HMS adapter not yet implemented")
        else:
            raise ValueError(f"Unknown HMS adapter type: {adapter_type}")


# Global HMS adapter instance (configured via environment variable)
import os
HMS_ADAPTER_TYPE = os.getenv("HMS_ADAPTER_TYPE", "csv")
HMS_CSV_PATH = os.getenv("HMS_CSV_PATH", None)

try:
    hms_adapter = HmsAdapterFactory.create_adapter(
        adapter_type=HMS_ADAPTER_TYPE,
        csv_path=HMS_CSV_PATH
    )
    logger.info(f"✅ HMS Adapter initialized: {HMS_ADAPTER_TYPE}")
except Exception as e:
    logger.error(f"❌ Failed to initialize HMS adapter: {e}")
    hms_adapter = None
