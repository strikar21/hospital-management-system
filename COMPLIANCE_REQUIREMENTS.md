# Healthcare Compliance Requirements for FHIR R5-Based Vital Monitoring System in India

**Document Version:** 1.0
**Date:** 2025-11-21
**Focus:** Indian deployment with US HIPAA as secondary reference

---

## Executive Summary

This document outlines mandatory compliance requirements for deploying a FHIR R5-based wearable vital monitoring system in India. The system uses ESP32 watches for continuous patient monitoring with data transmitted to backend servers.

**Primary Regulations:**
1. Digital Personal Data Protection Act (DPDP) 2023
2. Medical Device Rules 2017
3. Clinical Establishments (Registration and Regulation) Act 2010
4. National Medical Council (NMC) Telemedicine Guidelines 2020

**Secondary Reference:** HIPAA (US) for technical best practices

---

## PART 1: MANDATORY INDIAN COMPLIANCE REQUIREMENTS

### 1.1 DPDP Act 2023 - Data Protection Requirements

#### 1.1.1 Consent Management (MANDATORY)
**Requirement:** Explicit and informed patient consent before collecting, processing, or sharing health data.

**Implementation:**
- Obtain written/electronic consent during admission
- Specify exact purposes: "continuous vital sign monitoring for clinical care"
- Allow purpose-specific consent (e.g., monitoring vs. research)
- Document consent withdrawal mechanism
- Store consent records with timestamps

**Timeline:** 18 months from Nov 2024 (by May 2026)

**Penalty:** Up to ₹250 crore for serious violations

#### 1.1.2 Encryption Requirements (MANDATORY)
**Requirement:** Strong encryption for data at rest and in transit.

**Implementation:**
- **In Transit:** TLS 1.3 for all API communications (watch → backend, backend → frontend)
- **At Rest:** AES-256 encryption for database storage
- **Additional:** Obfuscation/masking for PHI in logs
- **Tokens:** Virtual tokens for patient identifiers where possible

**Standards Reference:** Align with NIST SP 800-111 (at rest) and NIST SP 800-52 (in transit)

#### 1.1.3 Data Retention (MANDATORY)
**Requirement:** Retain data only as long as necessary; secure disposal when purpose fulfilled.

**Implementation:**
- **Access Logs:** Minimum 1 year (DPDP requirement)
- **Medical Records:** 3 years minimum (Clinical Establishments Act)
- **Audit Trails:** 6 years (align with HIPAA best practice)
- **Automatic Deletion:** When consent is withdrawn OR retention period expires
- **Backup Management:** Include deleted data in backup purging procedures

#### 1.1.4 Breach Notification (MANDATORY)
**Requirement:** Notify Data Protection Board of India (DPBI) and affected patients within 72 hours.

**Implementation:**
- Automated breach detection system
- Incident response plan with 72-hour timeline
- Notification template including:
  - Nature and extent of breach
  - Timing and location
  - Consequences and mitigation measures
  - Contact information for affected patients
- Maintain breach log for audit

**Timeline:** Immediate (DPBI provisions effective now)

#### 1.1.5 Patient Rights (MANDATORY)
**Requirement:** Enable patient access, correction, portability, and deletion rights.

**Implementation:**
- **Access:** Provide full medical records within 72 hours of request
- **Export:** FHIR R5 JSON format for data portability
- **Correction:** Allow patients to request data corrections (doctor approval required)
- **Deletion:** "Right to be forgotten" with legal retention exceptions
- **API Endpoint:** Patient portal for self-service requests

---

### 1.2 Medical Device Rules 2017

#### 1.2.1 Device Classification (MANDATORY)
**Classification:** ESP32 wearable vital monitors = **Class B** (low to moderate risk)

**Rationale:** Devices for direct diagnosis/monitoring of vital physiological processes = Class B

**Alternative:** If device provides active diagnostic feedback → **Class C** (moderate to high risk)

#### 1.2.2 Registration Requirements (MANDATORY)
**Implementation:**
- Register with Central Drugs Standard Control Organization (CDSCO)
- Submit technical file with device specifications
- Demonstrate safety and efficacy
- Obtain manufacturing/import license

**Timeline:** Before commercial deployment

#### 1.2.3 Calibration and Validation (MANDATORY)
**Requirement:** Regular calibration to ensure measurement accuracy.

