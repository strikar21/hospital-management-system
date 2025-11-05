# Calibration Pulse Analysis - Where Does It Come From?

**Question:** Does the calibration pulse come from the ESP32 watch or is it software-generated for display only?

**Answer:** **Software-generated for display only** (Frontend)

---

## Summary

The 1mV calibration pulse you see on ECG displays is **100% software-generated** by the frontend React application. The ESP32 watch **does NOT send** calibration pulses - it only sends physiological waveform data from the simulator.

---

## Evidence from Code

### 1. Frontend Generates Calibration Pulse

**File:** [hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx:38-72](hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx#L38-L72)

```typescript
// Initialize buffers and calibration pulse
useEffect(() => {
  if (isECGMode && !hasPulseAdded.current.every(Boolean)) {
    const samplesPerSecond = 500;
    const pulseDuration = 0.2; // 200ms pulse
    const totalPulseSamples = Math.floor(samplesPerSecond * pulseDuration); // 100 samples
    const pulseADC = 8388608 + (1 * 100000); // ✅ 1mV in ADC units (frontend calculation)
    const calibrationPulse = new Array(totalPulseSamples).fill(pulseADC);
    const spacerSamples = new Array(100).fill(8388608); // 0.2s baseline

    console.log(`Adding calibration pulse: ${totalPulseSamples} samples`);
    const timeout = setTimeout(() => {
      leads.forEach((_, index) => {
        if (!hasPulseAdded.current[index]) {
          dataBufferRef.current[index] = [...spacerSamples, ...calibrationPulse];
          hasPulseAdded.current[index] = true;
        }
      });
    }, 500);
    return () => clearTimeout(timeout);
  }
}, [isECGMode, leads, dataBufferRef, patient.id]);
```

**What this does:**
- When ECG viewer opens, frontend **creates fake ADC samples** representing 1mV
- Calculation: `8388608 + (1 * 100000)` = 1mV pulse in 24-bit ADC units
- Inserts this into the data buffer **before real data arrives** from watch
- Each lead gets the same calibration pulse added once

### 2. Utility Functions for Calibration Pulse Rendering

**File:** [hospital-display-app/src/utils/medicalWaveformUtils.ts:253-280](hospital-display-app/src/utils/medicalWaveformUtils.ts#L253-L280)

```typescript
/**
 * Generate calibration pulse for ECG (1mV step)
 * Used to verify scale accuracy
 */
export function generateECGCalibrationPulse(
  viewportWidth: number,
  viewportHeight: number
): string {
  const baseline = viewportHeight / 2;
  const mvRange = 4;
  const pixelsPerMV = viewportHeight / mvRange;

  // 1mV pulse: 0mV → 1mV → 0mV
  const pulseHeight = 1 * pixelsPerMV; // 1mV
  const pulseWidth = viewportWidth * 0.1; // 10% of width

  return `
    M 0 ${baseline}
    L ${pulseWidth * 0.3} ${baseline}
    L ${pulseWidth * 0.3} ${baseline - pulseHeight}
    L ${pulseWidth * 0.7} ${baseline - pulseHeight}
    L ${pulseWidth * 0.7} ${baseline}
    L ${viewportWidth} ${baseline}
  `.trim().replace(/\s+/g, ' ');
}
```

**Also:** Canvas-based calibration pulse drawing function at lines 474-513

### 3. ESP32 Does NOT Generate Calibration Pulses

**File:** [esp32_hospital_watch_complete/PhysiologicalSimulator.h](esp32_hospital_watch_complete/PhysiologicalSimulator.h)

**Evidence:**
- ❌ No `generateCalibrationPulse()` method
- ❌ No calibration pulse in `generateECGSample()` method
- ❌ No mention of calibration in the entire simulator code
- ✅ Only generates realistic PQRST cardiac waveforms

**File:** [esp32_hospital_watch_complete/PhysiologicalSimulator.cpp](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp)

- Searched for "calibration", "1mV", "calib" → **No matches found**
- ESP32 only generates physiological ECG/EEG waveforms using sine/cosine synthesis

### 4. ESP32 Calibration Command (Different Purpose)

**File:** [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino:901-920](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L901-L920)

```cpp
void handleCalibrationCommand(String commandId) {
  // Perform device self-calibration (NOT the 1mV pulse!)
  // This recalibrates sensors, ADC offsets, etc.

  calibrationDue = false;
  sendCommandAck(commandId, true, "Calibration complete");
}
```

**This is device calibration** (hardware self-test), **NOT the 1mV calibration pulse** shown on displays!

---

## Why Software-Generated?

### Medical Standards Context

In **real ECG machines**, the calibration pulse serves two purposes:

1. **Verify paper/display scale:** Proves 10mm = 1mV is accurate
2. **Printer alignment:** Ensures chart recorder is working properly

### In Our System

Since our display is **digital** (not paper), the calibration pulse is:

✅ **Display verification only** - Shows that the frontend is rendering at correct scale (10mm/mV)
✅ **Frontend-generated** - No need to waste ESP32 resources or network bandwidth
✅ **Non-clinical** - It's not actual patient data, just a visual reference marker

**Real clinical data** (PQRST waves) comes from ESP32 → MQTT → Backend → WebSocket → Frontend.

---

## Data Flow Comparison

### Calibration Pulse Flow:
```
Frontend (ECGViewerContainer.tsx)
  ↓
Creates fake ADC samples (1mV = ADC 8488608)
  ↓
Inserts into local buffer (dataBufferRef)
  ↓
Rendered on canvas
```

### Real ECG Data Flow:
```
ESP32 PhysiologicalSimulator
  ↓
Generates PQRST waveform samples (ADC values)
  ↓
MQTT publish to backend
  ↓
Backend WebSocket broadcast
  ↓
Frontend receives and appends to buffer
  ↓
Rendered on canvas
```

**Calibration pulse never touches the network!**

---

## Do Other Devices Generate Calibration Pulses?

### Real Hospital ECG Machines

**Yes** - Traditional ECG machines (GE, Philips, Nihon Kohden, etc.) **do generate** calibration pulses:

1. **Startup pulse:** 1mV square wave at the start of each strip
2. **Paper chart:** Printed on physical ECG paper
3. **Hardware-generated:** Built into the ECG amplifier/printer electronics
4. **Purpose:** Verify scale accuracy before interpretation

**Example:** When doctor sees ECG printout, they look for the calibration pulse to confirm 10mm = 1mV before measuring QRS amplitude.

### Modern Digital ICU Monitors

**No** - Modern bedside monitors (Philips IntelliVue, GE Dinamap, etc.) typically **do NOT show** calibration pulses on the live display:

- Real-time waveforms only
- Software-rendered grid with known pixel density
- Scale is verified in software/firmware (no need for visual calibration)
- **Optional:** Some devices show calibration pulse during self-test mode only

### Our System Design Choice

We follow **modern ICU monitor approach**:
- Calibration pulse shown **only when viewer opens** (verification)
- Helps staff verify display is rendering correctly
- Not shown continuously (would waste screen space)
- Not from hardware (no need - digital display has precise scaling)

---

## Technical Details

### ADC Encoding

**ESP32 sends 24-bit ADC values:**
- Midpoint: `8388608` (2^23) = 0mV
- Scale: `100000` ADC units per mV (ECG)
- Example: 1mV = `8388608 + 100000` = `8488608`

**Frontend calibration pulse:**
```typescript
const pulseADC = 8388608 + (1 * 100000); // = 8488608
const calibrationPulse = new Array(100).fill(pulseADC); // 100 samples = 200ms at 500Hz
```

**Rendered height:**
- 1mV × (canvas_height / 4mV_range) = 25% of canvas height
- On 200px tall canvas: 1mV = 50 pixels tall
- Matches medical standard: 10mm = 1mV (assuming ~96 DPI screen)

---

## Summary Table

| Aspect | ESP32 Watch | Frontend |
|--------|-------------|----------|
| **Generates calibration pulse?** | ❌ No | ✅ Yes |
| **Generates ECG waveforms?** | ✅ Yes (PQRST) | ❌ No (displays only) |
| **Calibration command?** | ✅ Yes (hardware self-test) | ❌ No |
| **Sends 1mV pulse over network?** | ❌ No | N/A |
| **Purpose of calibration pulse** | N/A | Display scale verification |

---

## Conclusion

**The 1mV calibration pulse is 100% software-generated by the frontend React application.**

- ESP32 watch: Only sends real physiological ECG/EEG data
- Frontend: Creates fake 1mV pulse and inserts it into buffer when viewer opens
- Purpose: Visual verification that display is rendering at correct medical scale (10mm/mV)
- This matches modern digital ICU monitor behavior (not traditional paper ECG machines)

**Reference Files:**
- Calibration pulse generation: [ECGViewerContainer.tsx:51-68](hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx#L51-L68)
- Rendering utilities: [medicalWaveformUtils.ts:253-513](hospital-display-app/src/utils/medicalWaveformUtils.ts#L253-L513)
- ESP32 simulator (NO calibration): [PhysiologicalSimulator.h](esp32_hospital_watch_complete/PhysiologicalSimulator.h)
