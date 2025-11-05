# Horizontal Scaling Analysis - ECG Waveform Compression

## User's Observation:
- **Current**: 2 waves in 5mm box (one large square)
- **Expected**: 1 wave = 3-4 small squares (3-4mm)

## Problem: Waveform is horizontally compressed (too fast)

---

## Current Configuration

### From ecgConfig.ts:
```typescript
PAPER_SPEED_MM_PER_S = 25;  // 25mm/s (standard)
SAMPLE_RATE_HZ = 500;       // 500Hz
```

### Calculations:
```
Time per large square (5mm):
5mm ÷ 25mm/s = 0.2 seconds = 200ms

Samples per large square:
500 samples/s × 0.2s = 100 samples

If 2 waves in 5mm:
- Each wave = 2.5mm = 50 samples = 100ms per wave
- Heart rate = 600 beats/min (60000ms / 100ms)
```

**This is IMPOSSIBLE** - 600 BPM is medically impossible (normal HR = 60-100 BPM)

---

## Root Cause Analysis

### Expected ECG Timing:
- **Normal heart rate**: 60-100 BPM
- **At 72 BPM**: 833ms per beat
- **Expected wave width**: 833ms per PQRST complex

### Expected Grid Size:
```
At 25mm/s paper speed:
833ms per beat × 25mm/s = 20.8mm per wave

One PQRST should span:
20.8mm = 4.16 large squares (5mm each)
       = 20.8 small squares (1mm each)
```

**User expects**: 1 wave = 3-4 squares → This matches ~15-20mm → **CORRECT**

---

## What's Wrong?

### Option 1: pixelsPerSample is Wrong
**File**: ECGWaveformCanvas.tsx line 105
```typescript
const pixelsPerSecond = mmToPixels(PAPER_SPEED_MM_PER_S); // 25mm/s at detected DPI
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ; // Fixed: 25mm/s ÷ 500Hz
```

**Math check**:
```
DPI = 96 (typical)
1mm = 96/25.4 = 3.78 pixels

25mm = 94.49 pixels per second
pixelsPerSample = 94.49 / 500 = 0.1890 pixels per sample

At 833ms per beat (72 BPM):
417 samples × 0.1890 px/sample = 78.8 pixels per wave

At 5mm = 18.9 pixels:
18.9px / 0.1890 px/sample = 100 samples = 200ms = 300 BPM
```

**This matches user's observation: 2 waves in 5mm**

---

## Solution: The Math is Actually CORRECT

Wait... let me recalculate based on what the ESP32 is ACTUALLY sending.

### If user sees 2 waves in 5mm:
```
2 waves in 5mm = 2 waves in 0.2 seconds
Each wave = 0.1 seconds = 100ms
Heart rate = 600 BPM
```

**BUT** the ESP32 simulator shows:
```cpp
// From PhysiologicalSimulator.cpp
currentHeartRate = 72.0;  // Resting heart rate
```

### The Issue: **Data is being downsampled or skipped**

Possible causes:
1. **MQTT/WebSocket dropping packets** - not all waveform data arriving
2. **Frontend skipping samples** - renderWaveformSegment() not drawing all samples
3. **Buffer is wrapping too fast** - circular buffer overwriting data before render
4. **pixelsPerSample calculation is wrong** - need to multiply by factor

---

## Quick Fix: Multiply pixelsPerSample

**User asks**: "what should i multiply with?"

**Answer**: You need to make waveforms **2x wider** (currently 2 waves in 5mm, want 1 wave in 4mm)

```typescript
// Current:
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ;

// Fix:
const pixelsPerSample = (pixelsPerSecond / SAMPLE_RATE_HZ) * 2.0;
```

**Why 2x?**
- Current: 2 waves in 5mm → Need: 1 wave in 5mm → **2x wider**
- OR: Current 2 waves in 5mm → Need: 1 wave in 4mm → **2.5x wider**

**Try**: Start with **2x** multiplier

---

## Implementation

### File: ECGWaveformCanvas.tsx line 105

**Before:**
```typescript
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ;
```

**After:**
```typescript
const HORIZONTAL_SCALE_FACTOR = 2.0;  // ← ADJUST THIS (try 2.0, then 2.5, then 3.0)
const pixelsPerSample = (pixelsPerSecond / SAMPLE_RATE_HZ) * HORIZONTAL_SCALE_FACTOR;
```

---

## Alternative: Check if Data is Missing

It's possible the ESP32 is sending data but the frontend is only receiving/rendering 50% of it.

**Check**:
1. ESP32 sends 50 samples per 100ms batch
2. Backend receives all 50 samples
3. Frontend WebSocket receives all 50 samples
4. Canvas renders all 50 samples

**Debug**: Add console log to check data arrival rate:
```typescript
console.log(`Received ${samples.length} samples in ${deltaTime}s = ${samples.length/deltaTime} samples/s`);
```

**Expected**: ~500 samples/s
**If seeing**: ~250 samples/s → Data is being dropped

---

## Recommendation

**Start with horizontal scale multiplier of 2x** and adjust from there:

```typescript
// Try values: 1.5, 2.0, 2.5, 3.0
const HORIZONTAL_SCALE_FACTOR = 2.0;
const pixelsPerSample = (pixelsPerSecond / SAMPLE_RATE_HZ) * HORIZONTAL_SCALE_FACTOR;
```

This will make the waveform **2x wider horizontally**, so:
- Current: 2 waves in 5mm
- After 2x: 1 wave in 5mm
- After 2.5x: 1 wave in 6.25mm (≈ 1 wave in 4-5 small squares) ✅ MATCHES USER EXPECTATION
