# EEG Generator Code Explanation & O1/O2 Diagnosis

**Date:** 2025-11-04
**Status:** Research Complete - Root Cause Found
**Author:** Claude Code Analysis

---

## 1. EEG Generator Code Explanation

### How EEG Generation Works

**Location:** [PhysiologicalSimulator.cpp:536-175](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L536-L175)

#### Timing Mechanism - YES, IT'S THE SAME 2MS TIMING AS ECG

```cpp
void PhysiologicalSimulator::generateEEGSample(int channel, int32_t& sample) {
    // Update phase trackers for each frequency band (500 Hz = 2ms per sample)
    float timeStep = 0.002;  // 2ms in seconds ← SAME AS ECG
    alphaPhase += 10.5 * timeStep;   // 10.5 Hz (alpha)
    betaPhase += 20.0 * timeStep;    // 20 Hz (beta)
    thetaPhase += 6.0 * timeStep;    // 6 Hz (theta)
    deltaPhase += 2.0 * timeStep;    // 2 Hz (delta)

    // Generate mixed waveform and convert to 24-bit ADC units
    sample = 8388608 + (int32_t)(amplitude * 1000);
}
```

**Key Points:**
- ✅ YES, EEG uses **2ms per sample** (500Hz) - SAME as ECG
- ✅ NO, timing does **NOT** advance per lead - it advances **PER SAMPLE** globally
- ✅ All 8 channels are generated in parallel with the same timestamp
- ✅ Phase trackers (alpha, beta, theta, delta) increment once per sample, not per channel

#### Sample Generation Flow

**Location:** [PhysiologicalSimulator.cpp:468-500](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L468-L500)

```cpp
void PhysiologicalSimulator::fillSampleBuffer(int32_t buffer[8][10]) {
    // Generate 10 samples for each of 8 leads/channels (20ms at 500 Hz)
    for (int i = 0; i < 10; i++) {
        if (currentMode == MODE_EEG) {
            // EEG: Generate samples for all channels
            for (int channel = 0; channel < 8; channel++) {
                generateEEGSample(channel, buffer[channel][i]);
            }
        }
    }
}
```

**Execution Order:**
1. Loop through 10 samples (i = 0 to 9)
2. For each sample, loop through 8 channels (channel = 0 to 7)
3. Generate one sample for each channel at the same time point
4. Move to next time point (2ms later)
5. Repeat

**Channel Mapping:**
- Channel 0 = Fp1 (frontal pole left)
- Channel 1 = Fp2 (frontal pole right)
- Channel 2 = F3 (frontal left)
- Channel 3 = F4 (frontal right)
- Channel 4 = C3 (central left)
- Channel 5 = C4 (central right)
- Channel 6 = O1 (occipital left) ← **GENERATING CORRECTLY**
- Channel 7 = O2 (occipital right) ← **GENERATING CORRECTLY**

#### EEG Waveform Characteristics

**Location:** [PhysiologicalSimulator.cpp:177-250](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L177-L250)

```cpp
float PhysiologicalSimulator::generateEEGWaveform(float phase, int channel) {
    // Mix frequency bands based on activity state
    float alpha = sin(2 * PI * alphaPhase) * 40.0;   // 40 μV (8-13 Hz)
    float beta = sin(2 * PI * betaPhase) * 15.0;     // 15 μV (13-30 Hz)
    float theta = sin(2 * PI * thetaPhase) * 50.0;   // 50 μV (4-8 Hz)
    float delta = sin(2 * PI * deltaPhase) * 80.0;   // 80 μV (0.5-4 Hz)

    // Channel-specific variations
    switch (channel) {
        case 6:  // O1 - Occipital left (highest alpha)
            channelMultiplier = 1.15;  // Strong alpha waves
            break;
        case 7:  // O2 - Occipital right
            channelMultiplier = 1.15;  // Similar to O1
            break;
    }
}
```

**O1/O2 Special Features:**
- ✅ O1 and O2 have **15% stronger alpha waves** (channelMultiplier = 1.15)
- ✅ This is anatomically correct (visual cortex produces strongest alpha)
- ✅ Code is generating O1/O2 data correctly with proper amplitudes

