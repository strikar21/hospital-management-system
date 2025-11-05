# Waveform Horizontal Compression - Root Cause Research

## User's Observation:
- **Seeing**: 2 complete ECG waves in 5mm (one large grid square)
- **Expected**: 1 wave in 3-4 large squares (15-20mm at 72 BPM)

## Investigation Steps:

### 1. ESP32 Data Generation ✅ CORRECT
**File**: esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino

**Line 1952**: `doc["sampleRate"] = 500;` ✅ Sends correct sample rate
**Line 1952**: `doc["duration"] = 0.1;` ✅ 100ms packets

**Generation Flow**:
- `generateMicroBatch()` called every 20ms (line 1095)
- Each call generates 10 samples via `simulator.fillSampleBuffer()` (line 1897)
- Accumulates to 50 samples
- `sendWaveformStream()` called every 100ms when buffer reaches 50 samples (line 1102)

**Math**:
```
5 batches × 10 samples = 50 samples per 100ms
50 samples / 0.1 seconds = 500 samples/second ✅ CORRECT
```

### 2. ESP32 ECG Timing ✅ CORRECT
**File**: esp32_hospital_watch_complete/PhysiologicalSimulator.cpp

**Line 16**: `currentHeartRate = 72.0;` (resting heart rate)
**Line 297**: `float cycleDuration = 60000.0 / currentHeartRate;`
**Line 325**: `ecgCycleTime += 2.0;` (updates every 2ms for 500Hz)

**Math**:
```
At 72 BPM:
cycleDuration = 60000ms / 72 = 833ms per beat
At 500Hz: 2ms per sample
833ms / 2ms = 416.5 samples per cardiac cycle ✅ CORRECT
```

### 3. Frontend Sample Rate ✅ CORRECT
**File**: hospital-display-app/src/config/ecgConfig.ts

**Line 24**: `export const SAMPLE_RATE_HZ = 500;` ✅ CORRECT

**File**: hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx

**Line 105**: `const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ;`

**Math**:
```
DPI = 96 (typical)
25mm/s paper speed
1mm = 96/25.4 = 3.78 pixels
25mm = 94.49 pixels per second
pixelsPerSample = 94.49 / 500 = 0.1890 pixels per sample ✅ CORRECT
```

### 4. Expected vs Actual Rendering

**Expected at 72 BPM**:
```
Cycle time: 833ms
Samples per cycle: 416.5 samples
Distance on screen: 416.5 × 0.1890 pixels/sample = 78.72 pixels
78.72 pixels / 3.78 pixels/mm = 20.8mm per wave ✅ CORRECT (4.2 large squares)
```

**User observes**: 2 waves in 5mm = each wave is 2.5mm

**Compression factor**: 20.8mm / 2.5mm = **8.32x too compressed**

---

## HYPOTHESIS: Data is Being Skipped or Downsampled

### Possible Causes:

1. **Frontend buffer slicing**: useECGViewer.ts might be slicing data incorrectly
2. **WebSocket dropping packets**: Not all 50-sample packets arriving
3. **Delta decoding failure**: decodeDeltaChannel() returning fewer samples
4. **Rendering skipping samples**: renderWaveformSegment() not drawing all samples
5. **Incorrect sample rate fallback**: Using 250Hz instead of 500Hz somewhere

---

## Let me check the actual data flow:

Need to verify:
1. How many samples are ACTUALLY in the buffer?
2. Is delta decoding working correctly?
3. Is renderWaveformSegment() drawing ALL samples?

---

## Action Items:

1. Check browser console for the debug log showing actual sample counts
2. Verify decodeDeltaChannel() is returning 50 samples (not 6-7 samples)
3. Check if frontend is using `waveformData.sampleRate || 250` fallback instead of 500
4. Verify renderWaveformSegment() is iterating through ALL samples

---

## Next Step:

**ASK USER**: Can you open the browser console and show me the output? Specifically looking for:
- `🔍 [Lead II] DPI spacing: ...` log showing actual sample counts
- Any errors about delta decoding
- Actual buffer lengths

The answer is **NOT** to multiply by 8x - that's treating the symptom not the cause.

We need to find WHERE the samples are being lost/skipped in the data pipeline.
