# Waveform Storage & Vitals Analysis NOT Working - Root Cause Research

**Date:** 2025-11-07
**Issue:** Neither waveform analysis NOR vitals alerts are happening
**Status:** ROOT CAUSE IDENTIFIED

---

## Executive Summary

**The backend IS receiving messages, but:**
1. ✅ `/stream` messages arrive (10/sec, waveform only)
2. ✅ `/vitals` messages arrive (1/sec, basic vitals only)
3. ❌ ECG/EEG analysis NEVER runs (no "🧠 Running ECG analysis..." logs)
4. ❌ Waveform metrics don't appear in tooltip
5. ❌ Alert detection may also be impacted

---

## Evidence from Backend Logs

### What IS Working:
```
2025-11-07 10:14:12 - 📨 MQTT STREAM MESSAGE RECEIVED: hospital/devices/fit-00001/stream
2025-11-07 10:14:12 -    Payload keys: ['deviceId', 'patientId', 'timestamp', 'mode', 'sequence', 'duration', 'sampleRate', 'ecgWaveform']
2025-11-07 10:14:12 -    Has ecgWaveform: True
2025-11-07 10:14:12 - ✅ Security validation passed for stream: deviceId=fit-00001, status=assigned
2025-11-07 10:14:13 - 📊 8CH Vitals processed for patient 081a5294... from device fit-00001 (mode: ecg)
```

### What is NOT Working:
**MISSING from logs:**
```
🧠 Running ECG analysis for patient...  ← NEVER APPEARS
✅ ECG Analysis: HR=89 BPM...           ← NEVER APPEARS
```

---

## Root Cause Analysis

### Architecture Problem

ESP32 sends TWO separate MQTT messages:

