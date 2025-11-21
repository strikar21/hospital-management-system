"""
Mock Hospital Management System (HMS) API Server
Simulates a hospital's existing patient database system
This would be replaced with real HMS integration in production
"""

from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime, date
import uvicorn

app = FastAPI(title="Mock HMS API", version="1.0.0")

# Mock patient database
MOCK_PATIENTS = {
    "PAT000001": {
        "id": "PAT000001",
        "mrn": "MRN-2025-001",
        "abhaId": "john.doe@abdm",
        "firstName": "John",
        "lastName": "Doe",
        "gender": "male",
        "birthDate": "1980-05-15",
        "phone": "+91-9876543210",
        "email": "john.doe@example.com",
        "address": {
            "line": ["123 Main Street", "Apartment 4B"],
            "city": "Mumbai",
            "state": "Maharashtra",
            "postalCode": "400001",
            "country": "India"
        },
        "active": True,
        "registeredAt": "2025-01-15T10:30:00Z",
        "emergencyContact": {
            "name": "Jane Doe",
            "relationship": "Spouse",
            "phone": "+91-9876543211"
        }
    },
    "PAT000002": {
        "id": "PAT000002",
        "mrn": "MRN-2025-002",
        "abhaId": "priya.sharma@abdm",
        "firstName": "Priya",
        "lastName": "Sharma",
        "gender": "female",
        "birthDate": "1992-08-22",
        "phone": "+91-9876543220",
        "email": "priya.sharma@example.com",
        "address": {
            "line": ["456 Park Avenue"],
            "city": "Delhi",
            "state": "Delhi",
            "postalCode": "110001",
            "country": "India"
        },
        "active": True,
        "registeredAt": "2025-02-10T14:20:00Z",
        "emergencyContact": {
            "name": "Rajesh Sharma",
            "relationship": "Father",
            "phone": "+91-9876543221"
        }
    }
}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Mock HMS API",
        "version": "1.0.0",
        "status": "running",
        "totalPatients": len(MOCK_PATIENTS)
    }


@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: str) -> Dict[str, Any]:
    """
    Get patient by ID

    In a real HMS, this would query the hospital's patient database
    """
    if patient_id not in MOCK_PATIENTS:
        raise HTTPException(404, f"Patient {patient_id} not found in HMS")

    return MOCK_PATIENTS[patient_id]


@app.get("/api/patients")
async def search_patients(
    mrn: Optional[str] = None,
    name: Optional[str] = None,
    abhaId: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search patients by various criteria

    In a real HMS, this would query the hospital's patient database
    """
    results = list(MOCK_PATIENTS.values())

    if mrn:
        results = [p for p in results if p['mrn'] == mrn]

    if name:
        name_lower = name.lower()
        results = [
            p for p in results
            if name_lower in p['firstName'].lower() or name_lower in p['lastName'].lower()
        ]

    if abhaId:
        results = [p for p in results if p.get('abhaId') == abhaId]

    return results


@app.get("/api/patients/{patient_id}/fhir")
async def get_patient_fhir(patient_id: str) -> Dict[str, Any]:
    """
    Get patient in FHIR R5 format

    This endpoint transforms HMS patient data to FHIR R5 format
    In production, this transformation might be done by the FHIR server
    """
    if patient_id not in MOCK_PATIENTS:
        raise HTTPException(404, f"Patient {patient_id} not found in HMS")

    hms_patient = MOCK_PATIENTS[patient_id]

    # Transform to FHIR R5 Patient resource
    fhir_patient = {
        "resourceType": "Patient",
        "id": hms_patient['id'],
        "identifier": [
            {
                "system": "http://hospital.example.com/mrn",
                "value": hms_patient['mrn']
            }
        ],
        "active": hms_patient['active'],
        "name": [
            {
                "use": "official",
                "family": hms_patient['lastName'],
                "given": [hms_patient['firstName']]
            }
        ],
        "telecom": [
            {
                "system": "phone",
                "value": hms_patient['phone'],
                "use": "mobile"
            },
            {
                "system": "email",
                "value": hms_patient['email']
            }
        ],
        "gender": hms_patient['gender'],
        "birthDate": hms_patient['birthDate'],
        "address": [
            {
                "use": "home",
                "line": hms_patient['address']['line'],
                "city": hms_patient['address']['city'],
                "state": hms_patient['address']['state'],
                "postalCode": hms_patient['address']['postalCode'],
                "country": hms_patient['address']['country']
            }
        ],
        "contact": [
            {
                "relationship": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v2-0131",
                                "code": "C",
                                "display": "Emergency Contact"
                            }
                        ]
                    }
                ],
                "name": {
                    "text": hms_patient['emergencyContact']['name']
                },
                "telecom": [
                    {
                        "system": "phone",
                        "value": hms_patient['emergencyContact']['phone']
                    }
                ]
            }
        ],
        "meta": {
            "lastUpdated": datetime.now().isoformat()
        }
    }

    # Add ABHA identifier if present
    if 'abhaId' in hms_patient and hms_patient['abhaId']:
        fhir_patient['identifier'].append({
            "system": "https://healthid.ndhm.gov.in",
            "value": hms_patient['abhaId']
        })

    return fhir_patient


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    print("=" * 70)
    print("Mock HMS API Server")
    print("=" * 70)
    print("\nStarting server on http://localhost:8001")
    print("\nEndpoints:")
    print("  GET  /api/patients/{id}       - Get patient by ID")
    print("  GET  /api/patients             - Search patients")
    print("  GET  /api/patients/{id}/fhir   - Get patient in FHIR R5 format")
    print("\nMock Patients:")
    for patient in MOCK_PATIENTS.values():
        print(f"  - {patient['id']}: {patient['firstName']} {patient['lastName']} (MRN: {patient['mrn']})")
    print("\n" + "=" * 70)

    uvicorn.run(app, host="0.0.0.0", port=8001)
