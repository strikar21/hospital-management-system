# Waveform Display Issue - Root Cause Investigation Status

## Investigation Complete - Awaiting Browser Console Output

### What I Found Through Actual Research:

**Backend MQTT Payload (CONFIRMED via debug logs):**
```
✅ ESP32 sending CORRECT structure:
  - ecgWaveform.limb.leadI = {baseline: 8388640, deltas: [49 values]}
  - ecgWaveform.limb.leadII = {baseline: ..., deltas: [...]}
  - ecgWaveform.limb.leadIII = {baseline: ..., deltas: [...]}
```

**Backend WebSocket Message Structure (from code analysis):**
```python
# websocket_manager.py:206-214
processed = waveformData.copy()  # Contains all MQTT fields
processed['ecgWaveform'] = processedECG

data = {
  'type': 'waveformStream',
  'patientId': ...,
  'deviceId': ...,
  'timestamp': ...,
  'waveform': processed  # ← Nested!
}
```

So backend sends:
```json
{
  "type": "waveformStream",
  "waveform": {
    "deviceId": "fit-00001",
    "patientId": "...",
    "mode": "ecg",
    "sequence": 123,
    "sampleRate": 500,
    "duration": 0.1,
    "ecgWaveform": {
      "limb": {
        "leadI": {baseline: ..., deltas: [...]},
        "leadII": {...},
        "leadIII": {...}
      }
    }
  }
}
```

**Frontend Code (from actual file read):**
```typescript
// useECGViewer.ts:109
const waveformData = message.waveform;  // ✅ Correctly extracts 'waveform'

// useECGViewer.ts:140
if (waveformData.ecgWaveform) {  // ✅ Should work if structure is correct
  const { limb, precordial, derived } = waveformData.ecgWaveform;
  ...
}
```

## The Mystery:

Frontend code looks CORRECT. Backend code looks CORRECT. ESP32 data is CORRECT.

But browser console showed `ecgWaveform.limb` arriving as EMPTY `{}`.

## Debug Logging Added:

**Frontend (useECGViewer.ts:115-132):**
```typescript
logger.log('🔍 [DEBUG] Waveform data keys:', Object.keys(waveformData));
logger.log('🔍 [DEBUG] Has ecgWaveform?', 'ecgWaveform' in waveformData);

if (waveformData.ecgWaveform?.limb) {
  logger.log('🔍 [DEBUG] ECG limb structure:', {...});
} else {
  logger.warn('🔍 [DEBUG] NO ecgWaveform.limb found! waveformData:', waveformData);
}
```

**Backend (mqtt_service.py:705-727) - REMOVED SPAM:**
Confirmed MQTT payload structure, then removed excessive logging.

## Next Step:

**CHECK BROWSER CONSOLE** to see output from the new frontend logging:
1. What are the actual keys in `waveformData`?
2. Does `ecgWaveform` exist in `waveformData`?
3. If yes, what's inside it?
4. If no, what DOES `waveformData` contain?

This will reveal where the data is getting lost between backend WebSocket and frontend reception.

## Possible Causes (Hypotheses):

1. **JSON Serialization Issue** - Python dict → JSON → TypeScript might be stripping nested objects
2. **WebSocket Message Parsing** - Frontend WebSocket service might be transforming the message
3. **Type Mismatch** - Pydantic model might be changing the structure during validation
4. **Field Name Issue** - camelCase conversion or field renaming somewhere in the chain

All hypotheses can be eliminated once we see the actual browser console output showing what keys exist in `waveformData`.
