"""
Data transformation utilities for converting between snake_case (database) and camelCase (frontend)
"""

from typing import Dict, Any, List, Union
import re
from datetime import datetime, date
import json
from decimal import Decimal

def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase"""
    components = snake_str.split('_')
    return components[0] + ''.join(word.capitalize() for word in components[1:])

def to_snake_case(camel_str: str) -> str:
    """Convert camelCase to snake_case"""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def transform_dict_to_camel(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform dictionary keys from snake_case to camelCase"""
    if not isinstance(data, dict):
        return data

    transformed = {}
    for key, value in data.items():
        camel_key = to_camel_case(key)
        if isinstance(value, dict):
            transformed[camel_key] = transform_dict_to_camel(value)
        elif isinstance(value, list):
            transformed[camel_key] = [
                transform_dict_to_camel(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            transformed[camel_key] = value

    return transformed

def transform_dict_to_snake(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform dictionary keys from camelCase to snake_case"""
    if not isinstance(data, dict):
        return data
    
    transformed = {}
    for key, value in data.items():
        snake_key = to_snake_case(key)
        if isinstance(value, dict):
            transformed[snake_key] = transform_dict_to_snake(value)
        elif isinstance(value, list):
            transformed[snake_key] = [
                transform_dict_to_snake(item) if isinstance(item, dict) else item 
                for item in value
            ]
        else:
            transformed[snake_key] = value
    
    return transformed

def serialize_dates_in_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert date/datetime/decimal objects to JSON serializable formats"""
    if not isinstance(data, dict):
        return data
    
    serialized = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        elif isinstance(value, date):
            serialized[key] = value.isoformat()
        elif isinstance(value, Decimal):
            serialized[key] = float(value)
        elif isinstance(value, dict):
            serialized[key] = serialize_dates_in_dict(value)
        elif isinstance(value, list):
            serialized[key] = [
                serialize_dates_in_dict(item) if isinstance(item, dict) else 
                item.isoformat() if isinstance(item, (datetime, date)) else
                float(item) if isinstance(item, Decimal) else item
                for item in value
            ]
        else:
            serialized[key] = value
    
    return serialized

def transform_patient_to_camel(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform patient data from database format to frontend format"""
    # First serialize any date objects
    serialized_data = serialize_dates_in_dict(patient_data)
    
    # Then transform to camelCase
    transformed = transform_dict_to_camel(serialized_data)
    
    # Handle special field mappings
    field_mappings = {
        'currentvitals': 'currentVitals',
        'recentvitals': 'recentVitals',
        'assigneddeviceid': 'assignedDeviceId',
        'dateofbirth': 'dateOfBirth',
        'phonenumber': 'phoneNumber',
        'emergencycontactname': 'emergencyContactName',
        'emergencycontactphone': 'emergencyContactPhone',
        'bloodtype': 'bloodType',
        'medicalhistory': 'medicalHistory',
        'currentmedications': 'currentMedications',
        'roomnumber': 'roomNumber',
        'bednumber': 'bedNumber',
        'attendingphysician': 'attendingPhysician',
        'nurseincharge': 'nurseInCharge',
        'admissiondate': 'admissionDate',
        'dischargedate': 'dischargeDate',
        'createdat': 'createdAt',
        'updatedat': 'updatedAt',
        'patientid': 'patientId',
        'deviceid': 'deviceId',
        'heartrate': 'heartRate',
        'devicestatus': 'deviceStatus',
        'devicebattery': 'deviceBattery',
        'devicelastseen': 'deviceLastSeen',
        'bloodpressuresystolic': 'bloodPressureSystolic',
        'bloodpressurediastolic': 'bloodPressureDiastolic',
        'oxygensaturation': 'oxygenSaturation',
        'respiratoryrate': 'respiratoryRate',
        'glucoselevel': 'glucoseLevel',
        'firstname': 'firstName',
        'lastname': 'lastName',
        'recommendedward': 'recommendedWard',
        'assigneddoctor': 'assignedDoctor',
        'recommendedby': 'recommendedBy',
        'processedby': 'processedBy',
        'processedat': 'processedAt',
        'assigneddoctorname': 'assignedDoctorName',
        'recommendedfrom': 'recommendedFrom',
        'serialnumber': 'serialNumber',
        'macaddress': 'macAddress',
        'firmwareversion': 'firmwareVersion',
        'batterylevel': 'batteryLevel',
        'lastseen': 'lastSeen',
        'calibrationdate': 'calibrationDate',
        'nextmaintenancedate': 'nextMaintenanceDate',
        'devicetype': 'deviceType',
        'isactive': 'isActive',
        'nfccardid': 'nfcCardId',
        'scheduledat': 'scheduledAt',
        'completedat': 'completedAt',
        'performedby': 'performedBy',
        'medicationid': 'medicationId',
        'scheduledtime': 'scheduledTime',
        'administeredat': 'administeredAt',
        'administeredby': 'administeredBy',
        'dosagegiven': 'dosageGiven',
        'startdate': 'startDate',
        'enddate': 'endDate',
        'prescribedby': 'prescribedBy',
        'therapyid': 'therapyId',
        'sessionnumber': 'sessionNumber',
        'scheduleddate': 'scheduledDate',
        'sessionnotes': 'sessionNotes',
        'authorid': 'authorId',
        'editedat': 'editedAt',
        'isedited': 'isEdited',
        'entrytype': 'entryType',
        'wardtype': 'wardType',
        'occupiedby': 'occupiedBy',
        'lastcleaned': 'lastCleaned',
        'resourcetype': 'resourceType',
        'resourceid': 'resourceId',
        'ipaddress': 'ipAddress',
        'useragent': 'userAgent',
        'userid': 'userId',
        'dischargerstatus': 'dischargeStatus',
        'assignedat': 'assignedAt',
        'unassignedat': 'unassignedAt'
    }
    
    # Apply specific mappings
    for old_key, new_key in field_mappings.items():
        if old_key in transformed:
            transformed[new_key] = transformed.pop(old_key)
    
    return transformed