# FHIR R5 Hospital IoT Backend - API Documentation

## Overview

This API provides FHIR R5 compliant endpoints for hospital management with IoT device integration.

**Base URL:** `http://localhost:8000`

**WebSocket Base URL:** `ws://localhost:8000/ws`

## Authentication

All endpoints require JWT authentication (except `/auth/login`).

**Authorization Header:**
```
Authorization: Bearer <your-jwt-token>
```

---

## 1. Authentication Endpoints

### POST /auth/login

Login with staff credentials.

**Request Body:**
```json
{
  "staffId": "STF000001",
  "pin": "1234"
}
```

**Response (200 OK):**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "tokenType": "Bearer",
  "expiresIn": 86400,
  "staffId": "STF000001",
  "role": "doctor",
  "nfcBadgeId": "NFC-DOC-001"
}
```

### POST /auth/logout

Logout and blacklist current token.

**Headers:** Authorization: Bearer <token>

**Response (200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

---

## 2. Patient Endpoints

### GET /fhir/Patient/{patient_id}

Retrieve patient details from HMS.

**Parameters:**
- `patient_id` (path): Patient ID (e.g., PAT000001)

**Response (200 OK):**
```json
{
  "resourceType": "Patient",
  "id": "PAT000001",
  "identifier": [
    {
      "system": "http://hospital.org/mrn",
      "value": "MRN-2025-001"
    },
    {
      "system": "http://abdm.gov.in/abha",
      "value": "john.doe@abdm"
    }
  ],
  "name": [
    {
      "use": "official",
      "family": "Doe",
      "given": ["John"]
    }
  ],
  "gender": "male",
  "birthDate": "1980-05-15",
  "telecom": [
    {
      "system": "phone",
      "value": "+91-9876543210",
      "use": "mobile"
    }
  ],
  "address": [
    {
      "use": "home",
      "line": ["123 Main Street"],
      "city": "Mumbai",
      "state": "Maharashtra",
      "postalCode": "400001",
      "country": "IN"
    }
  ]
}
```

---

## 3. Device Endpoints

### POST /fhir/Device

Register a new medical device.

**Request Body:**
```json
{
  "resourceType": "Device",
  "id": "DEV000001",
  "identifier": [
    {
      "system": "http://hospital.org/devices",
      "value": "ESP32-WATCH-001"
    }
  ],
  "type": {
    "coding": [
      {
        "system": "http://snomed.info/sct",
        "code": "706767009",
        "display": "Patient monitoring system"
      }
    ]
  },
  "manufacturer": "ESP32 Corp",
  "modelNumber": "ESP32-S3",
  "status": "active"
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "resourceType": "Device",
  "resourceId": "DEV000001",
  "resource": { ... },
  "status": "active",
  "createdAt": "2025-11-21T10:00:00Z"
}
```

### GET /fhir/Device/{device_id}

Retrieve device details.

**Response (200 OK):** Same as POST response

### GET /fhir/Device

Search all devices.

**Query Parameters:**
- `status` (optional): Filter by status (active, inactive, entered-in-error)
- `type` (optional): Filter by device type code

**Response (200 OK):**
```json
{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 3,
  "entry": [
    {
      "resource": { ... }
    }
  ]
}
```

---

## 4. Observation Endpoints

### POST /fhir/Observation

Create a new vital signs observation.

**Request Body:**
```json
{
  "resourceType": "Observation",
  "id": "OBS-HR-12345678",
  "status": "final",
  "category": [
    {
      "coding": [
        {
          "system": "http://terminology.hl7.org/CodeSystem/observation-category",
          "code": "vital-signs",
          "display": "Vital Signs"
        }
      ]
    }
  ],
  "code": {
    "coding": [
      {
        "system": "http://loinc.org",
        "code": "8867-4",
        "display": "Heart rate"
      }
    ]
  },
  "subject": {
    "reference": "Patient/PAT000001"
  },
  "effectiveDateTime": "2025-11-21T10:00:00Z",
  "issued": "2025-11-21T10:00:01Z",
  "valueQuantity": {
    "value": 72,
    "unit": "beats/minute",
    "system": "http://unitsofmeasure.org",
    "code": "/min"
  },
  "device": {
    "reference": "Device/DEV000001"
  }
}
```

**Response (201 Created):**
```json
{
  "observationId": "OBS-HR-12345678",
  "patientId": "PAT000001",
  "deviceId": "DEV000001",
  "code": "8867-4",
  "category": "vital-signs",
  "valueQuantity": 72.0,
  "valueUnit": "beats/minute",
  "status": "final",
  "effectiveDateTime": "2025-11-21T10:00:00Z"
}
```

### GET /fhir/Observation/patient/{patient_id}

Get patient's recent observations.

**Query Parameters:**
- `hours` (optional, default=24): Time window in hours
- `limit` (optional, default=100): Maximum results

**Response (200 OK):**
```json
{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 42,
  "entry": [
    {
      "time": "2025-11-21T10:00:00Z",
      "observationId": "OBS-HR-12345678",
      "patientId": "PAT000001",
      "code": "8867-4",
      "category": "vital-signs",
      "valueQuantity": 72.0,
      "valueUnit": "beats/minute",
      "status": "final"
    }
  ]
}
```

### GET /fhir/Observation/patient/{patient_id}/code/{loinc_code}

Get specific vital sign observations.

**Example:** `/fhir/Observation/patient/PAT000001/code/8867-4` (heart rate)

**Response:** Same as patient observations endpoint

---

## 5. Device Association Endpoints

### POST /fhir/DeviceAssociation

Assign a device to a patient.

**Request Body:**
```json
{
  "resourceType": "DeviceAssociation",
  "id": "ASSOC-12345678",
  "status": "active",
  "subject": {
    "reference": "Patient/PAT000001"
  },
  "device": {
    "reference": "Device/DEV000001"
  },
  "period": {
    "start": "2025-11-21T10:00:00Z"
  }
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "resourceType": "DeviceAssociation",
  "resourceId": "ASSOC-12345678",
  "resource": { ... },
  "status": "active",
  "subject": "Patient/PAT000001"
}
```

### PUT /fhir/DeviceAssociation/{association_id}/deactivate

Deactivate device assignment.

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "resourceType": "DeviceAssociation",
  "status": "inactive",
  "period": {
    "start": "2025-11-21T10:00:00Z",
    "end": "2025-11-21T18:00:00Z"
  }
}
```