**Implementation:**
- Establish calibration schedule (e.g., every 6 months)
- Document calibration procedures and results
- Maintain calibration logs per device
- Define acceptable tolerance ranges for vital signs:
  - Heart rate: ±5 bpm
  - SpO2: ±2%
  - Temperature: ±0.2°C
- Remove from service if out of calibration

#### 1.2.4 Post-Market Surveillance (MANDATORY)
**Requirement:** Track device performance and adverse events.

**Implementation:**
- Report serious adverse events to CDSCO
- Maintain complaint log
- Track device failures and accuracy issues
- Conduct periodic safety reviews

---

### 1.3 Clinical Establishments Act 2010

#### 1.3.1 Medical Record Maintenance (MANDATORY)
**Requirement:** Maintain comprehensive medical records with doctor oversight.

**Implementation:**
- **Retention:** Minimum 3 years from last treatment date
- **Format:** Electronic Medical Records (EMR) mandatory
- **Content:** All vitals readings with timestamps
- **Access:** Provide records within 72 hours of patient request
- **Doctor Signature:** All clinical interpretations must have RMP signature
- **Patient Identification:** Record at least one identification mark

#### 1.3.2 Doctor Oversight (MANDATORY)
**Requirement:** Registered Medical Practitioner (RMP) supervision for clinical decisions.

**Implementation:**
- Alert escalation requires RMP review
- Clinical interpretations signed by RMP (digital signature acceptable)
- RMP name printed below signature in government hospitals
- No autonomous clinical decisions without RMP approval

#### 1.3.3 Record Security (MANDATORY)
**Implementation:**
- Role-Based Access Control (RBAC) for EMR access
- Audit trail for all record access/modifications
- Backup procedures for data recovery
- Disaster recovery plan

---

### 1.4 NMC Telemedicine Guidelines 2020

#### 1.4.1 Applicability
**Scope:** Remote patient monitoring falls under telemedicine guidelines.

**Key Requirements:**
- RMP must complete online training (within 3 years of guideline notification)
- Maintain same ethics standards as in-person consultations
- Patient privacy and confidentiality (IMC Act 1956)

#### 1.4.2 Communication Standards
**Implementation:**
- Support text, audio, video communications for RMP consultation
- Secure communication channels (encrypted)
- Document all remote consultations

#### 1.4.3 Medication Prescriptions
**Limitation:** Follow Drugs and Cosmetics Act 1940 for telemedicine prescriptions.

**Implementation:**
- Categorize medications appropriately (List O, A, B, Prohibited)
- Restrict controlled substances via telemedicine
- Require in-person visit for prohibited medications

---

## PART 2: HIPAA COMPLIANCE (US REFERENCE - SECONDARY)

### 2.1 Technical Safeguards (2025 Updates)

#### 2.1.1 Access Control
**Requirement:** Role-Based Access Control (RBAC) ensuring users access only necessary ePHI.

**Implementation:**
- Unique user IDs for all system users
- Automatic logoff after inactivity
- Encryption and decryption controls
- Emergency access procedures

#### 2.1.2 Audit Controls
**Requirement:** Record and examine activity in systems containing ePHI.

**Implementation:**
- Log all ePHI access (who, what, when, where)
- 6-year audit log retention minimum
- Regular audit log review
- Automated alerting for suspicious activity

#### 2.1.3 Encryption (2025 Mandate)
**Major Change:** Encryption now MANDATORY (previously "addressable").

**Requirements:**
- Encryption at rest (NIST SP 800-111)
- Encryption in transit (NIST SP 800-52, TLS 1.3)
- Multi-Factor Authentication (MFA) for system access
- Network segmentation

#### 2.1.4 Annual Compliance Audit
**New Requirement (2025):** Annual security audit mandatory.

**Implementation:**
- Conduct comprehensive security risk assessment yearly
- Document findings and remediation plans
- Third-party audit recommended

---

## PART 3: FHIR R5 COMPLIANCE FEATURES

### 3.1 Core Compliance Resources

#### 3.1.1 Consent Resource
**Purpose:** Granular control over data sharing and patient consent management.

**Implementation:**
```json
{
  "resourceType": "Consent",
  "status": "active",
  "scope": {
    "coding": [{
      "system": "http://terminology.hl7.org/CodeSystem/consentscope",
      "code": "patient-privacy"
    }]
  },
  "patient": { "reference": "Patient/123" },
  "dateTime": "2025-11-21T10:30:00Z",
  "performer": [{ "reference": "Patient/123" }],
  "provision": {
    "type": "permit",
    "purpose": [{
      "system": "http://terminology.hl7.org/CodeSystem/v3-ActReason",
      "code": "TREAT"
    }],
    "period": {
      "start": "2025-11-21",
      "end": "2026-11-21"
    }
  }
}
```

