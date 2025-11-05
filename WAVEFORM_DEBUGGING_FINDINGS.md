# Waveform Data Flow Debugging - Root Cause Found

## Status: MQTT Data is CORRECT ✅

### Investigation Summary

User reported waveforms not displaying despite vitals working. Through systematic investigation, we found:

**What Works:**
- ✅ ESP32 v5.2.5 sending delta-encoded waveforms correctly
- ✅ Database storage working (9,105+ waveforms stored with correct format)
- ✅ MQTT broker receiving messages (10 msg/sec)
- ✅ Backend MQTT service receiving and parsing messages correctly
- ✅ WebSocket connection exists and subscriptions work
- ✅ Vitals working fine (using different code path)

**The Problem:**
- ❌ Frontend receiving waveform WebSocket messages but with `ecgWaveform.limb` as empty object `{}`
- ❌ Browser console shows 0 samples buffered
- ❌ No waveforms rendering on screen

## Actual Data Structure (Confirmed via Debug Logging)

### MQTT Payload Received by Backend:
```
Payload keys: ['deviceId', 'patientId', 'timestamp', 'mode', 'sequence', 'duration', 'sampleRate', 'ecgWaveform']

ecgWaveform structure:
  type: <class 'dict'>
  keys: ['limb', 'precordial', 'derived']

  limb:
    type: <class 'dict'>
    keys: ['leadI', 'leadII', 'leadIII']

    leadI:
      type: <class 'dict'>
      keys: ['baseline', 'deltas']
      sample: baseline=8388640, deltas_len=49
```

**This is PERFECT!** ESP32 is sending exactly what we expect.

## Next Investigation Steps

The data is correct at MQTT level, but arriving empty at frontend. The issue must be in:

1. **Backend WebSocket Broadcasting** - Check [websocket_manager.py:sendWaveformStream()](websocket_manager.py)
   - Does `processWaveformData()` properly preserve the nested structure?
   - Is JSON serialization stripping the nested objects?

2. **Frontend WebSocket Reception** - Check [WebSocketService.ts:_routeMessage()](WebSocketService.ts)
   - Is the message being parsed correctly?
   - Is the data structure being preserved through deserialization?

3. **Frontend Data Extraction** - Check [useECGViewer.ts:handleWaveformStream()](useECGViewer.ts)
   - Is the hook properly accessing `waveformData.ecgWaveform.limb.leadI`?
   - Is delta decoding happening correctly?

## Debug Logging Added

### Backend (mqtt_service.py:705-727)
Added detailed structural inspection of MQTT payload showing exact keys and data types at each level.

### Frontend (useECGViewer.ts:115-130)
Added logging to show structure of `ecgWaveform.limb` object received via WebSocket.

##Next Action

Need to add logging to `websocket_manager.py` `sendWaveformStream()` function to see if the data is being correctly passed to WebSocket clients.