### GET /fhir/DeviceAssociation/patient/{patient_id}

Get patient's device assignments.

**Response (200 OK):**
```json
{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 1,
  "entry": [
    {
      "resource": { ... }
    }
  ]
}
```

---

## 6. Consent Management Endpoints (DPDP Act 2023)

### POST /fhir/Consent

Create patient consent.

**Request Body:**
```json
{
  "patientId": "PAT000001",
  "scope": "patient-privacy",
  "category": ["ICOL"],
  "purposeOfUse": ["TREAT", "ETREAT"],
  "effectiveStart": "2025-11-21T00:00:00Z",
  "effectiveEnd": "2026-11-21T00:00:00Z",
  "grantorSignature": "data:image/png;base64,iVBORw0KG...",
  "witnessSignature": "data:image/png;base64,iVBORw0KG...",
  "createdBy": "Practitioner/STF000001"
}
```

**Response (201 Created):**
```json
{
  "resourceType": "Consent",
  "id": "CONSENT-12345678",
  "status": "active",
  "scope": {
    "coding": [
      {
        "system": "http://terminology.hl7.org/CodeSystem/consentscope",
        "code": "patient-privacy",
        "display": "Privacy Consent"
      }
    ]
  },
  "category": [
    {
      "coding": [
        {
          "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
          "code": "ICOL",
          "display": "information collection"
        }
      ]
    }
  ],
  "subject": {
    "reference": "Patient/PAT000001"
  },
  "date": "2025-11-21T10:00:00Z",
  "period": {
    "start": "2025-11-21T00:00:00Z",
    "end": "2026-11-21T00:00:00Z"
  },
  "grantor": [
    {
      "reference": "Patient/PAT000001"
    }
  ],
  "verification": [
    {
      "verified": true,
      "verifiedBy": {
        "reference": "Practitioner/STF000001"
      },
      "verificationDate": "2025-11-21T10:00:00Z"
    }
  ],
  "_signatures": {
    "grantor": "data:image/png;base64,...",
    "witness": "data:image/png;base64,..."
  }
}
```

### GET /fhir/Consent/{consent_id}

Retrieve consent details.

### GET /fhir/Consent/patient/{patient_id}

Get all consents for a patient.

**Query Parameters:**
- `status` (optional): Filter by status (active, inactive, entered-in-error)

### PUT /fhir/Consent/{consent_id}/withdraw

Withdraw patient consent.

**Response (200 OK):**
```json
{
  "resourceType": "Consent",
  "id": "CONSENT-12345678",
  "status": "inactive",
  "dateTime": "2025-11-21T10:30:00Z"
}
```

### GET /fhir/Consent/check

Check if patient has valid consent.