**Features:**
- Time-bound consent periods
- Purpose-specific consent (treatment, research, billing)
- Granular data sharing controls
- Consent withdrawal tracking

#### 3.1.2 AuditEvent Resource
**Purpose:** Record security and privacy-relevant events.

**Implementation:**
```json
{
  "resourceType": "AuditEvent",
  "type": {
    "system": "http://dicom.nema.org/resources/ontology/DCM",
    "code": "110110",
    "display": "Patient Record"
  },
  "action": "R",
  "recorded": "2025-11-21T10:30:00Z",
  "agent": [{
    "type": {
      "coding": [{
        "system": "http://terminology.hl7.org/CodeSystem/extra-security-role-type",
        "code": "humanuser"
      }]
    },
    "who": { "reference": "Practitioner/456" },
    "requestor": true
  }],
  "entity": [{
    "what": { "reference": "Patient/123" },
    "type": {
      "system": "http://terminology.hl7.org/CodeSystem/audit-entity-type",
      "code": "1",
      "display": "Person"
    },
    "role": {
      "system": "http://terminology.hl7.org/CodeSystem/object-role",
      "code": "1",
      "display": "Patient"
    }
  }]
}
```

**Audit Actions:**
- **C**reate: New resource created
- **R**ead: Resource accessed/viewed
- **U**pdate: Resource modified
- **D**elete: Resource deleted/purged

**Compliance Use:**
- DPDP 1-year access log requirement
- HIPAA 6-year audit trail
- Privacy Accounting of Disclosures
- Breach investigation forensics

#### 3.1.3 Provenance Resource
**Purpose:** Track data lineage (who, what, when, where, why).

**Implementation:**
```json
{
  "resourceType": "Provenance",
  "target": [{ "reference": "Observation/789" }],
  "recorded": "2025-11-21T10:30:00Z",
  "activity": {
    "coding": [{
      "system": "http://terminology.hl7.org/CodeSystem/v3-DataOperation",
      "code": "CREATE"
    }]
  },
  "agent": [{
    "type": {
      "coding": [{
        "system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
        "code": "author"
      }]
    },
    "who": { "reference": "Device/esp32-watch-001" }
  }],
  "entity": [{
    "role": "source",
    "what": { "reference": "Device/esp32-watch-001" }
  }]
}
```

**Compliance Use:**
- Track data source (ESP32 watch vs. manual entry)
- Verify data integrity for regulatory audits
- Support data correction requests
- Establish chain of custody

### 3.2 Data Retention and Deletion in FHIR

#### 3.2.1 Logical Delete
**FHIR Operation:** `DELETE /fhir/Patient/123`

**Behavior:**
- Resource marked as deleted (HTTP 410 Gone)
- Moved to history repository
- Still retrievable via `vread` for audit purposes
- Satisfies "soft delete" for legal retention

#### 3.2.2 Hard Delete (Expunge)
**FHIR Operation:** `$expunge` operation

**Behavior:**
- Physically removes data from database
- Irreversible deletion
- Use for "right to be forgotten" after retention period
- Must also purge backups and logs

**Implementation Considerations:**
- Schedule expunge operations after DPDP/Clinical Establishments Act retention periods
- Document expunge operations in audit log
- Legal review before expunging (active litigation holds)

#### 3.2.3 Patient Data Export
**FHIR Operation:** `$export` or Bulk Data API

**Compliance:**
- Supports DPDP "right to data portability"
- Export entire patient record as FHIR Bundle
- Standardized format for interoperability
- Within 72-hour timeframe (Clinical Establishments Act)

---

## PART 4: MINIMAL COMPLIANCE CHECKLIST FOR MVP

### 4.1 MANDATORY for Indian MVP Deployment

#### Database Layer
- [ ] **Consent Management Table** - Track patient consent with timestamps
- [ ] **AuditEvent Table** - Log all data access (1-year retention minimum)
- [ ] **User Authentication** - Unique user IDs, password policies, MFA recommended
- [ ] **Role-Based Access Control (RBAC)** - Nurse, Doctor, Admin roles
- [ ] **Data Encryption at Rest** - AES-256 for database
- [ ] **Backup Procedures** - Automated backups with encryption

