# Tremor and Bioimpedance - Research Findings

**Date:** 2025-11-06
**Status:** RESEARCH COMPLETE - Awaiting implementation decision

---

## Key Findings from Code Research

### 1. Current Architecture ✅

**Three Simulator Classes Exist:**

1. **PhysiologicalSimulator** (`PhysiologicalSimulator.h/cpp`)
   - **Purpose:** Overall patient state management (HR, temp, SpO2, BP, tremor, bioz, fall risk)
   - **Currently:** ✅ ACTIVELY USED by main firmware
   - **Has methods:**
     - `getTremorIntensity()` → Returns 0-10 scale (from lines 740-742)
     - `getBioimpedance()` → Returns 200-1000 Ω (from lines 736-738)
   - **Implementation:** Simple state-based generation (lines 170-203)
     - Tremor: 0.2-2.0 based on activity (RESTING=0.2, EXERCISE=2.0)
     - BioZ: 450-590 Ω based on activity (SLEEP=450, EXERCISE=590)

2. **BMI323Simulator** (`BMI323Simulator.h/cpp`)
   - **Purpose:** Bosch IMU simulator (accelerometer + gyroscope)
   - **Currently:** ❌ NOT USED (not included in main firmware)
   - **Hardware it simulates:** BMI323 6-axis IMU chip
   - **Has advanced methods:**
     - `getTremorIntensity()` → FFT-based 4-12 Hz tremor detection
     - `getFallRisk()` → 0-10 scale from fall detection state machine
     - `getStepCount()`, `detectDoubleTap()`, motion analysis
   - **Note:** More realistic tremor detection using accelerometer FFT analysis

3. **MAX86178Simulator** (`MAX86178Simulator.h/cpp`)
   - **Purpose:** Maxim PPG + BioZ AFE simulator
   - **Currently:** ❌ NOT USED (not included in main firmware)
   - **Hardware it simulates:** MAX86178 PPG chip with bioimpedance
   - **Has methods:**
     - `getBioimpedance()` → Returns 20-50 Ω (thoracic impedance for respiratory rate)
     - `getPerfusionIndex()` → Shock/sepsis detection
     - `getHeartRate()`, `getSpO2()`, `getRespiratoryRate()`
   - **Note:** More realistic bioimpedance from PPG chip simulation

---

## Current Data Sources

| Vital | Current Source | Notes |
|-------|----------------|-------|
| **Heart Rate** | PhysiologicalSimulator | Simple state-based |
| **SpO2** | PhysiologicalSimulator | Simple state-based |
| **Temperature** | PhysiologicalSimulator | Simple state-based |
| **Respiratory Rate** | PhysiologicalSimulator | Simple state-based |
| **Blood Pressure** | PhysiologicalSimulator | Simple state-based (just added v5.2.14) |
| **Tremor** | PhysiologicalSimulator | ❌ NOT transmitted (simple 0.2-2.0 generation) |
| **Bioimpedance** | PhysiologicalSimulator | ❌ NOT transmitted (simple 450-590 Ω generation) |
| **Fall Risk (IMU)** | PhysiologicalSimulator | ❌ NOT transmitted (simple 0.5-4.0 generation) |

**Hardware simulators BMI323 and MAX86178 exist but are NOT integrated!**

---

## User's Correct Understanding

You stated:
> "tremor and fall alert from watch. but fall risk comes from accelerometer + patient drug + other data."

**You are CORRECT:**

1. **Tremor:** Should come from BMI323 accelerometer (FFT analysis of 4-12 Hz vibrations)
   - Current: PhysiologicalSimulator (simple state-based 0.2-2.0)
   - Better: BMI323Simulator.getTremorIntensity() (FFT-based, realistic)

2. **Bioimpedance:** Should come from MAX86178 PPG chip
   - Current: PhysiologicalSimulator (simple state-based 450-590 Ω)
   - Correct: MAX86178Simulator.getBioimpedance() (thoracic impedance 20-50 Ω for respiratory monitoring)