**Query Parameters:**
- `patientId` (required): Patient ID
- `scope` (required): Consent scope (patient-privacy, research, treatment)
- `category` (required): Category code (ICOL, IDSCL, etc.)
- `purpose` (required): Purpose of use (TREAT, ETREAT, etc.)

**Response (200 OK):**
```json
{
  "hasConsent": true,
  "consentId": "CONSENT-12345678",
  "status": "active",
  "expiresAt": "2026-11-21T00:00:00Z"
}
```

---

## 7. Audit Event Endpoints (HIPAA 2025)

### POST /fhir/AuditEvent

Log an access event.

**Request Body:**
```json
{
  "action": "read",
  "agentId": "Practitioner/STF000001",
  "agentRole": "doctor",
  "entityType": "Patient",
  "entityId": "PAT000001",
  "outcome": "success",
  "ipAddress": "192.168.1.100",
  "userAgent": "Mozilla/5.0...",
  "purposeOfEvent": "Treatment"
}
```

**Response (201 Created):**
```json
{
  "resourceType": "AuditEvent",
  "id": "AUDIT-12345678",
  "recorded": "2025-11-21T10:00:00Z",
  "action": "read",
  "outcome": "success",
  "agent": [
    {
      "who": {
        "reference": "Practitioner/STF000001"
      },
      "role": [
        {
          "text": "doctor"
        }
      ]
    }
  ],
  "entity": [
    {
      "what": {
        "reference": "Patient/PAT000001"
      }
    }
  ],
  "source": {
    "observer": {
      "reference": "Device/API-SERVER"
    }
  }
}
```

### GET /fhir/AuditEvent/patient/{patient_id}

Get patient's access log.

**Query Parameters:**
- `days` (optional, default=30): Time window in days
- `limit` (optional, default=100): Maximum results

**Response (200 OK):**
```json
{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 15,
  "entry": [
    {
      "recorded": "2025-11-21T10:00:00Z",
      "action": "read",
      "outcome": "success",
      "agentId": "Practitioner/STF000001",
      "agentRole": "doctor",
      "entityType": "Patient",
      "entityId": "PAT000001"
    }
  ]
}
```

### GET /fhir/AuditEvent/agent/{agent_id}

Get staff activity log.

---

## 8. WebSocket Endpoints

### WS /ws/vitals

Stream all patient vitals (global subscription).

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/vitals');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log(message);
};
```

**Messages Received:**

**Connection confirmation:**
```json
{
  "type": "connected",
  "message": "Connected to vitals stream (all patients)",
  "stats": {
    "connections": {
      "global": 1,
      "patients": {},
      "total": 1
    },
    "uptime": "2025-11-21T10:00:00Z"
  }
}
```

**Observation:**
```json
{
  "type": "observation",
  "timestamp": "2025-11-21T10:00:00Z",
  "data": {
    "resourceType": "Observation",
    "id": "OBS-HR-12345678",
    "code": {
      "coding": [
        {
          "system": "http://loinc.org",
          "code": "8867-4",
          "display": "Heart rate"
        }
      ]
    },
    "valueQuantity": {
      "value": 72,
      "unit": "beats/minute"
    },
    "subject": {
      "reference": "Patient/PAT000001"
    }
  }
}
```

**Alert:**
```json
{
  "type": "alert",
  "timestamp": "2025-11-21T10:00:00Z",
  "severity": "critical",
  "data": {
    "resourceType": "Flag",
    "id": "ALERT-12345678",
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
          "system": "http://loinc.org",
          "code": "8867-4",
          "display": "Heart rate"
        }
      ],
      "text": "Critical heart rate: 160 beats/minute"
    },
    "subject": {
      "reference": "Patient/PAT000001"
    }
  }
}
```

**Device status:**
```json
{
  "type": "device_status",
  "timestamp": "2025-11-21T10:00:00Z",
  "deviceId": "Device/DEV000001",
  "data": {
    "battery": 85,
    "connectivity": "connected",
    "lastSeen": "2025-11-21T10:00:00Z"
  }
}
```

**Audit event:**
```json
{
  "type": "audit",
  "timestamp": "2025-11-21T10:00:00Z",
  "data": {
    "resourceType": "AuditEvent",
    "action": "entry",
    "agent": [
      {
        "who": {
          "reference": "Practitioner/STF000001"
        }
      }
    ]
  }
}
```

### WS /ws/vitals/{patient_id}

Stream specific patient vitals.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/vitals/PAT000001');
```

**Messages Sent (Commands):**

