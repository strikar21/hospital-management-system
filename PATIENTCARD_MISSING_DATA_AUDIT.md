# PatientCard Missing Data Audit Report

**Date:** 2025-11-06
**Component:** PatientCard (PatientCardContainer and child components)
**Audit Scope:** Comparison of available patient data fields vs. displayed data

---

## Executive Summary

This audit identifies **critical medical data** available in the patient data structure but **NOT currently displayed** on the PatientCard component. The PatientCard shows basic vitals and alerts but omits several clinically important data points that could improve patient safety and care quality.

**Key Finding:** The PatientCard is missing display of several critical patient safety fields including allergies, code status, active problems, medication schedules, ECG/EEG analysis metrics, and enhanced patient safety information.

---

## Section 1: Available Patient Data Fields (from PatientTypes.ts)

### 1.1 Basic Patient Information
- ✅ **Currently Available:**
  - `id` - Patient ID
  - `mrn` - Medical Record Number
  - `name`, `firstName`, `lastName`
  - `age`, `gender`, `weight`
  - `bedNumber`, `roomNumber`, `ward`, `room`, `department`
  - `assignedDoctor`, `attendingPhysician`, `nurseInCharge`
  - `diagnosis`
  - `status` - Patient status
  - `dischargeStatus`
  - `admissionDate`

### 1.2 Device Information
- ✅ **Currently Available:**
  - `assignedDeviceId`
  - `deviceStatus` - connection status
  - `deviceBatteryLevel`
  - `deviceLastSeen`
  - `deviceSerialNumber`
  - `deviceName`, `deviceModel`, `deviceManufacturer`
  - `deviceMacAddress`
  - `deviceFirmwareVersion`
  - `deviceLocation`
  - `deviceAssignedAt`, `deviceAssignedBy`
  - `deviceCalibrationDate`
  - `deviceNextMaintenanceDate`

### 1.3 Vital Signs (Primary)
- ✅ **Currently Available:**
  - `heartRate` - BPM
  - `systolicPressure`, `diastolicPressure` - mmHg
  - `respiratoryRate` - breaths/min
  - `oxygenSaturation` - percentage
  - `skinTemperature` - Fahrenheit
  - `ecgReading`, `eegReading`
  - `isEcgMode` - ECG/EEG mode flag

### 1.4 Advanced Monitoring Vitals
- ✅ **Currently Available:**
  - `bioimpedance` - 20-50Ω thoracic impedance
  - `tremor` - 0-10 scale
  - `imuFallRisk` - 0-10 numeric fall risk
  - `perfusionIndex` - 0-20% perfusion index
  - `stepCount`
  - `watchWorn` - Watch worn status
  - `lastMovementTime`

### 1.5 ECG Analysis Data (Nested Object)
- ✅ **Currently Available:**
  - `vitals.ecg.rrInterval` - RR interval in ms
  - `vitals.ecg.qrsDuration` - QRS duration in ms
  - `vitals.ecg.qtInterval` - QT interval in ms
  - `vitals.ecg.axis` - Heart axis in degrees
  - `vitals.ecg.rhythm` - Detected rhythm (sinus, afib, etc.)
  - `vitals.ecg.stSegment` - ST segment analysis (normal/elevated/depressed)

### 1.6 EEG Analysis Data (Nested Object)
- ✅ **Currently Available:**
  - `vitals.eeg.alphaPower` - Alpha band (8-13 Hz)
  - `vitals.eeg.betaPower` - Beta band (13-30 Hz)
  - `vitals.eeg.thetaPower` - Theta band (4-8 Hz)
  - `vitals.eeg.deltaPower` - Delta band (0.5-4 Hz)
  - `vitals.eeg.gammaPower` - Gamma band (30-100 Hz)
  - `vitals.eeg.dominantFrequency` - Dominant frequency in Hz
  - `vitals.eeg.seizureActivity` - Seizure detection flag