3. **Fall Risk:** Complex calculation
   - **Watch-side (IMU):** BMI323Simulator.getFallRisk() → 0-10 scale from fall detection
   - **Backend-side:** Combine with:
     - Patient medications (sedatives, blood pressure meds increase risk)
     - Age (elderly = higher risk)
     - Medical history (stroke, Parkinson's, previous falls)
     - Mobility assessment scores
   - **Frontend:** Display combined fall risk with breakdown

---

## Architecture Decision Required

### Option A: Keep Simple (Current PhysiologicalSimulator) ✅ EASIER
**Pros:**
- Already works
- No additional complexity
- Fast implementation (10-15 minutes)
- Just read existing getTremorIntensity() and getBioimpedance()

**Cons:**
- Less realistic (state-based, not sensor-based)
- Tremor is simple 0.2-2.0 range (not FFT-based)
- BioZ is 450-590 Ω (should be 20-50 Ω thoracic impedance)

**Changes needed:**
1. ESP32 firmware: Read from simulator, transmit via MQTT (4 code changes)
2. Database: Add tremor and bioimpedance columns
3. Backend: Update INSERT query

---

### Option B: Integrate Hardware Simulators ⚠️ MORE REALISTIC
**Pros:**
- More realistic tremor detection (FFT-based from accelerometer)
- Correct bioimpedance range (20-50 Ω thoracic)
- Better fall detection (state machine: NORMAL → FREEFALL → IMPACT → LYING)
- Future-ready for actual hardware integration

**Cons:**
- Requires instantiating BMI323Simulator and MAX86178Simulator
- Need to call update() methods at correct frequencies (BMI323: 1600Hz, MAX86178: 100Hz)
- More complex timing management
- Longer implementation time (1-2 hours)

**Changes needed:**
1. ESP32 firmware: Include simulators, create instances, call update(), read values
2. Database: Add tremor, bioimpedance, fallRisk columns
3. Backend: Update INSERT query with 3 fields

---

## Bioimpedance Value Ranges - IMPORTANT DIFFERENCE

### PhysiologicalSimulator (Current):
- Range: **450-590 Ω**
- Represents: Whole-body bioimpedance (incorrect for respiratory monitoring)
- Used for: General hydration status

### MAX86178Simulator (Correct):
- Range: **20-50 Ω**
- Represents: **Thoracic impedance** (chest wall resistance)
- Used for: **Respiratory rate calculation** (impedance changes with breathing)
- Clinical use: Impedance cardiography, respiratory monitoring

**User is CORRECT:** BioZ should come from MAX86178 (PPG chip), not PhysiologicalSimulator!

---

## Fall Risk - Multi-Source Calculation

### Watch-Side (Real-time)
**Source:** BMI323 IMU accelerometer
- Freefall detection (< 0.5g for >500ms)
- Impact detection (> 3g sudden spike)
- Lying orientation (horizontal for >10 seconds)
- **Output:** fallState enum (NORMAL, FREEFALL, IMPACT, LYING)
- **Score:** 0-10 scale (0-3=low, 4-6=medium, 7-8=high, 9-10=CRITICAL fall detected)

### Backend-Side (Clinical Assessment)
**Additional Factors:**
- **Medications:** Sedatives, antihypertensives, opioids (+2-3 points)
- **Age:** >65 years (+1), >75 years (+2), >85 years (+3)
- **Medical conditions:** Stroke (+2), Parkinson's (+3), dementia (+2)
- **Previous falls:** Within 6 months (+2), multiple falls (+3)
- **Mobility:** Gait impairment (+2), requires assistive device (+1)
- **Environmental:** Low lighting (+1), wet floor (+1), stairs (+1)

**Combined Fall Risk Formula:**
```
Total Fall Risk = IMU Score (0-10) + Clinical Factors (0-15)
Final Score: 0-25 scale → Map to Low/Medium/High/Critical
```

---

## Recommended Implementation Path

### Phase 1: Quick Win (Use Existing PhysiologicalSimulator) ⏸️
**Time:** 15-20 minutes
**Complexity:** Low
**Steps:**
1. Add tremor/bioimpedance columns to database
2. ESP32: Read simulator.getTremorIntensity() and simulator.getBioimpedance()
3. ESP32: Transmit via MQTT
4. Backend: Update INSERT query
5. **Result:** Tremor and bioz data flowing (simple but working)

### Phase 2: Hardware Simulator Integration (Future Enhancement) ⏸️
**Time:** 1-2 hours
**Complexity:** Medium
**Steps:**
1. Integrate BMI323Simulator (tremor from FFT, fall detection)
2. Integrate MAX86178Simulator (correct thoracic bioimpedance 20-50 Ω)
3. Update timing loops (1600Hz for IMU, 100Hz for PPG)
4. **Result:** Realistic sensor-based tremor and bioimpedance

### Phase 3: Clinical Fall Risk Calculation (Backend) ⏸️
**Time:** 2-3 hours
**Complexity:** High
**Requirements:**
1. Patient medication database (drug-fall risk mapping)
2. Patient demographics (age, medical history)
3. Fall risk scoring algorithm
4. Alert generation rules
5. **Result:** Comprehensive fall risk assessment

---

## Database Schema Requirements

### Phase 1 (PhysiologicalSimulator):
```sql
ALTER TABLE vitals_realtime
ADD COLUMN tremor NUMERIC(4,2),           -- 0.00-10.00
ADD COLUMN bioimpedance NUMERIC(6,2);    -- 200.00-1000.00 Ω
```

### Phase 2 (Hardware Simulators):
```sql
ALTER TABLE vitals_realtime
ADD COLUMN tremor NUMERIC(4,2),           -- 0.00-10.00 (FFT-based from BMI323)
ADD COLUMN bioimpedance NUMERIC(5,2),    -- 20.00-50.00 Ω (thoracic from MAX86178)
ADD COLUMN "imuFallRisk" NUMERIC(4,2);   -- 0.00-10.00 (from BMI323 fall detection)
```

---

## Backend Pydantic Model - Already Ready! ✅

The backend **already supports all fields**:
```python
# File: hospital-backend/app/models/neural_vitals.py (lines 248-253)
class VitalsRealtimeMessage(BaseModel):
    bioimpedance: Optional[float] = Field(None, ge=200.0, le=1000.0)  # Phase 1 range
    tremor: Optional[float] = Field(None, ge=0.0, le=10.0)
    imuFallRisk: Optional[float] = Field(None, ge=0.0, le=10.0)
```

**Note:** Phase 2 would need to update bioimpedance range to `ge=20.0, le=50.0`

---

## Questions for User

1. **Which implementation path?**
   - [ ] Phase 1: Quick win with PhysiologicalSimulator (15 min)
   - [ ] Phase 2: Proper hardware simulators (1-2 hours)
   - [ ] Phase 1 now, Phase 2 later

2. **Bioimpedance range preference?**
   - [ ] Keep 450-590 Ω (whole-body, Phase 1)
   - [ ] Use 20-50 Ω (thoracic, Phase 2 - requires MAX86178 integration)

3. **Fall risk implementation?**
   - [ ] Phase 1: Simple IMU score from PhysiologicalSimulator (0.5-4.0)
   - [ ] Phase 2: Proper BMI323 fall detection (0-10 with state machine)
   - [ ] Phase 3: Clinical fall risk calculation on backend (medications, age, etc.)

4. **Priority order?**
   - Tremor monitoring (Parkinson's, seizure detection)
   - Bioimpedance monitoring (fluid retention, respiratory)
   - Fall risk assessment (elderly care, fall prevention)

---

## Summary

**Current State:**
- PhysiologicalSimulator generates tremor (0.2-2.0) and bioz (450-590 Ω)
- Hardware simulators (BMI323, MAX86178) exist but NOT integrated
- ESP32 firmware does NOT read or transmit tremor/bioz data
- Database does NOT have tremor/bioz columns
- Backend Pydantic model ALREADY supports all fields ✅

**User is Correct:**
- Tremor should ideally come from BMI323 (accelerometer FFT)
- Bioimpedance should come from MAX86178 (PPG chip, thoracic impedance)
- Fall risk is multi-factorial (IMU + medications + demographics)

**Recommendation:**
Start with Phase 1 (quick win using existing PhysiologicalSimulator), then plan Phase 2 (proper hardware integration) after verifying the data pipeline works end-to-end.

---

## Next Steps - Awaiting User Decision

Please confirm:
1. Which implementation path? (Phase 1, 2, or 1→2)
2. Any specific clinical use cases to prioritize?
3. Proceed with implementation after approval
