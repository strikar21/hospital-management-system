# Complete FHIR R5 System - Final Execution Plan

**System**: Minimal FHIR R5 core + pluggable device modules + compliance + CSDS v2.0

**Timeline**: 3 weeks

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  DEVICE MODULES (Pluggable)                      │
│  - ESP32 Watch Module (MQTT → FHIR Observations)                │
│  - Door Scanner Module (NFC → FHIR Observations/AuditEvents)    │
│  - Future Devices (any protocol → FHIR resources)               │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│               FHIR R5 CORE DATABASE (7 tables)                   │
│                                                                  │
│  PostgreSQL (5 tables):                                          │
│  1. fhirResources - All FHIR R5 resources (JSONB)               │
│  2. fhirConsent - Patient consent tracking (DPDP 2023)          │
│  3. fhirAuditEvent - Access logs (DPDP + HIPAA)                 │
│  4. staff - Authentication (NFC badge, PIN, password)            │
│  5. tokenBlacklist - JWT revocation                              │
│                                                                  │
│  TimescaleDB (2 hypertables):                                    │
│  6. fhirObservations - Time-series vitals (1 year)              │
│  7. deviceCalibration - Calibration logs (Medical Device Rules) │
└─────────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FHIR R5 REST API                              │
│  GET  /fhir/R5/Patient?identifier={mrn}                         │
│  GET  /fhir/R5/Device?status=active                             │
│  GET  /fhir/R5/Observation?patient={id}&code={loinc}            │
│  GET  /fhir/R5/Consent?patient={id}&status=active               │
│  GET  /fhir/R5/AuditEvent?agent={staffId}&date=ge{ts}           │
│  POST /fhir/R5/DeviceAssociation                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema (7 Tables + CSDS v2.0)

**CSDS v2.0**: ALL fields use camelCase (no snake_case, no PascalCase, no kebab-case)

### PostgreSQL (5 tables)

