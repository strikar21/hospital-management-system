# Backend Waveform Cache Fix - Implementation Plan

## Problem
ESP32 sends vitals and waveforms as SEPARATE MQTT messages:
- `/vitals` topic: Basic vitals (HR, SpO2, temp) - NO waveform data
- `/stream` topic: Waveform data only - NO vitals

Our current code only analyzes waveforms when they're included WITH vitals in the same message. Since ESP32 sends them separately, analysis never runs.

## Solution
Add a **waveform cache** in the backend:
1. When `/stream` message arrives → Cache the waveform data (per device)
2. When `/vitals` message arrives → Use cached waveform (if recent) to run analysis
3. Attach analysis results to vitals before storing

## Implementation

### Step 1: Add Waveform Cache to MQTTService
```python
class MQTTService:
    def __init__(self):
        # ... existing code ...
        self.waveformCache: Dict[str, Dict[str, Any]] = {}  # deviceId -> {waveform, timestamp}
```

### Step 2: Cache Waveforms in _handleWaveformStream()
```python
async def _handleWaveformStream(self, deviceId: str, payload: Dict[str, Any]):
    # ... existing validation ...

    # Cache waveform for analysis when vitals arrive
    self.waveformCache[deviceId] = {
        'waveform': payload,
        'timestamp': datetime.now(),
        'mode': payload.get('mode')
    }

    # ... existing WebSocket broadcast ...
```

### Step 3: Use Cached Waveform in _handleVitalsMessageNew()
```python
async def _handleVitalsMessageNew(self, deviceId: str, payload: Dict[str, Any]):
    # ... existing validation ...

    # Check for cached waveform (from /stream messages)
    cachedWaveform = self.waveformCache.get(deviceId)
    if cachedWaveform:
        # Check if cache is recent (< 2 seconds old)
        cacheAge = (datetime.now() - cachedWaveform['timestamp']).total_seconds()

        if cacheAge < 2.0 and cachedWaveform['mode'] == vitalsMsg.mode:
            # Use cached waveform for analysis
            waveformData = cachedWaveform['waveform']

            if vitalsMsg.mode == 'ecg' and 'ecgWaveform' in waveformData:
                # Run ECG analysis
                analysisResult = ecgAnalysisService.analyzeECG(waveformData['ecgWaveform'], mode='ecg')

                if analysisResult and analysisResult.confidence > 0.5:
                    vitalsMsg.ecgAnalysis = ECGAnalysis(...)

            elif vitalsMsg.mode == 'eeg' and 'eegWaveform' in waveformData:
                # Run EEG analysis
                analysisResult = eegAnalysisService.analyzeEEG(waveformData['eegWaveform'], mode='eeg')

                if analysisResult and analysisResult.confidence > 0.5:
                    vitalsMsg.eegAnalysis = EEGAnalysis(...)

    # Store vitals WITH analysis
    await self._storeVitalsRealtime(vitalsMsg)
```

## Benefits
- Works with ESP32's current message format (no firmware changes needed)
- Backend does all the analysis (correct architecture)
- Uses most recent waveform data for accurate analysis
- 2-second cache timeout prevents stale data

## Testing
1. ESP32 sends `/stream` (waveform) every 100ms
2. ESP32 sends `/vitals` (basic vitals) every 1 second
3. Backend caches waveforms
4. When vitals arrive, backend uses latest cached waveform
5. Backend runs analysis and stores WITH vitals in same row
6. Frontend tooltip shows metrics!

## Files to Modify
- `hospital-backend/app/services/mqtt_service.py`
  - Add `waveformCache` dict to `__init__`
  - Modify `_handleWaveformStream()` to cache waveforms
  - Modify `_handleVitalsMessageNew()` to use cached waveforms