#### API Layer
- [ ] **TLS 1.3 Encryption** - All communications encrypted in transit
- [ ] **API Authentication** - JWT tokens with expiration
- [ ] **Rate Limiting** - Prevent brute force attacks
- [ ] **Input Validation** - Prevent SQL injection, XSS
- [ ] **Consent Verification** - Check consent before data access
- [ ] **Audit Logging Middleware** - Log all API requests

#### Business Logic
- [ ] **RMP Oversight** - All alerts require doctor review/signature
- [ ] **Consent Workflow** - Admission process includes consent form
- [ ] **Data Retention Policy** - Automated deletion after 3 years (configurable)
- [ ] **Patient Portal** - Self-service data access/export (72-hour SLA)
- [ ] **Breach Response Plan** - 72-hour notification procedure

#### Device Management
- [ ] **Device Registration** - Track each ESP32 watch with serial number
- [ ] **Calibration Tracking** - Schedule and log calibration events
- [ ] **Device Assignment** - Map device to patient during admission
- [ ] **Device Decommissioning** - Secure data wipe on discharge

#### Compliance Documentation
- [ ] **Privacy Policy** - Patient-facing document in English + Hindi
- [ ] **Consent Form Template** - Legal review for DPDP compliance
- [ ] **Data Retention Schedule** - Document retention periods by data type
- [ ] **Incident Response Plan** - Breach notification procedures
- [ ] **Security Policies** - Password, access control, encryption standards
- [ ] **Training Materials** - Staff training on privacy and security

### 4.2 ADDITIONAL FHIR Resources Beyond 4-Table Minimal Plan

Your current minimal plan likely includes:
1. **Patient** - Demographics
2. **Device** - ESP32 watches
3. **Observation** - Vital signs (TimescaleDB)
4. **Practitioner** - Doctors/nurses

**MANDATORY Additions for Compliance:**

5. **Consent** - Patient consent management (DPDP requirement)
6. **AuditEvent** - Access logging (DPDP 1-year retention)
7. **Provenance** - Data lineage tracking (optional but recommended)

**Recommended Additions:**

8. **Organization** - Hospital/clinic information
9. **Location** - Room/bed tracking for door scanner integration
10. **Encounter** - Admission/discharge tracking
11. **Condition** - Diagnoses linked to monitoring
12. **CarePlan** - Treatment plans requiring monitoring

### 4.3 MVP Timeline and Priorities

#### Phase 1: Pre-Launch (MANDATORY)
- Implement encryption (at rest + in transit)
- Build Consent resource and workflow
- Build AuditEvent logging
- Establish RBAC system
- Create privacy policy and consent forms
- Conduct internal security audit

#### Phase 2: Launch (MANDATORY)
- Register devices with CDSCO (Class B)
- Train staff on privacy procedures
- Enable patient portal for data access
- Establish breach response team
- Document all policies and procedures

#### Phase 3: Post-Launch (MANDATORY)
- Monitor audit logs monthly
- Conduct annual compliance audit
- Review and update policies annually
- Track device calibration schedule
- Submit post-market surveillance reports to CDSCO

---

## PART 5: COMPLIANCE GAPS AND RECOMMENDATIONS

### 5.1 Technical Architecture Recommendations