### 1.7 Patient Safety Fields
- ✅ **Currently Available:**
  - `allergies` - Array of allergy objects
  - `codeStatus` - fullcode/dnr/dnrcca/comfortcare
  - `activeProblems` - Array of active problems
  - `lastMedicationTime`
  - `nextMedicationDue`

### 1.8 Medical Records
- ✅ **Currently Available:**
  - `alerts` - Array of alert objects
  - `medications` - Array of medication objects
  - `investigations` - Array of investigation objects
  - `therapies` - Array of therapy objects
  - `notes` - Array of note/comment objects
  - `caseSheet` - Array of case sheet entries
  - `handoffNotes` - Array of handoff note objects

### 1.9 Vital Metadata
- ✅ **Currently Available:**
  - `vitals.lastDataReceived` - Last data timestamp
  - `vitals.dataQualityScore` - 0-1 scale for data quality

---

## Section 2: Currently Displayed Data on PatientCard

### 2.1 PatientCardHeader Component
**Currently Shows:**
- ✅ Patient name (`patient.name`)
- ✅ Age and gender (`patient.age`, `patient.gender`)
- ✅ Department (`patient.department`)
- ✅ Patient status (`patient.status`) - color-coded badge
- ✅ Bed number and ward (`patient.bedNumber`, `patient.ward`)
- ✅ Last data received timestamp (`patient.vitals.lastDataReceived`)
- ✅ Watch connection status indicator (icon + color)
- ✅ Top 2 inline alerts with acknowledge button
- ✅ Bedside mode button

### 2.2 PatientCardAlerts Component
**Currently Shows:**
- ✅ Alert banner with severity color (red/orange/yellow/green)
- ✅ Total unacknowledged alerts count
- ✅ Alert status text ("ALERTS PRESENT" or "ALL NORMAL")

### 2.3 PatientVitalStrip Component
**Currently Shows:**
- ✅ Heart Rate (HR) - BPM
- ✅ Oxygen Saturation (SpO2) - %
- ✅ Skin Temperature (Temp) - °F
- ✅ Blood Pressure (BP) - systolic/diastolic mmHg
- ✅ Respiratory Rate (RR) - /min
- ✅ Bioimpedance (BioZ) - Ω
- ✅ Tremor - /10 scale
- ✅ Fall Risk - /10 scale
- ✅ Perfusion Index - %
- ✅ Step Count
- ✅ Watch Worn Status (ON/OFF)
- ✅ ECG/EEG toggle display

### 2.4 PatientCardWaveform Component
**Currently Shows:**
- ✅ Real-time ECG/EEG waveform visualization
- ✅ Current ECG/EEG reading value
- ✅ Sweep speed indicator (25mm/s)
- ✅ Heart rate display (BPM)
- ✅ ECG/EEG mode toggle button
- ✅ Arrhythmia/seizure activity warnings

### 2.5 WatchDetailsModal (Separate Modal)
**Currently Shows (when clicked):**
- ✅ Device ID (`assignedDeviceId`)
- ✅ Patient location (room, bed, department, ward)
- ✅ Connection status with time since last seen
- ✅ Battery level with visual indicator
- ✅ Last seen timestamp
- ✅ Serial number, device name, MAC address
- ✅ Firmware version, model, manufacturer
- ✅ Device location, assigned date
- ✅ Calibration date, next maintenance date

---

## Section 3: Missing/Unused Data - HIGH PRIORITY

### 3.1 CRITICAL PATIENT SAFETY DATA (NOT DISPLAYED)

#### **🚨 Allergies** - CRITICAL MISSING
- **Field:** `patient.allergies` (array of allergy objects)
- **Current Status:** ❌ NOT displayed anywhere on PatientCard
- **Clinical Impact:** HIGH RISK - Allergies are critical for medication safety
- **Recommendation:** Display allergy count/indicator on PatientCard header
  - Show allergy icon/badge if `allergies.length > 0`
  - Click to view full allergy list
  - Color-coded: Red for severe allergies, yellow for mild