```sql
-- =============================================================================
-- 1. fhirResources (Core FHIR R5 storage)
-- =============================================================================
CREATE TABLE fhirResources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- FHIR identity (CSDS: camelCase)
    resourceType TEXT NOT NULL,        -- Patient, Device, Observation, etc.
    resourceId TEXT NOT NULL,          -- Business ID (PAT001, DEV001)
    resource JSONB NOT NULL,           -- Full FHIR R5 JSON

    -- Extracted fields for fast queries (CSDS: camelCase)
    status TEXT,                       -- active, inactive, etc.
    subject TEXT,                      -- Patient/{id}

    -- Versioning (CSDS: camelCase)
    versionId INTEGER DEFAULT 1,
    deleted BOOLEAN DEFAULT false,

    -- Audit (CSDS: camelCase)
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_fhir_resource UNIQUE (resourceType, resourceId, deleted)
);

CREATE INDEX idx_fhir_type ON fhirResources(resourceType) WHERE deleted = false;
CREATE INDEX idx_fhir_type_id ON fhirResources(resourceType, resourceId) WHERE deleted = false;
CREATE INDEX idx_fhir_subject ON fhirResources(subject) WHERE deleted = false;
CREATE INDEX idx_fhir_resource_gin ON fhirResources USING gin(resource);

-- =============================================================================
-- 2. fhirConsent (DPDP Act 2023 Compliance)
-- =============================================================================
CREATE TABLE fhirConsent (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Patient (CSDS: camelCase)
    patientId TEXT NOT NULL,           -- Patient/{id}

    -- Consent details (CSDS: camelCase)
    status TEXT NOT NULL DEFAULT 'active',  -- active | withdrawn | expired
    scope TEXT NOT NULL,               -- patient-privacy | research | treatment
    category TEXT[] NOT NULL,          -- ["IDSCL", "RESEARCH"]

    -- Purpose (CSDS: camelCase)
    purposeOfUse TEXT[] NOT NULL,      -- ["TREAT", "ETREAT", "HPAYMT"]

    -- Period (CSDS: camelCase)
    effectiveStart TIMESTAMPTZ NOT NULL,
    effectiveEnd TIMESTAMPTZ,

    -- Signature (CSDS: camelCase)
    grantorSignature TEXT,             -- Base64 signature
    witnessSignature TEXT,             -- Staff signature

    -- Audit (CSDS: camelCase)
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    createdBy TEXT NOT NULL,           -- Staff/{id}
    withdrawnAt TIMESTAMPTZ,
    withdrawnBy TEXT,

    CONSTRAINT valid_consent_period CHECK (effectiveEnd IS NULL OR effectiveEnd > effectiveStart)
);

CREATE INDEX idx_consent_patient ON fhirConsent(patientId, status);
CREATE INDEX idx_consent_active ON fhirConsent(status, effectiveStart, effectiveEnd)
    WHERE status = 'active';

-- =============================================================================
-- 3. fhirAuditEvent (DPDP + HIPAA Compliance)
-- =============================================================================
CREATE TABLE fhirAuditEvent (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Action (CSDS: camelCase)
    action CHAR(1) NOT NULL,           -- C, R, U, D, E (create, read, update, delete, execute)
    outcome TEXT NOT NULL DEFAULT 'success',  -- success | failure

    -- Who (CSDS: camelCase)
    agentId TEXT NOT NULL,             -- Staff/{id} who performed action
    agentRole TEXT NOT NULL,           -- doctor | nurse | admin

    -- What (CSDS: camelCase)
    entityType TEXT NOT NULL,          -- Patient | Device | Observation
    entityId TEXT NOT NULL,            -- Resource ID accessed

    -- When/Where (CSDS: camelCase)
    recorded TIMESTAMPTZ DEFAULT NOW(),
    ipAddress INET,
    userAgent TEXT,

    -- Purpose (CSDS: camelCase)
    purposeOfEvent TEXT,               -- TREAT | ETREAT | HPAYMT

    -- Retention (DPDP: 1 year minimum, HIPAA: 6 years)
    expiresAt TIMESTAMPTZ DEFAULT NOW() + INTERVAL '6 years'
);

CREATE INDEX idx_audit_agent ON fhirAuditEvent(agentId, recorded DESC);
CREATE INDEX idx_audit_entity ON fhirAuditEvent(entityType, entityId, recorded DESC);
CREATE INDEX idx_audit_recorded ON fhirAuditEvent(recorded DESC);
CREATE INDEX idx_audit_expires ON fhirAuditEvent(expiresAt) WHERE expiresAt < NOW();

-- =============================================================================
-- 4. staff (Authentication - NOT FHIR)
-- =============================================================================
CREATE TABLE staff (
    id TEXT PRIMARY KEY,               -- STF000001 (CSDS: camelCase)

    -- Identity (CSDS: camelCase)
    nfcBadgeId TEXT UNIQUE,
    pin TEXT,
    passwordHash TEXT,

    -- Role (CSDS: camelCase)
    role TEXT NOT NULL CHECK (role IN ('doctor', 'nurse', 'admin', 'technician')),

    -- Status (CSDS: camelCase)
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),

    -- Audit (CSDS: camelCase)
    createdAt TIMESTAMPTZ DEFAULT NOW(),
    updatedAt TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_staff_nfc ON staff(nfcBadgeId) WHERE nfcBadgeId IS NOT NULL;
CREATE INDEX idx_staff_role ON staff(role, status) WHERE status = 'active';

-- NOTE: Staff full details (name, email, qualifications) stored as FHIR Practitioner
--       resource in fhirResources table

-- =============================================================================
-- 5. tokenBlacklist (JWT Revocation - NOT FHIR)
-- =============================================================================
CREATE TABLE tokenBlacklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token TEXT UNIQUE NOT NULL,
    blacklistedAt TIMESTAMPTZ DEFAULT NOW(),  -- CSDS: camelCase
    expiresAt TIMESTAMPTZ NOT NULL             -- CSDS: camelCase
);

CREATE INDEX idx_token_expires ON tokenBlacklist(expiresAt);
```

### TimescaleDB (2 hypertables)