#### 5.1.1 Database Schema
```sql
-- Consent Management (MANDATORY)
CREATE TABLE fhir_consent (
    id UUID PRIMARY KEY,
    patientId UUID REFERENCES fhir_patient(id),
    status VARCHAR(20) NOT NULL, -- active, inactive, withdrawn
    scope VARCHAR(50) NOT NULL, -- patient-privacy, research
    purpose VARCHAR(50)[], -- treatment, payment, research
    consentDate TIMESTAMP NOT NULL,
    effectiveStart TIMESTAMP NOT NULL,
    effectiveEnd TIMESTAMP,
    performerId UUID, -- who gave consent
    grantorSignature TEXT, -- digital signature
    createdAt TIMESTAMP DEFAULT NOW(),
    updatedAt TIMESTAMP DEFAULT NOW()
);

-- Audit Events (MANDATORY)
CREATE TABLE fhir_audit_event (
    id UUID PRIMARY KEY,
    eventType VARCHAR(50) NOT NULL, -- patient-record, device-data
    action CHAR(1) NOT NULL, -- C, R, U, D
    recorded TIMESTAMP NOT NULL,
    agentType VARCHAR(50), -- humanuser, device
    agentId UUID, -- Practitioner or Device reference
    patientId UUID, -- subject of event
    entityType VARCHAR(50),
    entityId UUID,
    outcome VARCHAR(20), -- success, failure
    ipAddress INET,
    userAgent TEXT,
    -- Retention: 1 year minimum (DPDP), 6 years recommended (HIPAA)
    expiresAt TIMESTAMP DEFAULT NOW() + INTERVAL '6 years'
);

-- Device Calibration (MANDATORY)
CREATE TABLE device_calibration_log (
    id UUID PRIMARY KEY,
    deviceId UUID REFERENCES fhir_device(id),
    calibrationDate TIMESTAMP NOT NULL,
    performedBy UUID REFERENCES fhir_practitioner(id),
    heartRateAccuracy DECIMAL(5,2), -- +/- bpm
    spo2Accuracy DECIMAL(5,2), -- +/- percentage
    temperatureAccuracy DECIMAL(5,2), -- +/- degrees
    status VARCHAR(20), -- pass, fail
    nextCalibrationDue TIMESTAMP,
    notes TEXT
);

-- Data Retention Tracking
CREATE TABLE data_retention_schedule (
    id UUID PRIMARY KEY,
    resourceType VARCHAR(50) NOT NULL,
    retentionYears INTEGER NOT NULL,
    legalBasis TEXT,
    autoDelete BOOLEAN DEFAULT TRUE
);
```

#### 5.1.2 API Middleware (Compliance Layer)
```javascript
// Consent Verification Middleware
async function verifyConsent(req, res, next) {
    const patientId = req.params.patientId;
    const purpose = req.headers['x-access-purpose']; // treatment, research

    const consent = await getActiveConsent(patientId, purpose);
    if (!consent || consent.status !== 'active') {
        await logAuditEvent({
            action: 'R',
            outcome: 'failure',
            reason: 'no-active-consent',
            patientId,
            agentId: req.user.id
        });
        return res.status(403).json({ error: 'No active consent for this purpose' });
    }

    req.consent = consent;
    next();
}

// Audit Logging Middleware
async function auditLog(req, res, next) {
    const startTime = Date.now();

    res.on('finish', async () => {
        await createAuditEvent({
            eventType: 'patient-record',
            action: mapHttpMethodToAction(req.method),
            recorded: new Date(),
            agentId: req.user?.id,
            patientId: req.params.patientId,
            outcome: res.statusCode < 400 ? 'success' : 'failure',
            ipAddress: req.ip,
            userAgent: req.headers['user-agent'],
            duration: Date.now() - startTime
        });
    });

    next();
}
```

### 5.2 Compliance Gaps in Current Architecture

Based on your project structure, potential gaps include:

1. **Missing Consent Management** - No evidence of FHIR Consent resource implementation
2. **Incomplete Audit Logging** - May not capture all required access events
3. **Device Calibration Tracking** - Required for Medical Device Rules 2017
4. **Patient Portal** - Need self-service data access for DPDP compliance
5. **Data Retention Automation** - No automated deletion after retention periods
6. **Breach Response Procedures** - Must document 72-hour notification workflow
7. **RMP Digital Signatures** - Clinical interpretations need doctor sign-off
8. **Training Documentation** - Staff training records for compliance audits

### 5.3 Priority Implementation Roadmap

**Week 1-2: Critical Security**
- Implement TLS 1.3 for all APIs
- Enable AES-256 database encryption
- Deploy RBAC system
- Set up audit logging middleware

**Week 3-4: DPDP Compliance**
- Build Consent resource and API
- Create consent form templates
- Implement consent verification in API
- Build patient portal (data access/export)

**Week 5-6: Medical Device Compliance**
- Register devices with CDSCO
- Build calibration tracking system
- Document device specifications
- Create post-market surveillance procedures

**Week 7-8: Documentation and Testing**
- Finalize privacy policy
- Create incident response plan
- Conduct security penetration testing
- Train staff on compliance procedures

---

## PART 6: ONGOING COMPLIANCE OBLIGATIONS

### 6.1 Daily/Weekly Operations
- Monitor system access logs for anomalies
- Review failed login attempts
- Check device connectivity status
- Respond to patient data requests (72-hour SLA)