#### **🚨 Code Status** - CRITICAL MISSING
- **Field:** `patient.codeStatus` (fullcode/dnr/dnrcca/comfortcare)
- **Current Status:** ❌ NOT displayed anywhere on PatientCard
- **Clinical Impact:** HIGH RISK - Code status is essential for emergency response
- **Recommendation:** Display code status badge on PatientCard header
  - Use clear abbreviations: "FC" (Full Code), "DNR", "DNR/CCA", "Comfort"
  - Color-coded: Green for full code, purple for DNR, blue for comfort care

#### **⚠️ Active Problems** - HIGH PRIORITY MISSING
- **Field:** `patient.activeProblems` (array of strings)
- **Current Status:** ❌ NOT displayed on PatientCard
- **Clinical Impact:** MEDIUM - Active problems guide clinical decision-making
- **Recommendation:** Show active problem count on PatientCard
  - Display as badge/indicator: "3 Active Problems"
  - Click to view full list in modal or patient detail

#### **⚠️ Medication Schedule** - HIGH PRIORITY MISSING
- **Fields:** `patient.lastMedicationTime`, `patient.nextMedicationDue`
- **Current Status:** ❌ NOT displayed on PatientCard
- **Clinical Impact:** MEDIUM - Important for medication adherence monitoring
- **Recommendation:** Display next medication due time
  - Show countdown timer if medication is due soon (< 30 mins)
  - Color-coded: Red if overdue, yellow if due soon, green if on schedule
  - Example: "Next Med: 14:30" or "Med Due in 15m"

### 3.2 IMPORTANT ECG/EEG ANALYSIS DATA (NOT DISPLAYED)

#### **ECG Advanced Metrics** - MEDIUM PRIORITY MISSING
- **Fields:**
  - `vitals.ecg.rrInterval` - RR interval (ms)
  - `vitals.ecg.qrsDuration` - QRS duration (ms)
  - `vitals.ecg.qtInterval` - QT interval (ms)
  - `vitals.ecg.axis` - Heart axis (degrees)
  - `vitals.ecg.rhythm` - Detected rhythm
  - `vitals.ecg.stSegment` - ST segment analysis
- **Current Status:** ❌ NOT displayed on PatientCard
- **Clinical Impact:** MEDIUM - Important for arrhythmia detection and cardiac monitoring
- **Recommendation:** Add ECG metrics tooltip/overlay on waveform hover
  - Show key metrics when hovering over ECG waveform area
  - Display rhythm type prominently if abnormal (e.g., "A-Fib", "VT")
  - Highlight ST segment changes with color coding

#### **EEG Band Powers** - MEDIUM PRIORITY MISSING
- **Fields:**
  - `vitals.eeg.alphaPower`, `betaPower`, `thetaPower`, `deltaPower`, `gammaPower`
  - `vitals.eeg.dominantFrequency`
  - `vitals.eeg.seizureActivity`
- **Current Status:** ❌ NOT displayed on PatientCard
- **Clinical Impact:** MEDIUM - Important for neurological monitoring
- **Recommendation:** Add EEG band power visualization
  - Show mini bar chart of band powers when in EEG mode
  - Display dominant frequency next to EEG reading
  - Seizure activity is likely shown via backend alerts (verify)

### 3.3 USEFUL PATIENT IDENTIFICATION DATA (NOT DISPLAYED)

#### **Medical Record Number (MRN)** - LOW PRIORITY MISSING
- **Field:** `patient.mrn`
- **Current Status:** ❌ NOT displayed on PatientCard
- **Clinical Impact:** LOW - Useful for patient identification but not critical for monitoring
- **Recommendation:** Add MRN to PatientCardHeader (small text)
  - Display below patient name: "MRN: 12345678"
  - Low contrast to avoid visual clutter

#### **Attending Physician Name** - LOW PRIORITY MISSING
- **Fields:** `patient.attendingPhysician`, `patient.attendingPhysicianName`, `patient.assignedDoctor`
- **Current Status:** ❌ NOT displayed on PatientCard
- **Clinical Impact:** LOW - Useful for care coordination but not critical for monitoring
- **Recommendation:** Add physician name to PatientCardHeader tooltip
  - Show on hover: "Attending: Dr. Smith"