```sql
-- =============================================================================
-- 6. fhirObservations (Time-series FHIR Observations)
-- =============================================================================
CREATE TABLE fhirObservations (
    time TIMESTAMPTZ NOT NULL,

    -- FHIR identity (CSDS: camelCase)
    observationId TEXT NOT NULL,
    patientId TEXT NOT NULL,
    deviceId TEXT,

    -- Full FHIR R5 Observation resource
    observation JSONB NOT NULL,

    -- Extracted fields for fast queries (CSDS: camelCase)
    code TEXT NOT NULL,                -- LOINC code (e.g., "8867-4")
    category TEXT,                     -- vital-signs | activity | access-log
    valueQuantity NUMERIC(10,2),
    valueUnit TEXT,
    status TEXT NOT NULL,              -- registered | preliminary | final

    -- Audit (CSDS: camelCase)
    createdAt TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('fhirObservations', 'time', if_not_exists => TRUE);

-- Retention: 1 year (DPDP 2023 minimum)
SELECT add_retention_policy('fhirObservations', INTERVAL '1 year', if_not_exists => TRUE);

CREATE INDEX idx_fhir_obs_patient ON fhirObservations(patientId, time DESC);
CREATE INDEX idx_fhir_obs_code ON fhirObservations(code, patientId, time DESC);
CREATE INDEX idx_fhir_obs_category ON fhirObservations(category, time DESC);
CREATE INDEX idx_fhir_obs_gin ON fhirObservations USING gin(observation);

-- =============================================================================
-- 7. deviceCalibration (Medical Device Rules 2017 Compliance)
-- =============================================================================
CREATE TABLE deviceCalibration (
    time TIMESTAMPTZ NOT NULL,

    -- Device (CSDS: camelCase)
    deviceId TEXT NOT NULL,            -- Device/{id}

    -- Calibration details (CSDS: camelCase)
    calibrationType TEXT NOT NULL,     -- routine | post-repair | initial
    performedBy TEXT NOT NULL,         -- Staff/{id}

    -- Accuracy measurements (CSDS: camelCase)
    heartRateAccuracy NUMERIC(5,2),    -- % accuracy
    spo2Accuracy NUMERIC(5,2),
    temperatureAccuracy NUMERIC(5,2),
    bloodPressureAccuracy NUMERIC(5,2),

    -- Result (CSDS: camelCase)
    status TEXT NOT NULL,              -- pass | fail | conditional
    notes TEXT,

    -- Next calibration (CSDS: camelCase)
    nextCalibrationDue TIMESTAMPTZ NOT NULL,

    -- Audit (CSDS: camelCase)
    createdAt TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('deviceCalibration', 'time', if_not_exists => TRUE);

-- Retention: 5 years (device lifetime)
SELECT add_retention_policy('deviceCalibration', INTERVAL '5 years', if_not_exists => TRUE);

CREATE INDEX idx_device_cal_device ON deviceCalibration(deviceId, time DESC);
CREATE INDEX idx_device_cal_next_due ON deviceCalibration(nextCalibrationDue) WHERE status = 'pass';
```

---

## FHIR R5 Resources (What We Store)

### 1. Patient (from HMS, cached)
```json
{
  "resourceType": "Patient",
  "id": "PAT000001",
  "identifier": [
    { "system": "http://hospital.example.com/mrn", "value": "MRN12345" },
    { "system": "https://healthid.ndhm.gov.in", "value": "john@abdm" }
  ],
  "name": [{ "family": "Doe", "given": ["John"] }],
  "gender": "male",
  "birthDate": "1980-05-15"
}
```

### 2. Device (ESP32 watch, door scanner)
```json
{
  "resourceType": "Device",
  "id": "DEV000001",
  "type": [{ "coding": [{ "code": "706767009", "display": "Patient monitoring system" }] }],
  "status": "active",
  "property": [
    { "type": { "text": "batteryLevel" }, "valueQuantity": [{ "value": 85, "unit": "%" }] },
    { "type": { "text": "lastCalibrated" }, "valueDateTime": "2025-11-01T00:00:00Z" }
  ]
}
```

### 3. Observation (vitals, access logs)
```json
{
  "resourceType": "Observation",
  "id": "OBS-HR-001",
  "status": "final",
  "category": [{ "coding": [{ "code": "vital-signs" }] }],
  "code": { "coding": [{ "system": "http://loinc.org", "code": "8867-4", "display": "Heart rate" }] },
  "subject": { "reference": "Patient/PAT000001" },
  "device": { "reference": "Device/DEV000001" },
  "effectiveDateTime": "2025-11-21T10:30:00Z",
  "valueQuantity": { "value": 78, "unit": "beats/minute" }
}
```

