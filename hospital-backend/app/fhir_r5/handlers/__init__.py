"""
FHIR R5 Resource Handlers
Each handler manages a specific FHIR resource type
"""

from .patient_handler import PatientHandler
from .device_handler import DeviceHandler
from .observation_handler import ObservationHandler
from .device_association_handler import DeviceAssociationHandler

__all__ = [
    'PatientHandler',
    'DeviceHandler',
    'ObservationHandler',
    'DeviceAssociationHandler'
]
