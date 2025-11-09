# ECG/EEG Metrics Integration - Implementation Plan

## Problem Diagnosis

The backend IS running ECG/EEG analysis correctly, but the results are NOT appearing in the patient vitals tooltip because of a data storage mismatch.

### Current Flow (BROKEN):
1. ✅ ESP32 sends vitals message with waveform data
2. ✅ MQTT service receives message
3. ✅ Backend runs ECG/EEG analysis service (lines 516-530 in mqtt_service.py)
4. ✅ Analysis calculates rrInterval, qrsDuration, alphaPower, etc.
5. ❌ **BUG**: Analysis results are stored in a SEPARATE vitals_realtime row (line 149, 167)
6. ❌ **RESULT**: Frontend queries latest vitals and gets basic vitals only, NOT the analysis metrics

### Root Cause:
**File:** `hospital-backend/app/services/mqtt_service.py`
**Lines:** 478, 149, 167

The `_storeVitalsRealtime()` function (line 478) stores basic vitals.
Then `_storeAnalysisAsVitals()` function (lines 149, 167) stores analysis results in a DIFFERENT row with a DIFFERENT timestamp.

When the frontend queries "latest vitals", it gets whichever row has the most recent timestamp - usually the basic vitals row WITHOUT the analysis metrics!

## Solution

### Option 1: Store Analysis WITH Basic Vitals (RECOMMENDED)
Modify the flow to pass analysis results to `_storeVitalsRealtime()` so they're stored in the SAME row.

**Pros:**
- Single database row per vitals update
- Frontend gets ALL data in one query
- Matches expected data structure
- More efficient

**Cons:**
- Requires refactoring mqtt_service.py

### Option 2: Update Existing Row With Analysis
After analysis completes, UPDATE the existing vitals row with analysis results.

**Pros:**
- Minimal code changes
- Clear separation of concerns

**Cons:**
- Two database operations per vitals update
- Potential race conditions

### Option 3: Frontend Query Both Rows
Modify frontend/patient_service to query BOTH vitals rows and merge them.

**Pros:**
- No backend changes needed

**Cons:**
- Complex frontend logic
- Slower queries
- Doesn't fix root cause

## Recommended Solution: Option 1

### Implementation Steps:

#### Step 1: Modify `_storeVitalsRealtime()` to Accept Analysis Results
**File:** `hospital-backend/app/services/mqtt_service.py`
**Function:** `_storeVitalsRealtime(vitalsMsg, ecgAnalysis=None, eegAnalysis=None)`

Change the function signature to accept optional analysis results:
```python
async def _storeVitalsRealtime(
    self,
    vitalsMsg: VitalsRealtimeMessage,
    ecgAnalysis: Optional[ECGAnalysisResult] = None,
    eegAnalysis: Optional[EEGAnalysisResult] = None
):
```

#### Step 2: Update INSERT Statement
Use the analysis results when inserting into vitals_realtime:
```python
await tsConn.execute("""
    INSERT INTO vitals_realtime (
        time, "patientId", "deviceId", mode,
        "heartRate", "respiratoryRate", "skinTemperature",
        "oxygenSaturation", "batteryLevel", "signalQuality",
        "rrInterval", "qrsDuration", "qtInterval", axis, rhythm, "stSegment",
        "alphaPower", "betaPower", "thetaPower", "deltaPower", "gammaPower",
        "dominantFrequency", "seizureActivity",
        ...
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
        $11, $12, $13, $14, $15, $16,  # ECG analysis
        $17, $18, $19, $20, $21, $22, $23,  # EEG analysis
        ...
    )
""",
    vitalsMsg.timestamp, vitalsMsg.patientId, vitalsMsg.deviceId, vitalsMsg.mode,
    vitalsMsg.heartRate, vitalsMsg.respiratoryRate, vitalsMsg.skinTemperature,
    vitalsMsg.oxygenSaturation, vitalsMsg.batteryLevel, vitalsMsg.signalQuality,
    ecgAnalysis.rrInterval if ecgAnalysis else None,
    ecgAnalysis.qrsDuration if ecgAnalysis else None,
    ecgAnalysis.qtInterval if ecgAnalysis else None,
    ecgAnalysis.axis if ecgAnalysis else None,
    ecgAnalysis.rhythm if ecgAnalysis else None,
    ecgAnalysis.stSegment if ecgAnalysis else None,
    eegAnalysis.alphaPower if eegAnalysis else None,
    eegAnalysis.betaPower if eegAnalysis else None,
    eegAnalysis.thetaPower if eegAnalysis else None,
    eegAnalysis.deltaPower if eegAnalysis else None,
    eegAnalysis.gammaPower if eegAnalysis else None,
    eegAnalysis.dominantFrequency if eegAnalysis else None,
    eegAnalysis.seizureActivity if eegAnalysis else None,
    ...
)
```