### 4. Consent (DPDP 2023 compliance)
```json
{
  "resourceType": "Consent",
  "id": "CONSENT-001",
  "status": "active",
  "scope": { "coding": [{ "code": "patient-privacy" }] },
  "category": [{ "coding": [{ "code": "IDSCL" }] }],
  "patient": { "reference": "Patient/PAT000001" },
  "dateTime": "2025-11-21T08:00:00Z",
  "provision": {
    "type": "permit",
    "period": { "start": "2025-11-21T08:00:00Z", "end": "2026-11-21T08:00:00Z" },
    "purpose": [{ "code": "TREAT" }, { "code": "ETREAT" }]
  }
}
```

### 5. AuditEvent (access logging)
```json
{
  "resourceType": "AuditEvent",
  "id": "AUDIT-001",
  "type": { "code": "R", "display": "Read" },
  "recorded": "2025-11-21T10:30:00Z",
  "outcome": "success",
  "agent": [{ "who": { "reference": "Practitioner/STF000001" }, "role": [{ "text": "nurse" }] }],
  "entity": [{ "what": { "reference": "Patient/PAT000001" } }],
  "source": { "site": "Hospital ICU Dashboard" }
}
```

### 6. DeviceAssociation (device ↔ patient)
```json
{
  "resourceType": "DeviceAssociation",
  "id": "ASSOC-001",
  "status": { "coding": [{ "code": "active" }] },
  "subject": { "reference": "Patient/PAT000001" },
  "device": { "reference": "Device/DEV000001" },
  "period": { "start": "2025-11-21T08:00:00Z" }
}
```

### 7. Practitioner (staff details)
```json
{
  "resourceType": "Practitioner",
  "id": "PRAC-STF000001",
  "identifier": [{ "system": "http://hospital.example.com/staff", "value": "STF000001" }],
  "name": [{ "family": "Johnson", "given": ["Sarah"], "prefix": ["Dr."] }],
  "qualification": [{ "code": { "coding": [{ "code": "MD" }] } }]
}
```

---

## FHIR R5 API Endpoints

```
# Patient
GET  /fhir/R5/Patient?identifier=MRN12345

# Device
GET  /fhir/R5/Device?status=active&type=watch
POST /fhir/R5/Device

# Observation
GET  /fhir/R5/Observation?patient={id}&code=8867-4&date=ge{ts}
POST /fhir/R5/Observation

# Consent (DPDP 2023)
GET  /fhir/R5/Consent?patient={id}&status=active
POST /fhir/R5/Consent
PATCH /fhir/R5/Consent/{id}  # Withdraw consent

# AuditEvent (DPDP + HIPAA)
GET  /fhir/R5/AuditEvent?agent={staffId}&date=ge{ts}
POST /fhir/R5/AuditEvent

# DeviceAssociation
GET  /fhir/R5/DeviceAssociation?subject={patientId}&status=active
POST /fhir/R5/DeviceAssociation
PATCH /fhir/R5/DeviceAssociation/{id}
```

---

## Device Modules (Pluggable)

### ESP32 Watch Module
**File**: `app/modules/esp32_watch/adapter.py`

- MQTT vitals → FHIR Observations
- Heart rate, SpO2, temp, BP, RR (LOINC codes)
- Alert detection (threshold violations)

### Door Scanner Module
**File**: `app/modules/door_scanner/adapter.py`

- NFC tap → FHIR AuditEvent (access log)
- Staff-patient interaction tracking
- DPDP 2023 compliance (who accessed which patient)

### Future Devices
- Just implement adapter interface
- Convert device data → FHIR resources
- No database changes needed!

---

## Implementation Timeline (3 Weeks)

### Week 1: FHIR Core + Compliance

**Day 1: Database Clean Slate**
- [ ] Backup current database
- [ ] Drop all existing tables
- [ ] Create 7 new tables (PostgreSQL + TimescaleDB)
- [ ] Verify CSDS v2.0 compliance (all camelCase)

**Day 2: FHIR Core Services**
- [ ] FHIRResourceRepository (CRUD + search + versioning)
- [ ] Patient handler (GET only - from HMS)
- [ ] Device handler (GET, POST, PATCH)
- [ ] Observation handler (GET, POST)
- [ ] DeviceAssociation handler (GET, POST, PATCH)

**Day 3: Compliance Services**
- [ ] Consent handler (GET, POST, PATCH - withdraw)
- [ ] AuditEvent handler (POST only - auto-logged)
- [ ] Audit logging middleware (intercepts all API calls)