#### **Diagnosis** - MEDIUM PRIORITY MISSING
- **Field:** `patient.diagnosis`
- **Current Status:** ❌ NOT displayed on PatientCard
- **Clinical Impact:** MEDIUM - Important context for vital sign interpretation
- **Recommendation:** Add diagnosis as tooltip on patient name
  - Show on hover: truncated diagnosis text
  - Full diagnosis visible in patient detail view

### 3.4 DATA QUALITY INDICATOR (NOT DISPLAYED)

#### **Data Quality Score** - LOW PRIORITY MISSING
- **Field:** `vitals.dataQualityScore` (0-1 scale)
- **Current Status:** ❌ NOT displayed on PatientCard
- **Clinical Impact:** LOW - Useful for troubleshooting data issues
- **Recommendation:** Add subtle data quality indicator
  - Show icon/color when data quality is poor (< 0.7)
  - Tooltip explains data quality issues
  - Example: Yellow warning icon with "Data Quality: Fair"

### 3.5 DEVICE METADATA (PARTIALLY DISPLAYED)

#### **Device Assigned By** - LOW PRIORITY MISSING
- **Field:** `patient.deviceAssignedBy`
- **Current Status:** ❌ NOT displayed (even in WatchDetailsModal)
- **Clinical Impact:** LOW - Audit trail information
- **Recommendation:** Add to WatchDetailsModal
  - Show in device details: "Assigned by: Nurse Smith"

---

## Section 4: Data Already Well-Displayed

### 4.1 Well-Implemented Features
The following data is already displayed effectively:

✅ **Basic Patient Info:** Name, age, gender, location (bed/room/ward)
✅ **Patient Status:** Color-coded status badge (stable/critical/emergency)
✅ **All Primary Vitals:** HR, SpO2, Temp, BP, RR with alert status indicators
✅ **Advanced Vitals:** Bioimpedance, tremor, fall risk, perfusion, step count
✅ **Watch Device Status:** Connection, battery, last seen (via modal)
✅ **Device Technical Details:** Serial number, MAC, firmware, calibration dates
✅ **Real-time Waveforms:** ECG/EEG visualization with mode toggle
✅ **Alerts:** Count, severity, inline display with acknowledgment
✅ **Vital Status Indicators:** Color-coded vitals with alert highlighting

---

## Section 5: Recommended Additions - Prioritized

### Priority 1: CRITICAL (Must Add)
1. **Allergy Indicator**
   - Add allergy badge/icon to PatientCardHeader
   - Red/yellow color coding based on severity
   - Click to view full allergy list

2. **Code Status Badge**
   - Display code status (FC/DNR/etc.) on PatientCardHeader
   - Color-coded badge for quick recognition
   - Essential for emergency response

### Priority 2: HIGH (Should Add)
3. **Active Problems Count**
   - Show "X Active Problems" badge
   - Click for full list

4. **Medication Schedule**
   - Display "Next Med: HH:MM" or countdown
   - Color-coded if overdue or due soon

5. **Medical Record Number (MRN)**
   - Small text below patient name
   - Helps with patient identification

### Priority 3: MEDIUM (Nice to Have)
6. **ECG Advanced Metrics**
   - Tooltip overlay on ECG waveform hover
   - Show RR interval, QRS, QT, rhythm, ST segment

7. **Diagnosis Display**
   - Tooltip on patient name hover
   - Provides clinical context

8. **Data Quality Indicator**
   - Subtle warning when data quality is poor
   - Helps troubleshoot connectivity issues

### Priority 4: LOW (Future Enhancement)
9. **EEG Band Powers**
   - Mini bar chart when in EEG mode
   - Show dominant frequency

10. **Device Assigned By**
    - Add to WatchDetailsModal
    - Audit trail information

---

## Section 6: Implementation Recommendations

### 6.1 Layout Suggestions

**PatientCardHeader Enhancement:**
```
[Patient Name] [Allergy Icon] [Code Status Badge] [Watch Status]
[Age, Gender] | MRN: 12345 | Next Med: 14:30 ⏰
[Department] | 3 Active Problems 🔴
```

