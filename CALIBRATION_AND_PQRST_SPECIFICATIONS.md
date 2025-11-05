# Calibration Pulse & PQRST Complex - Complete Specifications

## Your Questions Answered

### 1. Does the calibration pulse have a tail? (Small 1 square flat line)

**Answer: NO - Current implementation has NO tail**

Looking at [ECGViewerContainer.tsx:51-63](hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx#L51-L63):

```typescript
const samplesPerSecond = 500;
const pulseDuration = 0.2; // 200ms pulse
const totalPulseSamples = Math.floor(samplesPerSecond * pulseDuration); // 100 samples
const pulseADC = 8388608 + (1 * 100000); // 1mV in ADC units
const calibrationPulse = new Array(totalPulseSamples).fill(pulseADC);
const spacerSamples = new Array(100).fill(8388608); // 0.2s baseline at 0mV

dataBufferRef.current[index] = [...spacerSamples, ...calibrationPulse];
//                                ^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^
//                                  100 samples       100 samples
//                                  at 0mV (flat)     at 1mV (pulse)
```

**Current Pattern:**
```
Spacer (200ms) + Pulse (200ms) = Total 400ms
[0mV baseline] [1mV pulse]      [then data starts]
```

**Standard Medical Calibration Pulse Should Be:**
```
[1mV pulse] [0mV tail] = Total 400ms
  200ms       200ms
```

**ISSUE FOUND:** The spacer is BEFORE the pulse, should be AFTER!

### 2. Is the pulse 1mV? ✅ YES

**Answer: YES - Exactly 1mV**

From [ECGViewerContainer.tsx:55](hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx#L55):
```typescript
const pulseADC = 8388608 + (1 * 100000); // 1mV in ADC units
//               ^^^^^^^^   ^^^^^^^^^^^
//               Midpoint   +1mV offset
//               (0mV)      (100,000 ADC units = 1mV)
```

**ADC Encoding (from ESP32):**
- **Midpoint:** 8,388,608 (24-bit ADC center = 0mV)
- **Scale:** 100,000 ADC units per 1mV
- **Pulse value:** 8,388,608 + 100,000 = **8,488,608 ADC units = +1.0mV** ✅

**Visual on Grid (at 10mm/mV scale):**
- 1mV = 10mm = 2 big squares (vertical)
- 200ms = 5mm = 1 big square (horizontal)
- **Expected size: 2×1 big squares** ✅ (User confirmed this is correct!)

### 3. PQRST Complex Values (From ESP32)

From [PhysiologicalSimulator.cpp:280-363](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L280-L363):

#### **P Wave (0-8% of cycle, ~80ms)**
- **Amplitude:** 0.15 mV
- **Shape:** Smooth sinusoidal bump
- **Represents:** Atrial depolarization
```cpp
amplitude = 0.15 * sin(t * PI);  // Peak: +0.15mV
```

#### **PR Segment (8-16% of cycle, ~80ms)**
- **Amplitude:** 0.0 mV ✅ **FLAT LINE (isoelectric)**
- **Represents:** AV node delay
```cpp
amplitude = 0.0;
```

#### **Q Wave (16-18% of cycle, ~20ms)**
- **Amplitude:** -0.15 mV (negative deflection)
- **Represents:** Initial septal depolarization
```cpp
amplitude = -0.15 * (t / 0.25);  // Max: -0.15mV
```

#### **R Wave (18-21.5% of cycle, ~35ms)**
- **Amplitude:** ~1.5 mV (peak value, varies by lead)
- **Shape:** Sharp positive spike (tallest part!)
- **Represents:** Ventricular depolarization
```cpp
amplitude = -0.15 + 1.7 * sin(r_t * PI);  // Peak: ~1.55mV
//          ^^^^^^   ^^^
//          Offset   Tall spike!
```

#### **S Wave (21.5-24% of cycle, ~28ms)**
- **Amplitude:** -0.25 mV (negative deflection)
- **Represents:** Late ventricular depolarization
```cpp
amplitude = -0.25 * (1.0 - s_t);  // Max: -0.25mV
```

#### **ST Segment (24-32% of cycle, ~80ms)**
- **Amplitude:** 0.0 mV ✅ **FLAT LINE (isoelectric)**
- **Represents:** Early ventricular repolarization
- **Clinical note:** ST elevation/depression = emergency!
```cpp
amplitude = 0.0;
```

#### **T Wave (32-56% of cycle, ~240ms)**
- **Amplitude:** 0.30 mV
- **Shape:** Smooth rounded positive wave
- **Represents:** Ventricular repolarization
```cpp
amplitude = 0.30 * sin(t * PI);  // Peak: +0.30mV
```

#### **TP Segment (56-100% of cycle, ~440ms)**
- **Amplitude:** 0.0 mV ✅ **FLAT LINE (isoelectric)**
- **Represents:** Diastole (heart at rest before next beat)
```cpp
amplitude = 0.0;
```

## Complete ECG Cycle Timeline (at 72 BPM)

Total cycle duration: **833ms** (60,000ms / 72 beats)

| Phase | Duration | % of Cycle | Amplitude | Description |
|-------|----------|------------|-----------|-------------|
| **P wave** | 80ms | 0-8% | +0.15 mV | Atrial contraction |
| **PR segment** | 80ms | 8-16% | **0.0 mV** | **FLAT** - AV delay |
| **Q wave** | 20ms | 16-18% | -0.15 mV | Septal depolarization |
| **R wave** | 35ms | 18-21.5% | **+1.5 mV** | **TALLEST** - Ventricular depolarization |
| **S wave** | 28ms | 21.5-24% | -0.25 mV | Late depolarization |
| **ST segment** | 80ms | 24-32% | **0.0 mV** | **FLAT** - Early repolarization |
| **T wave** | 240ms | 32-56% | +0.30 mV | Ventricular repolarization |
| **TP segment** | 440ms | 56-100% | **0.0 mV** | **FLAT** - Diastole |

## Lead-Specific Amplitude Multipliers

The base PQRST values above are multiplied by lead-specific factors:

| Lead | Name | Multiplier | R-Wave Peak | Notes |
|------|------|------------|-------------|-------|
| 0 | Lead I (LA-RA) | 0.75× | 1.125 mV | Lateral view |
| 1 | Lead II (LL-RA) | 1.0× | **1.5 mV** | Reference (tallest limb lead) |
| 2 | V1 (precordial) | 0.50× | 0.75 mV | Small R, deep S |
| 3 | V2 (precordial) | 0.65× | 0.975 mV | Transitional |
| 4 | V3 (precordial) | 0.85× | 1.275 mV | Balanced R=S |
| 5 | V4 (precordial) | 1.25× | **1.875 mV** | **Tallest R wave!** |
| 6 | V5 (precordial) | 1.15× | 1.725 mV | High lateral |
| 7 | V6 (precordial) | 1.05× | 1.575 mV | Lateral |

## Visual Summary

### What You SHOULD See on Display:

```
Time (horizontal) →

  [Calibration Pulse]   [First Heartbeat]          [Second Heartbeat]

   2 squares    ___                  ___                     ___
   tall (1mV)  |   |                |   | T                 |   | T
               |   |   P      R     |   |          P      R |   |
  ─────────────     ──────  ────────     ─────────────  ────────     ────
                           \/                              \/
                           Q S                             Q S

  ← 1 square → ← baseline → QRS ← ST → T ← TP baseline →
     200ms       ~440ms     ~80ms  80ms  240ms  ~440ms
```

### Key Features to Verify:

✅ **Calibration pulse:** 1mV tall, 200ms wide (2 vertical × 1 horizontal big squares)
✅ **After pulse:** Should be flat baseline (0mV) before first heartbeat
✅ **P wave:** Small bump (+0.15mV)
✅ **PR segment:** **FLAT at 0mV** for ~80ms
✅ **QRS complex:** Sharp spike (R wave ~1.5mV is tallest)
✅ **ST segment:** **FLAT at 0mV** for ~80ms (very important clinically!)
✅ **T wave:** Rounded bump (+0.30mV)
✅ **TP segment:** **FLAT at 0mV** for ~440ms (longest flat part)

## BUG IDENTIFIED: Calibration Pulse Order Wrong

**Current implementation puts spacer BEFORE pulse:**
```typescript
dataBufferRef.current[index] = [...spacerSamples, ...calibrationPulse];
//                               ^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^
//                               WRONG ORDER!
```

**Should be:**
```typescript
dataBufferRef.current[index] = [...calibrationPulse, ...spacerSamples];
//                               ^^^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^
//                               Pulse first         Then flat tail
```

This matches standard ECG machine behavior where the calibration pulse has a trailing flat segment.

---

## Answer Summary

| Question | Answer |
|----------|--------|
| Does calibration pulse have a tail? | **NO (BUG!)** - Should have 200ms flat tail after pulse |
| Is the pulse 1mV? | **YES ✅** - Exactly 1.0mV = 2 big squares tall |
| P wave amplitude? | **+0.15 mV** |
| Q wave amplitude? | **-0.15 mV** |
| R wave amplitude? | **~1.5 mV** (tallest, varies by lead 0.75-1.875mV) |
| S wave amplitude? | **-0.25 mV** |
| T wave amplitude? | **+0.30 mV** |
| PR segment? | **0.0 mV (FLAT)** ✅ |
| ST segment? | **0.0 mV (FLAT)** ✅ |
| TP segment? | **0.0 mV (FLAT)** ✅ |

**All three isoelectric segments should display as perfectly flat baselines at 0mV!**