**Ping:**
```json
{
  "type": "ping",
  "timestamp": "2025-11-21T10:00:00Z"
}
```

**Get stats:**
```json
{
  "type": "stats"
}
```

**Messages Received:** Same as global endpoint, but filtered for specified patient.

### GET /ws/stats

Get WebSocket statistics.

**Response (200 OK):**
```json
{
  "connections": {
    "global": 3,
    "patients": {
      "PAT000001": 2,
      "PAT000002": 1
    },
    "total": 6
  },
  "uptime": "2025-11-21T10:00:00Z"
}
```

---

## 9. Device Calibration Endpoints

### POST /calibration/log

Log device calibration.

**Request Body:**
```json
{
  "deviceId": "DEV000001",
  "calibrationType": "routine",
  "performedBy": "STF000001",
  "heartRateAccuracy": 99.5,
  "spo2Accuracy": 98.8,
  "temperatureAccuracy": 99.2,
  "bloodPressureAccuracy": 97.5,
  "status": "pass",
  "notes": "All sensors within normal range",
  "nextCalibrationMonths": 2
}
```

**Response (200 OK):**
```json
{
  "deviceId": "Device/DEV000001",
  "calibrationType": "routine",
  "performedBy": "Practitioner/STF000001",
  "status": "pass",
  "nextCalibrationDue": "2026-01-21T10:00:00Z",
  "timestamp": "2025-11-21T10:00:00Z"
}
```

### GET /calibration/history/{device_id}

Get calibration history for device.

**Query Parameters:**
- `limit` (optional, default=10): Maximum records

**Response (200 OK):**
```json
[
  {
    "time": "2025-11-21T10:00:00Z",
    "deviceId": "Device/DEV000001",
    "calibrationType": "routine",
    "performedBy": "Practitioner/STF000001",
    "heartRateAccuracy": 99.5,
    "spo2Accuracy": 98.8,
    "temperatureAccuracy": 99.2,
    "bloodPressureAccuracy": 97.5,
    "status": "pass",
    "notes": "All sensors within normal range",
    "nextCalibrationDue": "2026-01-21T10:00:00Z"
  }
]
```

### GET /calibration/due

Get devices due for calibration.

**Query Parameters:**
- `daysAhead` (optional, default=7): Look-ahead window in days

**Response (200 OK):**
```json
[
  {
    "deviceId": "Device/DEV000001",
    "nextCalibrationDue": "2025-11-28T10:00:00Z",
    "lastCalibration": "2025-09-28T10:00:00Z",
    "lastStatus": "pass",
    "daysUntilDue": 7
  }
]
```

### GET /calibration/check/{device_id}

Check if device has valid calibration.

**Response (200 OK):**
```json
{
  "deviceId": "Device/DEV000001",
  "isCalibrated": true,
  "nextDue": "2026-01-21T10:00:00Z"
}
```

### GET /calibration/stats

Get calibration statistics.

**Response (200 OK):**
```json
{
  "totalDevices": 3,
  "totalCalibrations": 12,
  "passed": 11,
  "failed": 1,
  "overdue": 0
}
```

---

## Error Responses

All endpoints return standard error responses:

**400 Bad Request:**
```json
{
  "detail": "Invalid request: missing required field 'patientId'"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Invalid or expired token"
}
```

**403 Forbidden:**
```json
{
  "detail": "No valid consent found for patient PAT000001"
}
```

**404 Not Found:**
```json
{
  "detail": "Resource not found: Patient/PAT999999"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Database connection failed"
}
```

---

## Compliance Standards

### FHIR R5
- All resources conform to FHIR R5 specification
- Standard LOINC codes for observations
- Standard SNOMED codes for device types

### DPDP Act 2023 (Digital Personal Data Protection)
- Digital consent with signatures and witnesses
- Consent withdrawal capability
- Purpose-based access control
- Patient data access logs

### HIPAA 2025
- 6-year audit event retention
- Complete access logging
- Automatic audit event expiration
- Patient access report generation

### Medical Device Rules 2017 (India)
- Regular calibration tracking (2-month intervals)
- Calibration accuracy measurements
- Calibration due date alerts
- 5-year calibration history retention

### CSDS v2.0 (Coding Standard)
- All field names in camelCase
- No snake_case in API responses
- Consistent naming conventions

---

## Rate Limits

- **Authentication:** 10 requests/minute per IP
- **REST API:** 100 requests/minute per token
- **WebSocket:** 5 connections per user

---

## Support

For issues or questions:
- GitHub: [hospital-management-system](https://github.com/yourusername/hospital-management-system)
- Email: support@hospital.org