#### Step 3: Modify `_handleVitalsMessageNew()` Flow
**File:** `hospital-backend/app/services/mqtt_service.py`
**Lines:** 480-538

Change from:
```python
# Store vitals first
await self._storeVitalsRealtime(vitalsMsg)

# Run analysis
analysisResult = ecgAnalysisService.analyzeECG(waveformData, mode='ecg')

# Store analysis separately (WRONG!)
await self._storeAnalysisAsVitals(patientId, deviceId, analysisResult, 'ecg')
```

To:
```python
# Run analysis FIRST
analysisResult = None
if waveformMsg.mode == 'ecg' and waveformMsg.ecgWaveform:
    analysisResult = ecgAnalysisService.analyzeECG(waveformData, mode='ecg')

# Store vitals WITH analysis results
await self._storeVitalsRealtime(
    vitalsMsg,
    ecgAnalysis=analysisResult if vitalsMsg.mode == 'ecg' else None,
    eegAnalysis=analysisResult if vitalsMsg.mode == 'eeg' else None
)
```

#### Step 4: Remove `_storeAnalysisAsVitals()` Function
This function is no longer needed since analysis is stored with vitals.

**Lines to Remove:** 857-913

#### Step 5: Update `_handleWaveformMessage()` Similarly
The waveform handler (lines 106-181) has the same issue. Apply same fix.

## Testing Checklist

After implementation:
- [ ] ESP32 sends vitals with waveform data
- [ ] Backend runs ECG/EEG analysis
- [ ] Analysis results stored in SAME vitals_realtime row as basic vitals
- [ ] Frontend query returns vitals WITH ecg/eeg objects
- [ ] Tooltip shows "RR: 850ms | QRS: 95ms..." instead of "No ECG metrics available"
- [ ] Both ECG and EEG modes work correctly
- [ ] Analysis confidence threshold (>0.5) is respected

## Files to Modify

1. ✏️ `hospital-backend/app/services/mqtt_service.py`
   - Line 635: Modify `_storeVitalsRealtime()` signature
   - Lines 652-696: Update INSERT statement to include analysis
   - Lines 480-538: Modify flow in `_handleVitalsMessageNew()`
   - Lines 106-181: Modify flow in `_handleWaveformMessage()`
   - Lines 857-913: DELETE `_storeAnalysisAsVitals()` function

## Expected Result

After fix, when hovering over ECG/EEG title in PatientCard:
- **Before:** "No ECG metrics available"
- **After:** "ECG Metrics: RR: 850ms | QRS: 95ms | QT: 410ms | Rhythm: sinus | Axis: 45° | ST: normal"

## Estimated Effort

- Code changes: 30 minutes
- Testing: 15 minutes
- Total: 45 minutes

## Risk Assessment

**Risk Level:** LOW

**Risks:**
- Minimal - just reorganizing when data is stored
- No schema changes needed
- No frontend changes needed
- Backwards compatible (analysis fields are optional)

**Mitigation:**
- Test with both ECG and EEG modes
- Verify existing vitals still work if analysis fails
- Check that analysis confidence threshold is respected
