# Hospital System - Unified CamelCase Migration Schema

## Master Field Mapping

### Core Entity IDs
```
patient_id → patientId
device_id → deviceId  
staff_id → staffId
user_id → userId
assignment_id → assignmentId
therapy_id → therapyId
investigation_id → investigationId
```

### Unified "By" Fields (STANDARDIZED)
```
prescribed_by → createdBy
ordered_by → createdBy
assigned_by → assignedBy
performed_by → createdBy
recorded_by → createdBy
unassigned_by → unassignedBy
completed_by → completedBy
```

### Unified Time Fields (STANDARDIZED)
```
created_at → createdAt
updated_at → updatedAt
assigned_at → assignedAt
unassigned_at → unassignedAt
ordered_date → orderedAt
completed_date → completedAt
start_date → startedAt
end_date → endedAt
recorded_date → recordedAt
```

### Medical/Vital Fields
```
heart_rate → heartRate
blood_pressure → bloodPressure
blood_pressure_systolic → bloodPressureSystolic
blood_pressure_diastolic → bloodPressureDiastolic
oxygen_saturation → oxygenSaturation
respiratory_rate → respiratoryRate
ecg_value → ecgValue
eeg_value → eegValue
fall_risk → fallRisk
vital_type → vitalType
```

### Device Fields
```
device_type → deviceType
device_name → deviceName
device_token → deviceToken
mac_address → macAddress
ip_address → ipAddress
firmware_version → firmwareVersion
battery_level → batteryLevel
signal_strength → signalStrength
last_seen → lastSeen
last_heartbeat → lastHeartbeat
assignment_status → status (context: assignments)
quality_indicator → qualityIndicator
```

### Boolean Fields
```
is_active → isActive
is_ecg_mode → isEcgMode
can_edit → canEdit
```

### Status & Type Fields
```
entry_type → entryType
alert_type → alertType
assignment_reason → assignmentReason
unassignment_reason → unassignmentReason
verification_status → verificationStatus
```

### Medical Records
```
allergen_type → allergenType
case_sheet → caseSheet
handoff_notes → handoffNotes
patient_response → patientResponse
```

### API & Config Fields
```
access_token → accessToken
refresh_token → refreshToken
api_key → apiKey
nfc_id → nfcId
app_session_id → appSessionId
```

## Table Renames (if needed)
```
patient_investigations → patientInvestigations
patient_therapies → patientTherapies
therapy_sessions → therapySessions
vital_history → vitalHistory
vital_readings → vitalReadings
device_alerts_ts → deviceAlertsTs
device_status_log → deviceStatusLog
device_assignments → deviceAssignments
```