**Day 4: Seed Data + Tests**
- [ ] Seed: 2 staff (with NFC badges), 3 devices, 0 patients
- [ ] Test: Create consent, verify audit logging
- [ ] Test: FHIR search queries

**Day 5: HMS Mock API**
- [ ] Mock HMS with 2 fake patients
- [ ] Test: Pull patient data from HMS
- [ ] Test: Create DeviceAssociation

### Week 2: Device Modules

**Day 1-2: ESP32 Watch Module**
- [ ] ESP32WatchAdapter (MQTT → FHIR Observations)
- [ ] Convert vitals → FHIR (LOINC codes)
- [ ] Alert detection (threshold violations)
- [ ] Test: ESP32 → MQTT → FHIR Observations in TimescaleDB

**Day 3: Door Scanner Module**
- [ ] DoorScannerAdapter (NFC → FHIR AuditEvent)
- [ ] Access log with staff-patient linking
- [ ] Test: NFC tap → creates AuditEvent

**Day 4: Device Calibration**
- [ ] Calibration logging service
- [ ] Store calibration data in deviceCalibration table
- [ ] Next calibration due alerts

**Day 5: WebSocket + Real-time**
- [ ] WebSocket broadcasts FHIR Observations
- [ ] WebSocket broadcasts AuditEvents
- [ ] Test: Real-time vitals streaming

### Week 3: Frontend + Testing

**Day 1-2: Frontend Dashboard**
- [ ] Patient list (from HMS API)
- [ ] Assign watch (creates DeviceAssociation)
- [ ] Live vitals display (WebSocket → FHIR Observations)
- [ ] Alert list (FHIR Flag resources)

**Day 3: Consent Management UI**
- [ ] Consent form (digital signature)
- [ ] Consent withdrawal button
- [ ] Consent status display

**Day 4: Testing + Documentation**
- [ ] End-to-end test: Login → assign watch → monitor → see audit logs
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Module developer guide (for future devices)

**Day 5: Cleanup + Release**
- [ ] Remove all old HMS endpoints
- [ ] Remove legacy code
- [ ] Final code review
- [ ] Tag release: v1.0.0

---

## CSDS v2.0 Compliance Checklist

**ALL fields must be camelCase:**

✅ Database columns: `patientId`, `createdAt`, `nfcBadgeId`
✅ API request/response: `{ "patientId": "PAT001", "firstName": "John" }`
✅ FHIR resource fields: Already camelCase (FHIR R5 standard)
✅ MQTT payload fields: `{ "deviceId": "DEV001", "heartRate": 78 }`
✅ Frontend properties: `patientId`, `deviceStatus`, `createdAt`

**NO snake_case, NO PascalCase (except class names), NO kebab-case**

---

## Compliance Summary

### DPDP Act 2023
- ✅ Consent management (fhirConsent table)
- ✅ Access logging (fhirAuditEvent table, 1-year retention)
- ✅ Data retention (1 year vitals, 6 years audit logs)
- ✅ Encryption (TLS 1.3 in transit, AES-256 at rest)

### HIPAA 2025
- ✅ Audit trails (fhirAuditEvent, 6-year retention)
- ✅ Encryption (mandatory in 2025)
- ✅ Access control (RBAC via staff.role)

### Medical Device Rules 2017
- ✅ Calibration tracking (deviceCalibration table)
- ✅ Post-market surveillance (device maintenance logs)

### Clinical Establishments Act 2010
- ✅ 3-year medical record retention (FHIR resources + observations)
- ✅ RMP oversight (Practitioner resources)

---

## Success Criteria

### Week 1 ✅
- 7 tables created (all camelCase)
- FHIR core services working
- Consent + audit logging functional

### Week 2 ✅
- ESP32 watch → FHIR Observations
- Door scanner → FHIR AuditEvents
- Device calibration tracking
- Real-time WebSocket streaming

### Week 3 ✅
- Full workflow: consent → assign watch → monitor → audit logs
- API documentation complete
- Module developer guide complete
- Zero legacy HMS code

---

## Ready to Execute?

Type "yes" to start **Week 1, Day 1**:
1. Backup database
2. Drop all tables (clean slate)
3. Create 7 new tables (CSDS v2.0 + compliance)
4. Seed test data