### 6.2 Monthly Tasks
- Review audit logs for unauthorized access
- Check device calibration due dates
- Update staff on policy changes
- Backup verification and testing

### 6.3 Annual Requirements
- Conduct comprehensive security audit (HIPAA 2025 requirement)
- Review and update privacy policies
- Staff compliance training refresh
- CDSCO post-market surveillance report
- Data retention policy review

### 6.4 Event-Driven Obligations
- Breach notification within 72 hours (DPDP)
- Adverse event reporting to CDSCO (immediate for serious events)
- Patient complaint investigation and response
- Consent withdrawal processing (immediate)

---

## PART 7: CONCLUSION AND RECOMMENDATIONS

### 7.1 Key Takeaways

1. **DPDP Act 2023 is the cornerstone** - Encryption, consent, breach notification, and patient rights are non-negotiable.

2. **FHIR R5 provides built-in compliance tools** - Consent, AuditEvent, and Provenance resources align perfectly with Indian regulations.

3. **Medical Device Rules require registration** - ESP32 watches are Class B devices requiring CDSCO registration and calibration.

4. **Doctor oversight is mandatory** - All clinical decisions require RMP review and digital signature.

5. **18-month implementation window** - DPDP compliance obligations take effect by May 2026.

### 7.2 Minimal Compliance = 7 FHIR Resources

Your MVP must include:
1. **Patient** - Demographics
2. **Device** - ESP32 watches + calibration tracking
3. **Observation** - Vital signs (TimescaleDB)
4. **Practitioner** - RMPs with digital signature capability
5. **Consent** - MANDATORY for DPDP compliance
6. **AuditEvent** - MANDATORY for access logging
7. **Organization** - Hospital registration information

**Optional but Recommended:**
8. Provenance - Data lineage tracking
9. Encounter - Admission/discharge workflow
10. Location - Room/bed tracking for door scanners

### 7.3 Budget Implications

**Compliance Costs:**
- CDSCO device registration: ₹50,000 - ₹2,00,000 (one-time)
- Annual security audit: ₹1,00,000 - ₹5,00,000
- Legal consultation (privacy policy, consent forms): ₹50,000 - ₹1,50,000
- Staff training: ₹25,000 - ₹50,000 annually
- Encryption infrastructure (HSM, key management): ₹2,00,000 - ₹10,00,000

**Penalty Avoidance:**
- DPDP non-compliance: Up to ₹250 crore
- Medical Device Rules violation: License suspension + penalties
- Clinical Establishments Act: Registration cancellation

### 7.4 Final Recommendation

**DO NOT DEPLOY WITHOUT:**
1. Encryption (at rest + in transit)
2. Consent management system
3. Audit logging (1-year minimum retention)
4. RBAC with unique user IDs
5. Privacy policy and consent forms (legal review)
6. Breach response plan (72-hour timeline)
7. CDSCO device registration (Class B)

**DEPLOY WITH CONFIDENCE AFTER:**
1. Internal security audit completed
2. Staff trained on compliance procedures
3. Patient portal functional (72-hour data access)
4. Calibration tracking system operational
5. Backup and disaster recovery tested
6. All policies documented and approved

---

## APPENDIX A: Useful Resources

### Indian Regulations
- **DPDP Rules 2025:** https://www.meity.gov.in/
- **Clinical Establishments Act 2010:** https://clinicalestablishments.mohfw.gov.in/
- **Medical Device Rules 2017:** https://cdsco.gov.in/
- **NMC Telemedicine Guidelines:** https://www.nmc.org.in/

### FHIR R5 Specifications
- **Consent Resource:** https://hl7.org/fhir/R5/consent.html
- **AuditEvent Resource:** https://hl7.org/fhir/R5/auditevent.html
- **Provenance Resource:** https://hl7.org/fhir/R5/provenance.html
- **Security and Privacy Module:** https://hl7.org/fhir/R5/secpriv-module.html

### Standards and Best Practices
- **NIST SP 800-111:** Guide to Storage Encryption Technologies
- **NIST SP 800-52:** TLS Implementation Guidance
- **HL7 FHIR Security:** https://www.hl7.org/fhir/security.html

---

**Document Prepared By:** Claude (Anthropic AI)
**Review Status:** Draft - Requires legal review before implementation
**Next Review Date:** 2026-05-21 (6 months before DPDP full compliance deadline)
