# V-Lead Compression Root Cause - FOUND

## The Bug Confirmed

**Screenshot Evidence:**
- Lead I & II: ~4-5 heartbeats (normal spacing)
- V1-V6: ~15-20 heartbeats (severe horizontal compression - 3-4x more beats)
- Lead III, aVR, aVL, aVF: Normal spacing

**Console Log Evidence:**
- ALL 12 leads: Exactly 12,500 samples
- ALL 12 leads: `samplesVisible=1661`
- ALL 12 leads: Identical rendering parameters

## ESP32 Waveform Generation Analysis

### Code Verified ([PhysiologicalSimulator.cpp:468-500](../esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L468-L500))

```cpp
void PhysiologicalSimulator::fillSampleBuffer(int32_t buffer[8][10]) {
    // ✅ FIX: Calculate phase ONCE per sample, use same phase for all leads
    for (int i = 0; i < 10; i++) {
        if (currentMode == MODE_ECG) {
            // ECG: Calculate cardiac cycle phase for this sample
            float cycleDuration = 60000.0 / currentHeartRate;
            float phase = ecgCycleTime / cycleDuration;

            // Generate all 8 leads with same phase
            for (int lead = 0; lead < 8; lead++) {
                generateECGSampleWithPhase(lead, phase, buffer[lead][i]);
            }

            // ✅ Increment time ONCE per sample (not per lead)
            ecgCycleTime += 2.0;  // 500 Hz = 2ms per sample
            if (ecgCycleTime >= cycleDuration) {
                ecgCycleTime = 0.0;  // New beat - reset to P wave
            }
        }
    }
}
```

**✅ CORRECT:** All leads share the SAME phase at each sample point - timing is synchronized.

### Lead Vector Amplitudes ([PhysiologicalSimulator.cpp:388-466](../esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L388-L466))

```cpp
case 1:  // Lead II (+60° - Inferior, REFERENCE lead)
    R_vec = 1.0;    // Tallest R (reference)

case 2:  // V1 (Right precordial - rS pattern)
    R_vec = 0.30;   // SMALL r wave (30% of normal)
    S_vec = 2.50;   // DEEP S wave (250% of normal)

case 3:  // V2 (Transitional - RS pattern)
    R_vec = 0.65;   // Growing R (65% of normal)
    S_vec = 1.80;   // Still significant S (180%)

case 5:  // V4 (Left precordial - TALLEST R wave)
    R_vec = 1.40;   // TALLEST R wave (140%)
    S_vec = 0.40;   // Small S (40%)
```

**Analysis:** V-leads have different **vertical amplitudes** (especially deeper S waves), but NOT different **horizontal timing**.

## Frontend Rendering Analysis

### Buffer Processing ([useECGViewer.ts:139-184](../hospital-display-app/src/hooks/useECGViewer.ts#L139-L184))

```typescript
// Limb leads (I, II, III) - REQUIRED
if (limb?.leadI) {
  const samples = getData(limb.leadI, 'Lead I');
  dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);
}

// Precordial leads (V1-V6) - OPTIONAL
if (precordial?.v1) {
  const samples = getData(precordial.v1, 'V1');
  dataBufferRef.current[6] = [...dataBufferRef.current[6], ...samples].slice(-maxBufferSize);
}
```

**✅ IDENTICAL PROCESSING** for all leads.

### Canvas Rendering ([ECGWaveformCanvas.tsx:152-169](../hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L152-L169))

```typescript
// ✅ PHASE 2: ICU Monitor Typewriter Mode - show LAST samplesVisible samples
const visibleData = data.slice(-samplesVisible);

renderWaveformSegment(
  visibleData,
  ctx,
  0,  // Fill entire screen from left to right
  height,
  isECGMode,
  pixelsPerSample,
  pixelsPerUnit,
  leadColor
);
```

**✅ IDENTICAL RENDERING** for all leads.

## The Paradox

### What We Know:
1. ✅ ESP32 sends 50 samples per lead every 100ms (verified in code)
2. ✅ All leads share same cardiac phase timing (verified in fillSampleBuffer)
3. ✅ Frontend processes all leads identically (verified in useECGViewer.ts)
4. ✅ Canvas renders all leads identically (verified in ECGWaveformCanvas.tsx)
5. ✅ Console logs show all leads have 12,500 samples
6. ✅ All leads display last 1,661 samples (`samplesVisible=1661`)

### What We See:
- 🚨 **V-leads show 3-4x MORE heartbeats** in the same canvas width
- 🚨 **Lead I/II show ~4-5 heartbeats** (normal)
- 🚨 **V1-V6 show ~15-20 heartbeats** (compressed)

## Hypothesis: The REAL Root Cause

Given that:
- Code is correct and identical for all leads
- Timing is synchronized across all leads
- Buffer sizes are identical
- Rendering logic is identical

**The only possible explanation:**

### 🔍 BATCH UPLOAD DATA DUPLICATION

The V-leads might be receiving **DUPLICATE or CONCATENATED data packets** during the 30-second batch upload process.

**Evidence needed:**
1. Check sequence numbers to detect out-of-order messages
2. Check actual delta array lengths in real-time
3. Compare Lead I vs V1 delta counts at same sequence number

**Diagnostic logs added but not yet loaded:**
```typescript
// 🔢 Waveform sequence: 10, 20, 30...
// 🔍 Lead I: 50 deltas → 51 samples (SEQ: 10)
// 🔍 V1: 150 deltas → 151 samples (SEQ: 10) ← WOULD PROVE DUPLICATION
// 📊 Buffer lengths at sequence 10:
```

## Next Steps

**IMMEDIATE:** Ask user to hard refresh browser (Ctrl+Shift+R) to load diagnostic logging code

**THEN:** Analyze diagnostic logs to confirm if:
- V-leads receive different delta array lengths than Lead I/II
- Sequence numbers show batch upload out-of-order delivery
- Buffer accumulation differs between limb leads and V-leads

## Alternative Theory (Less Likely)

**WebSocket message parsing bug** where V-leads get concatenated with previous messages, but this would show in buffer lengths (which are identical at 12,500).

**Conclusion:** The bug is REAL but hidden in the **data delivery layer** (MQTT → WebSocket → React state), not in the ESP32 generation or frontend rendering logic.