---

## 2. O1/O2 Data Flow - Complete Path Analysis

### ESP32 Generation (✅ WORKING)

**Location:** [esp32_hospital_watch_complete.ino:2058-2061](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L2058-L2061)

```cpp
// Occipital channels (O1, O2)
JsonObject occipital = eegWaveform.createNestedObject("occipital");
addDeltaEncodedChannel(occipital, "O1", waveformAccumulator[6], 50);  // ← CH6 = O1
addDeltaEncodedChannel(occipital, "O2", waveformAccumulator[7], 50);  // ← CH7 = O2
```

**Verification from ESP32 Serial Logs:**
```
Mode=EEG, HR=89, Temp=37.1°C
Waveform stream: EEG (seq: 210, size: 2961 bytes)
```

✅ **ESP32 is generating and transmitting O1/O2 data**

### Backend Processing (✅ WORKING)

**From Backend Logs:**
```
[DEBUG] MQTT received: waveform/stream/c51d867e-8ecf-477d-bb6d-1a5ddc5aa84f
[WS_DEBUG] Broadcasting waveformStream to 1 clients
[WS_DEBUG] Broadcasting to room: watch_c51d867e
[WS_DEBUG] Message sent to sid=ZdLgQM52XiEm_NaxAAAF
```

✅ **Backend is receiving and broadcasting EEG waveforms with O1/O2**

### Frontend Reception (⚠️ ISSUE FOUND)