**Example Visual Layout:**
```
┌─────────────────────────────────────────────────────┐
│ 🚨 ALERTS PRESENT                              [2]  │
├─────────────────────────────────────────────────────┤
│ John Doe 🔴⚠️ [DNR] 🟢●                [👁️] [STABLE]│
│ 65y, Male | MRN: PAT0012 | Next Med: 14:30       │
│ Cardiology | 2 Allergies | 3 Active Problems     │
│ Bed 5 • Ward A           Updated: 2:45 PM        │
├─────────────────────────────────────────────────────┤
│ [Vital Signs Strip - scrolling]                    │
├─────────────────────────────────────────────────────┤
│ [ECG/EEG Waveform Display]                         │
│ 💭 Hover for ECG metrics (RR, QRS, QT, Rhythm)    │
└─────────────────────────────────────────────────────┘
```

### 6.2 Color Coding Standards

**Allergy Indicators:**
- 🔴 Red circle: Severe/life-threatening allergies
- 🟡 Yellow circle: Moderate allergies
- ⚪ Gray circle: Mild allergies

**Code Status Badges:**
- 🟢 Green: Full Code (FC)
- 🟣 Purple: DNR
- 🔵 Blue: DNR/CCA or Comfort Care

**Medication Alerts:**
- 🔴 Red: Medication overdue (> 30 mins late)
- 🟡 Yellow: Medication due soon (< 15 mins)
- 🟢 Green: On schedule

### 6.3 Space Optimization

The PatientCard is currently **330px height** with:
- Alert banner: ~24px
- Header: 90px
- Vital strip: 80px
- Waveform: 85px
- Padding/spacing: ~51px

**Recommendation:** Add additional patient safety info to header without increasing height:
- Use multi-line header (already 90px tall - plenty of space)
- Add small badges/icons for allergies, code status, active problems
- Use tooltips for detailed information to avoid clutter

---

## Section 7: Conclusion

The PatientCard component displays vitals and device status comprehensively, but **omits several critical patient safety data fields** that are available in the patient data structure:

**CRITICAL MISSING DATA:**
1. Allergies (🚨 HIGH RISK)
2. Code Status (🚨 HIGH RISK)
3. Active Problems (⚠️ MEDIUM RISK)
4. Medication Schedule (⚠️ MEDIUM RISK)

**IMPORTANT MISSING DATA:**
5. Medical Record Number (MRN)
6. ECG/EEG advanced analysis metrics
7. Diagnosis display
8. Data quality indicators

**Recommendation:** Prioritize adding allergy indicators and code status badges to the PatientCardHeader as these are critical for patient safety and emergency response. Other enhancements can be phased in based on clinical feedback.

---

## Appendix: Data Fields Complete Inventory