1. **`/stream` topic** - Waveform data only (10 msg/sec)
   - Contains: `ecgWaveform` OR `eegWaveform`
   - NO vitals data (HR, SpO2, temp, etc.)
   - Handler: `_handleWaveformStream()` at [mqtt_service.py:251](c:/Users/Srika/OneDrive/Desktop/hospital-management-system/hospital-backend/app/services/mqtt_service.py#L251)
   - **Does NOT run analysis** - just stores to database & broadcasts WebSocket

2. **`/vitals` topic** - Basic vitals only (1 msg/sec)
   - Contains: `heartRate`, `oxygenSaturation`, `skinTemperature`, etc.
   - NO waveform data
   - Handler: `_handleVitalsMessageNew()` at [mqtt_service.py:450](c:/Users/Srika/OneDrive/Desktop/hospital-management-system/hospital-backend/app/services/mqtt_service.py#L450)
   - **Supposed to run analysis** BUT condition at line 481 checks for waveform:

```python
# Line 481-482: mqtt_service.py
if (vitalsMsg.sampleRate and vitalsMsg.duration and
    (vitalsMsg.ecgWaveform or vitalsMsg.eegWaveform)):
```

**This condition is ALWAYS FALSE** because `/vitals` messages don't contain waveform data!

---

## Why Analysis Never Runs

### Current Code Logic (Lines 477-530):

```python
# ========================================
# RUN ECG/EEG ANALYSIS FIRST (if waveform data present)
# ========================================
# Run backend analysis BEFORE storing vitals so we can include results in same row
if (vitalsMsg.sampleRate and vitalsMsg.duration and
    (vitalsMsg.ecgWaveform or vitalsMsg.eegWaveform)):  # ← ALWAYS FALSE

    if vitalsMsg.mode == 'ecg' and vitalsMsg.ecgWaveform:
        logger.info(f"🧠 Running ECG analysis...")  # ← NEVER EXECUTES
        analysisResult = ecgAnalysisService.analyzeECG(vitalsMsg.ecgWaveform.dict(), mode='ecg')
        # ... attach to vitalsMsg.ecgAnalysis

    elif vitalsMsg.mode == 'eeg' and vitalsMsg.eegWaveform:
        logger.info(f"🧠 Running EEG analysis...")  # ← NEVER EXECUTES
        analysisResult = eegAnalysisService.analyzeEEG(vitalsMsg.eegWaveform.dict(), mode='eeg')
        # ... attach to vitalsMsg.eegAnalysis

# Store in TimescaleDB vitals_realtime table (NOW includes analysis results)
await self._storeVitalsRealtime(vitalsMsg)  # ← Stores WITHOUT analysis metrics
```

**Result:** Vitals are stored to `vitals_realtime` table WITHOUT ECG/EEG analysis fields populated!

---

## Why Waveform Handler Doesn't Help

There's a **separate handler** for `/waveform` topic (10-second snapshots):
- Handler: `_handleWaveformMessage()` at [mqtt_service.py:175](c:/Users/Srika/OneDrive/Desktop/hospital-management-system/hospital-backend/app/services/mqtt_service.py#L175)
- **DOES run analysis** (lines 208-242)
- **BUT** analysis results are NOT stored in `vitals_realtime` table
- Comment at line 204 says: *"Analysis results from standalone waveform messages are NOT stored in vitals_realtime because they don't have vitals data"*

---

## Impact on Frontend

### Tooltip Shows "No ECG metrics available" Because:

1. Frontend queries `vitals_realtime` table for latest vitals
2. Backend returns vitals WITH NULL ECG/EEG analysis fields:
   ```javascript
   {
     heartRate: 89,
     oxygenSaturation: 98,
     skinTemperature: 36.5,
     ecg: null,  // ← Should be { rrInterval: 780, qrsDuration: 85, rhythm: "sinus", ... }
     eeg: null   // ← Should be { alphaPower: 25.3, betaPower: 18.7, ... }
   }
   ```
3. Frontend code in [PatientCardWaveform.tsx:91-96](c:/Users/Srika/OneDrive/Desktop/hospital-management-system/hospital-display-app/src/components/PatientCard/PatientCardWaveform.tsx#L91) checks:
   ```typescript
   const hasMetrics = patient.vitals?.ecg || patient.vitals?.eeg;

   {hasMetrics ? (
     <div>RR: {patient.vitals.ecg.rrInterval}ms ...</div>
   ) : (
     <div>No ECG metrics available</div>  // ← THIS IS WHAT WE SEE
   )}
   ```

---

## Alert Detection Status

**ALERT DETECTION CODE EXISTS** at [mqtt_service.py:600-664](c:/Users/Srika/OneDrive/Desktop/hospital-management-system/hospital-backend/app/services/mqtt_service.py#L600):

```python
# ========================================
# ALERT DETECTION (Complete System - Components 1 & 3)
# ========================================
# Detect alerts from vitals data
vitalsDict = {
    'heartRate': vitalsMsg.heartRate,
    'oxygenSaturation': vitalsMsg.oxygenSaturation,
    'respiratoryRate': vitalsMsg.respiratoryRate,
    'temperature': vitalsMsg.skinTemperature,
    'batteryLevel': vitalsMsg.batteryLevel,
    'signalQuality': vitalsMsg.signalQuality,
    'impedance': approximateImpedance if vitalsMsg.signalQuality is not None else None
}

alerts = await alertDetectionService.detectAlerts(vitalsDict, patientId, deviceId)
```

**BUT:** This only detects basic vitals alerts (tachycardia, bradycardia, hypoxia, etc.)

**NOT DETECTING:**
- Arrhythmia (requires ECG analysis)
- Seizures (requires EEG analysis)
- Advanced cardiac events (requires QRS/QT analysis)

---

## Solution Required

We need to implement **waveform caching** so backend can:

1. **Cache waveforms** when `/stream` messages arrive (every 100ms)
2. **Use cached waveform** when `/vitals` messages arrive (every 1 second)
3. **Run analysis** on cached waveform
4. **Attach analysis results** to vitals message
5. **Store everything together** in `vitals_realtime` table

### Implementation Plan:

#### 1. Add waveform cache to `MQTTService.__init__()` (line 38):
```python
def __init__(self):
    # ... existing code ...

    # ✅ NEW: Waveform cache for ECG/EEG analysis
    # ESP32 sends /stream (waveforms) and /vitals (basic vitals) as SEPARATE messages
    # Cache waveforms when /stream arrives, use when /vitals arrives to run analysis
    self.waveformCache: Dict[str, Dict[str, Any]] = {}  # deviceId -> {waveform, timestamp, mode}
```

#### 2. Cache waveforms in `_handleWaveformStream()` (after line 279):
```python
async def _handleWaveformStream(self, deviceId: str, payload: Dict[str, Any]):
    # ... existing validation ...

    # ✅ NEW: Cache waveform for analysis when vitals arrive
    self.waveformCache[deviceId] = {
        'waveform': payload,
        'timestamp': datetime.now(),
        'mode': payload.get('mode')
    }

    # ... existing WebSocket broadcast & storage ...
```

#### 3. Use cached waveform in `_handleVitalsMessageNew()` (replace lines 477-530):
```python
# ========================================
# RUN ECG/EEG ANALYSIS (using cached waveform from /stream)
# ========================================
# Check for cached waveform (from /stream messages sent every 100ms)
cachedWaveform = self.waveformCache.get(deviceId)

if cachedWaveform:
    cacheAge = (datetime.now() - cachedWaveform['timestamp']).total_seconds()

    # Use waveform if < 2 seconds old and mode matches
    if cacheAge < 2.0 and cachedWaveform['mode'] == vitalsMsg.mode:
        waveformData = cachedWaveform['waveform']

        if vitalsMsg.mode == 'ecg' and 'ecgWaveform' in waveformData:
            logger.info(f"🧠 Running ECG analysis for patient {patientId}...")
            analysisResult = ecgAnalysisService.analyzeECG(waveformData['ecgWaveform'], mode='ecg')

            if analysisResult and analysisResult.confidence > 0.5:
                from ..models.neural_vitals import ECGAnalysis
                vitalsMsg.ecgAnalysis = ECGAnalysis(
                    rrInterval=analysisResult.rrInterval,
                    qrsDuration=analysisResult.qrsDuration,
                    qtInterval=analysisResult.qtInterval,
                    axis=analysisResult.axis,
                    rhythm=analysisResult.rhythm,
                    stSegment=analysisResult.stSegment
                )

        elif vitalsMsg.mode == 'eeg' and 'eegWaveform' in waveformData:
            logger.info(f"🧠 Running EEG analysis for patient {patientId}...")
            analysisResult = eegAnalysisService.analyzeEEG(waveformData['eegWaveform'], mode='eeg')

            if analysisResult and analysisResult.confidence > 0.5:
                from ..models.neural_vitals import EEGAnalysis, EEGBandPowers
                vitalsMsg.eegAnalysis = EEGAnalysis(
                    bandPowers=EEGBandPowers(
                        alpha=analysisResult.alphaPower,
                        beta=analysisResult.betaPower,
                        theta=analysisResult.thetaPower,
                        delta=analysisResult.deltaPower,
                        gamma=analysisResult.gammaPower or 0
                    ),
                    dominantFrequency=analysisResult.dominantFrequency,
                    seizureActivity=analysisResult.seizureActivity
                )

                # Critical: Seizure detection
                if analysisResult.seizureActivity and analysisResult.seizureConfidence > 0.7:
                    await self._createSeizureAlert(patientId, deviceId, analysisResult)

# Store vitals WITH analysis
await self._storeVitalsRealtime(vitalsMsg)
```

---

## Expected Results After Fix

### Backend Logs Will Show:
```
📨 MQTT STREAM MESSAGE RECEIVED: hospital/devices/fit-00001/stream
   Payload keys: ['deviceId', 'patientId', 'ecgWaveform', ...]
   ✅ Cached waveform for fit-00001 (age: 0.05s)

📨 MQTT VITALS MESSAGE RECEIVED: hospital/devices/fit-00001/vitals
   🧠 Running ECG analysis for patient 081a5294... (using cached waveform, age: 0.12s)
   ✅ ECG Analysis: HR=89 BPM, Rhythm=sinus, QRS=85ms, Confidence=0.87
   📊 8CH Vitals processed with ECG metrics
```

### Frontend Tooltip Will Show:
```
ECG Metrics:
RR: 780ms
QRS: 85ms
QT: 380ms
Axis: Normal
Rhythm: Sinus
ST: Normal
```

### Alerts Will Work:
- Arrhythmia detection (AFib, VTach, etc.)
- Seizure detection
- ST-segment elevation/depression alerts

---

## Files to Modify

1. **[mqtt_service.py](c:/Users/Srika/OneDrive/Desktop/hospital-management-system/hospital-backend/app/services/mqtt_service.py)**
   - Line 38: Add `self.waveformCache` to `__init__()`
   - Line 251-319: Update `_handleWaveformStream()` to cache waveforms
   - Line 477-530: Replace with waveform cache logic in `_handleVitalsMessageNew()`

---

## Next Steps

1. Implement waveform caching as documented above
2. Restart backend to apply changes
3. Verify logs show "🧠 Running ECG analysis..." messages
4. Test frontend tooltip shows actual metrics
5. Verify alerts are generated for abnormal rhythms

---

## Related Files

- [mqtt_service.py:251](c:/Users/Srika/OneDrive/Desktop/hospital-management-system/hospital-backend/app/services/mqtt_service.py#L251) - Stream handler
- [mqtt_service.py:450](c:/Users/Srika/OneDrive/Desktop/hospital-management-system/hospital-backend/app/services/mqtt_service.py#L450) - Vitals handler
- [PatientCardWaveform.tsx:91](c:/Users/Srika/OneDrive/Desktop/hospital-management-system/hospital-display-app/src/components/PatientCard/PatientCardWaveform.tsx#L91) - Tooltip rendering
- [ecg_analysis_service.py](c:/Users/Srika/OneDrive/Desktop/hospital-management-system/hospital-backend/app/services/ecg_analysis_service.py) - ECG analysis
- [eeg_analysis_service.py](c:/Users/Srika/OneDrive/Desktop/hospital-management-system/hospital-backend/app/services/eeg_analysis_service.py) - EEG analysis