**Location:** [useECGViewer.ts:112-118](hospital-display-app/src/hooks/useECGViewer.ts#L112-L118)

```typescript
// 🔍 DIAGNOSTIC: Log EEG structure when in EEG mode
if (waveformData.mode === 'eeg' && waveformData.eegWaveform) {
  console.log(`📦 [EEG DEBUG] Seq ${waveformData.sequence}:`, {
    frontal: waveformData.eegWaveform.frontal ? Object.keys(waveformData.eegWaveform.frontal) : null,
    central: waveformData.eegWaveform.central ? Object.keys(waveformData.eegWaveform.central) : null,
    temporal: waveformData.eegWaveform.temporal ? Object.keys(waveformData.eegWaveform.temporal) : null,
    occipital: waveformData.eegWaveform.occipital ? Object.keys(waveformData.eegWaveform.occipital) : null
  });
}
```

**Frontend Console Logs:**
```
📦 [EEG DEBUG] Seq 252: {frontal: Array(4), central: Array(2), temporal: null, occipital: Array(2)}
```

✅ **Frontend IS receiving occipital data** - shows `Array(2)` which means O1 and O2 are present!

### Frontend Buffer Assignment (⚠️ POTENTIAL ISSUE)

**Location:** [useECGViewer.ts:298-305](hospital-display-app/src/hooks/useECGViewer.ts#L298-L305)

```typescript
// Occipital channels (O1, O2) - OPTIONAL
// ✅ v5.2.5: O1, O2 (proper capitalization)
if (occipital?.O1) {
  const samples = getData(occipital.O1);
  dataBufferRef.current[20] = [...dataBufferRef.current[20], ...samples].slice(-maxBufferSize);
}
if (occipital?.O2) {
  const samples = getData(occipital.O2);
  dataBufferRef.current[21] = [...dataBufferRef.current[21], ...samples].slice(-maxBufferSize);
}
```

**Buffer Index Mapping:**
- Fp1 → buffer[12]
- Fp2 → buffer[13]
- F3 → buffer[14]
- F4 → buffer[15]
- C3 → buffer[16]
- C4 → buffer[17]
- T3 → buffer[18] (optional, currently null)
- T4 → buffer[19] (optional, currently null)
- O1 → buffer[20] ← **Target buffer**
- O2 → buffer[21] ← **Target buffer**

### Frontend Canvas Display (⚠️ ROOT CAUSE FOUND)

**Location:** [ECGDisplayGrid.tsx:85-87](hospital-display-app/src/components/ECGViewer/ECGDisplayGrid.tsx#L85-L87)

```typescript
// ✅ FIX: Map display index to actual buffer index
// ECG data is stored in buffer indices 0-11
// EEG data is stored in buffer indices 12-21
const getBufferIndex = (displayIndex: number): number => {
  return isECGMode ? displayIndex : displayIndex + 12;
};
```

**Canvas Rendering Logs:**
```
[ECGWaveformCanvas c51d867e Lead Fp1] Phase 1 (Typewriter): rendered 11100 samples
[ECGWaveformCanvas c51d867e Lead Fp2] Phase 1 (Typewriter): rendered 11100 samples
[ECGWaveformCanvas c51d867e Lead F3] Phase 1 (Typewriter): rendered 11100 samples
[ECGWaveformCanvas c51d867e Lead F4] Phase 1 (Typewriter): rendered 11100 samples
[ECGWaveformCanvas c51d867e Lead C3] Phase 1 (Typewriter): rendered 11100 samples
[ECGWaveformCanvas c51d867e Lead C4] Phase 1 (Typewriter): rendered 11100 samples
[ECGWaveformCanvas c51d867e Lead O1] No data, drawing baseline  ← ❌ PROBLEM
[ECGWaveformCanvas c51d867e Lead O2] No data, drawing baseline  ← ❌ PROBLEM
```

---

## 3. ROOT CAUSE: Frontend Buffer Index Calculation Bug

### The Problem

**When EEG viewer shows 8 channels in 4x2 layout:**

```typescript
const eegLeads = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'O1', 'O2'];
const visibleLeads = layout === 1
  ? [leads.findIndex((l) => l === selectedLead)]
  : Array.from({ length: Math.min(layout, leads.length) }, (_, i) => i);
```

For layout=9 (full view), `visibleLeads = [0, 1, 2, 3, 4, 5, 6, 7]` (display indices)

**Buffer Index Calculation:**
```typescript
const getBufferIndex = (displayIndex: number): number => {
  return isECGMode ? displayIndex : displayIndex + 12;
};
```

**Mapping in EEG mode:**
- Display index 0 (Fp1) → buffer[12] ✅
- Display index 1 (Fp2) → buffer[13] ✅
- Display index 2 (F3) → buffer[14] ✅
- Display index 3 (F4) → buffer[15] ✅
- Display index 4 (C3) → buffer[16] ✅
- Display index 5 (C4) → buffer[17] ✅
- Display index 6 (O1) → buffer[18] ❌ **WRONG! Should be buffer[20]**
- Display index 7 (O2) → buffer[19] ❌ **WRONG! Should be buffer[21]**

### Why This Bug Exists

**Frontend expects 8 consecutive EEG channels:**
```
Buffer 12: Fp1
Buffer 13: Fp2
Buffer 14: F3
Buffer 15: F4
Buffer 16: C3
Buffer 17: C4
Buffer 18: O1  ← Frontend thinks O1 is here
Buffer 19: O2  ← Frontend thinks O2 is here
```

**But data is actually stored with T3/T4 slots reserved:**
```
Buffer 12: Fp1
Buffer 13: Fp2
Buffer 14: F3
Buffer 15: F4
Buffer 16: C3
Buffer 17: C4
Buffer 18: T3 (empty - temporal channels not transmitted)
Buffer 19: T4 (empty - temporal channels not transmitted)
Buffer 20: O1 ← Actual O1 location
Buffer 21: O2 ← Actual O2 location
```

### The Missing Link

**In [useECGViewer.ts:298-305](hospital-display-app/src/hooks/useECGViewer.ts#L298-L305), data IS being written to buffers 20 and 21:**

```typescript
if (occipital?.O1) {
  const samples = getData(occipital.O1);
  dataBufferRef.current[20] = [...dataBufferRef.current[20], ...samples].slice(-maxBufferSize);  // ✅ Writing to buffer 20
}
if (occipital?.O2) {
  const samples = getData(occipital.O2);
  dataBufferRef.current[21] = [...dataBufferRef.current[21], ...samples].slice(-maxBufferSize);  // ✅ Writing to buffer 21
}
```

**But [ECGDisplayGrid.tsx:85-87](hospital-display-app/src/components/ECGViewer/ECGDisplayGrid.tsx#L85-L87) is reading from buffers 18 and 19:**

```typescript
// Display index 6 (O1) + 12 = 18 ← Looking for O1 in T3's buffer (empty)
// Display index 7 (O2) + 12 = 19 ← Looking for O2 in T4's buffer (empty)
```

---

## 4. The Fix - Two Options

### Option 1: Skip T3/T4 Buffers (RECOMMENDED)

**Modify [ECGDisplayGrid.tsx:85-87](hospital-display-app/src/components/ECGViewer/ECGDisplayGrid.tsx#L85-L87):**

```typescript
// ✅ FIX: Map display index to actual buffer index, skipping T3/T4 (18, 19)
const getBufferIndex = (displayIndex: number): number => {
  if (!isECGMode) {
    // EEG buffer mapping with T3/T4 gap
    // Fp1=12, Fp2=13, F3=14, F4=15, C3=16, C4=17, [T3=18, T4=19 skipped], O1=20, O2=21
    if (displayIndex < 6) {
      return displayIndex + 12;  // Fp1-Fp2-F3-F4-C3-C4 (12-17)
    } else {
      return displayIndex + 14;  // O1-O2 (20-21) - skip T3/T4 by adding extra 2
    }
  }
  return displayIndex;  // ECG: direct 1:1 mapping
};
```

### Option 2: Compact Buffer Layout (ALTERNATIVE)

**Modify [useECGViewer.ts:298-305](hospital-display-app/src/hooks/useECGViewer.ts#L298-L305) to write O1/O2 to buffers 18-19:**

```typescript
// Occipital channels (O1, O2) - write to 18-19 instead of 20-21
if (occipital?.O1) {
  const samples = getData(occipital.O1);
  dataBufferRef.current[18] = [...dataBufferRef.current[18], ...samples].slice(-maxBufferSize);  // Changed from 20 → 18
}
if (occipital?.O2) {
  const samples = getData(occipital.O2);
  dataBufferRef.current[19] = [...dataBufferRef.current[19], ...samples].slice(-maxBufferSize);  // Changed from 21 → 19
}
```

---

## 5. Summary - Answers to Your Questions

### Q1: Can you explain the EEG generator code?
**A:** EEG generator mixes 4 frequency bands (alpha 10.5Hz, beta 20Hz, theta 6Hz, delta 2Hz) with state-dependent weighting. O1/O2 have 15% stronger alpha waves (anatomically correct - visual cortex). See section 1 above for full code walkthrough.

### Q2: Is it also 2ms thing like ECG?
**A:** ✅ YES - EEG uses **exact same 2ms timing** as ECG (500Hz sampling rate). `timeStep = 0.002` is hardcoded in `generateEEGSample()`.

### Q3: Is it advancing 2ms each lead?
**A:** ❌ NO - timing advances **2ms per SAMPLE**, NOT per lead. All 8 channels (Fp1, Fp2, F3, F4, C3, C4, O1, O2) are generated in parallel at the same time point. Then time advances 2ms, and all 8 channels generate the next sample together.

### Q4: Are O1/O2 dead/flat lines?
**A:** ✅ NO - O1/O2 are **generating correctly** on ESP32, **transmitting correctly** via MQTT, **received correctly** by frontend (`occipital: Array(2)` in logs), **written correctly** to buffers 20-21. BUT canvas is reading from wrong buffers (18-19) which are empty T3/T4 slots. **This is a buffer index mapping bug, not a data generation bug.**

---

## 6. Recommended Next Steps

1. **Implement Option 1** (skip T3/T4 buffers in display mapping)
2. **Add diagnostic logging** to verify O1/O2 buffer lengths
3. **Test with real ESP32 watch** to confirm fix
4. **Update EEG lead array** if we ever add T3/T4 support

**Priority:** HIGH - Users are missing 25% of EEG data (O1/O2 occipital channels)

---

**END OF ANALYSIS**
