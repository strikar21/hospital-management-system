"""
Service Factory - Centralized access to all business services
Provides singleton instances and easy dependency injection
"""

from typing import Dict, Any
import logging

from .patient_service import PatientService
from .medication_service import MedicationService
from .investigation_service import InvestigationService
from .therapy_service import TherapyService
from .discharge_service import DischargeService


class ServiceFactory:
    """
    Factory pattern for managing service instances
    Ensures singleton behavior and manages dependencies
    """

    _instances: Dict[str, Any] = {}
    _logger = logging.getLogger(__name__)

    @classmethod
    def get_patient_service(cls) -> PatientService:
        """Get PatientService singleton instance"""
        if 'patient_service' not in cls._instances:
            cls._instances['patient_service'] = PatientService()
            cls._logger.info("PatientService instance created")
        return cls._instances['patient_service']

    @classmethod
    def get_medication_service(cls) -> MedicationService:
        """Get MedicationService singleton instance"""
        if 'medication_service' not in cls._instances:
            cls._instances['medication_service'] = MedicationService()
            cls._logger.info("MedicationService instance created")
        return cls._instances['medication_service']

    @classmethod
    def get_investigation_service(cls) -> InvestigationService:
        """Get InvestigationService singleton instance"""
        if 'investigation_service' not in cls._instances:
            cls._instances['investigation_service'] = InvestigationService()
            cls._logger.info("InvestigationService instance created")
        return cls._instances['investigation_service']

    @classmethod
    def get_therapy_service(cls) -> TherapyService:
        """Get TherapyService singleton instance"""
        if 'therapy_service' not in cls._instances:
            cls._instances['therapy_service'] = TherapyService()
            cls._logger.info("TherapyService instance created")
        return cls._instances['therapy_service']

    @classmethod
    def get_discharge_service(cls) -> DischargeService:
        """Get DischargeService singleton instance"""
        if 'discharge_service' not in cls._instances:
            cls._instances['discharge_service'] = DischargeService()
            cls._logger.info("DischargeService instance created")
        return cls._instances['discharge_service']

    @classmethod
    def get_all_services(cls) -> Dict[str, Any]:
        """Get all service instances"""
        return {
            'patient': cls.get_patient_service(),
            'medication': cls.get_medication_service(),
            'investigation': cls.get_investigation_service(),
            'therapy': cls.get_therapy_service(),
            'discharge': cls.get_discharge_service()
        }

    @classmethod
    def reset_instances(cls) -> None:
        """Reset all instances (useful for testing)"""
        cls._instances.clear()
        cls._logger.info("All service instances reset")


# Convenience functions for easy access
def get_patient_service() -> PatientService:
    """Convenience function to get PatientService"""
    return ServiceFactory.get_patient_service()


def get_medication_service() -> MedicationService:
    """Convenience function to get MedicationService"""
    return ServiceFactory.get_medication_service()


def get_investigation_service() -> InvestigationService:
    """Convenience function to get InvestigationService"""
    return ServiceFactory.get_investigation_service()


def get_therapy_service() -> TherapyService:
    """Convenience function to get TherapyService"""
    return ServiceFactory.get_therapy_service()


def get_discharge_service() -> DischargeService:
    """Convenience function to get DischargeService"""
    return ServiceFactory.get_discharge_service()