### Available but NOT Displayed:
```typescript
// CRITICAL PATIENT SAFETY
patient.allergies              // Array of allergy objects
patient.codeStatus             // fullcode/dnr/dnrcca/comfortcare
patient.activeProblems         // Array of active problems
patient.lastMedicationTime     // Last medication timestamp
patient.nextMedicationDue      // Next medication due time

// PATIENT IDENTIFICATION
patient.mrn                    // Medical Record Number
patient.firstName              // First name (only full name shown)
patient.lastName               // Last name (only full name shown)
patient.attendingPhysicianName // Attending physician name

// ECG ANALYSIS
patient.vitals.ecg.rrInterval      // RR interval in ms
patient.vitals.ecg.qrsDuration     // QRS duration in ms
patient.vitals.ecg.qtInterval      // QT interval in ms
patient.vitals.ecg.axis            // Heart axis in degrees
patient.vitals.ecg.rhythm          // Detected rhythm
patient.vitals.ecg.stSegment       // ST segment analysis

// EEG ANALYSIS
patient.vitals.eeg.alphaPower      // Alpha band power
patient.vitals.eeg.betaPower       // Beta band power
patient.vitals.eeg.thetaPower      // Theta band power
patient.vitals.eeg.deltaPower      // Delta band power
patient.vitals.eeg.gammaPower      // Gamma band power
patient.vitals.eeg.dominantFrequency // Dominant frequency
patient.vitals.eeg.seizureActivity // Seizure detection

// MONITORING METADATA
patient.vitals.dataQualityScore    // 0-1 data quality score
patient.vitals.lastMovementTime    // Last movement timestamp

// MEDICAL RECORDS (Arrays - not displayed on card, shown in detail view)
patient.medications            // Array of medications
patient.investigations         // Array of investigations
patient.therapies             // Array of therapies
patient.notes                 // Array of notes
patient.caseSheet             // Array of case sheet entries
patient.handoffNotes          // Array of handoff notes

// DEVICE AUDIT TRAIL
patient.deviceAssignedBy      // Who assigned the device
patient.roomNumber            // Room number (duplicate of room field)
patient.room                  // Room (duplicate of roomNumber field)
patient.diagnosis             // Patient diagnosis
patient.weight                // Patient weight in kg
patient.nurseInCharge         // Nurse in charge
patient.dischargeStatus       // Discharge status
patient.admissionDate         // Admission date
```

### Available and Currently Displayed:
```typescript
// DISPLAYED ON PATIENTCARD
patient.name                   // ✅ PatientCardHeader
patient.age                    // ✅ PatientCardHeader
patient.gender                 // ✅ PatientCardHeader
patient.department             // ✅ PatientCardHeader
patient.status                 // ✅ PatientCardHeader (badge)
patient.bedNumber              // ✅ PatientCardHeader
patient.ward                   // ✅ PatientCardHeader
patient.assignedDeviceId       // ✅ PatientCardHeader (icon)
patient.deviceStatus           // ✅ PatientCardHeader (icon color)
patient.alerts                 // ✅ PatientCardAlerts (count + inline)
patient.vitals.lastDataReceived // ✅ PatientCardHeader (timestamp)

// ALL PRIMARY VITALS
patient.vitals.heartRate       // ✅ PatientVitalStrip
patient.vitals.oxygenSaturation // ✅ PatientVitalStrip
patient.vitals.skinTemperature // ✅ PatientVitalStrip
patient.vitals.systolicPressure // ✅ PatientVitalStrip
patient.vitals.diastolicPressure // ✅ PatientVitalStrip
patient.vitals.respiratoryRate // ✅ PatientVitalStrip
patient.vitals.bioimpedance    // ✅ PatientVitalStrip
patient.vitals.tremor          // ✅ PatientVitalStrip
patient.vitals.imuFallRisk     // ✅ PatientVitalStrip
patient.vitals.perfusionIndex  // ✅ PatientVitalStrip
patient.vitals.stepCount       // ✅ PatientVitalStrip
patient.vitals.watchWorn       // ✅ PatientVitalStrip
patient.vitals.ecgReading      // ✅ PatientCardWaveform
patient.vitals.eegReading      // ✅ PatientCardWaveform
patient.vitals.isEcgMode       // ✅ PatientCardWaveform (mode toggle)

// DEVICE DETAILS (in WatchDetailsModal)
patient.deviceBatteryLevel     // ✅ WatchDetailsModal
patient.deviceLastSeen         // ✅ WatchDetailsModal
patient.deviceSerialNumber     // ✅ WatchDetailsModal
patient.deviceName             // ✅ WatchDetailsModal
patient.deviceMacAddress       // ✅ WatchDetailsModal
patient.deviceFirmwareVersion  // ✅ WatchDetailsModal
patient.deviceModel            // ✅ WatchDetailsModal
patient.deviceManufacturer     // ✅ WatchDetailsModal
patient.deviceLocation         // ✅ WatchDetailsModal
patient.deviceAssignedAt       // ✅ WatchDetailsModal
patient.deviceCalibrationDate  // ✅ WatchDetailsModal
patient.deviceNextMaintenanceDate // ✅ WatchDetailsModal
```

---

**End of Audit Report**
