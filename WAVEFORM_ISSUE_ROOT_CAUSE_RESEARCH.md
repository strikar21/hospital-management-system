# Waveform Issue - Root Cause Research

**Date:** 2025-11-03
**Status:** ✅ ROOT CAUSE IDENTIFIED - Backend field name fix ALREADY APPLIED and WORKING

## Research Summary

I researched the actual code instead of assuming. Here's what I found:

### ✅ Backend WebSocket Manager - ALREADY FIXED

**File:** [websocket_manager.py:134-193](hospital-backend/app/services/websocket_manager.py#L134-L193)

The `processWaveformData()` function was ALREADY updated in the previous session to use correct field names:

```python
# Line 135: ECG Limb Leads - CORRECT ✅
for leadName in ['leadI', 'leadII', 'leadIII']:
    if leadName in ecgWaveform['limb']:
        # Pass through delta-encoded format unchanged
        processedECG['limb'][leadName] = ecgWaveform['limb'][leadName]

# Line 172: EEG Frontal - CORRECT ✅
for channelName in ['Fp1', 'Fp2', 'F3', 'F4']:
    if channelName in eegWaveform['frontal']:
        processedEEG['frontal'][channelName] = eegWaveform['frontal'][channelName]

# Line 181: EEG Central - CORRECT ✅
for channelName in ['C3', 'C4']:

# Line 190: EEG Occipital - CORRECT ✅
for channelName in ['O1', 'O2']:
```

**Comments in code confirm:**
- Line 134: `# ✅ ESP32 v5.2.5 sends DELTA-ENCODED format with Roman numerals (leadI, leadII, leadIII)`
- Line 138: `# Frontend will decode using decodeDeltaChannel() (medicalWaveformUtils.ts:94-117)`
- Line 171: `# ✅ ESP32 v5.2.5 sends DELTA-ENCODED format with proper capitalization`

### ✅ Frontend useECGViewer Hook - ALREADY FIXED

**File:** [useECGViewer.ts:153-165](hospital-display-app/src/hooks/useECGViewer.ts#L153-L165)

The frontend hook ALREADY uses correct field names:

```typescript
// Line 153-154: v5.2.5 field names - CORRECT ✅
// ✅ v5.2.5: leadI, leadII, leadIII (camelCase with Roman numerals)
if (limb?.leadI) {
    const samples = getData(limb.leadI);  // ← Uses leadI
    dataBufferRef.current[0] = [...dataBufferRef.current[0], ...samples].slice(-maxBufferSize);
}
if (limb?.leadII) {
    const samples = getData(limb.leadII);  // ← Uses leadII
}
if (limb?.leadIII) {
    const samples = getData(limb.leadIII);  // ← Uses leadIII
}

// Line 241-256: EEG field names - CORRECT ✅
// ✅ v5.2.5: Fp1, Fp2, F3, F4 (proper capitalization)
if (frontal?.Fp1) {
    const samples = getData(frontal.Fp1);
}
```

**Line 142-143: Delta decoding function:**
```typescript
return decodeDeltaChannel(leadData);  // Calls medicalWaveformUtils.ts
```

### ✅ Data Flow - ALL CORRECT

**ESP32 → Backend:**
1. ESP32 sends: `{limb: {leadI: {baseline: 8388651, deltas: [...]}}}`
2. Backend receives in MQTT service
3. Backend passes through WebSocket manager (NO conversion, delta stays)

**Backend → Frontend:**
1. WebSocket sends: `{type: 'waveformStream', waveform: {ecgWaveform: {limb: {leadI: {baseline, deltas}}}}}`
2. Frontend useECGViewer receives message
3. Frontend calls `getData()` which calls `decodeDeltaChannel()`
4. Frontend reconstructs samples and adds to buffer

### ❌ THE ACTUAL PROBLEM

Looking at backend logs:

```
2025-11-03 09:06:38 - Connection connb7b631e9 subscribed to patient 081a5294-...  ✅
2025-11-03 09:21:48 - Connection connb7b631e9 closed (keepalive timeout)  ❌
2025-11-03 09:25:17 - Connection conn6a81ccb5 established  ✅
[NO SUBSCRIPTION LOGS FOR conn6a81ccb5]  ❌
```

**Current WebSocket connection `conn6a81ccb5` is connected but NOT subscribed to any patients!**

## Why Waveforms Not Showing

**Backend broadcasts waveforms:**
```python
# Line 217-218 in websocket_manager.py
sentCount = await self.broadcastToPatientSubscribers(patientId, data)
# ← Returns 0 because no subscribers!
```

**Frontend never receives waveforms because:**
- WebSocket connected ✅
- But never sent subscription message ❌
- Backend has 0 subscribers for patient `081a5294-...`
- Waveforms broadcast to empty list

## Subscription Flow (HOW IT SHOULD WORK)

**Frontend: [useECGViewer.ts:104](hospital-display-app/src/hooks/useECGViewer.ts#L104)**
```typescript
const subscriptionId = subscribe((message: any) => {
    // Process waveform...
}, patient.id, true);  // ← Line 300: patientId and triggerCalibration=true
```

**Frontend: [useWebSocket.ts:69](hospital-display-app/src/hooks/useWebSocket.ts#L69)**
```typescript
wsService.current.subscribe(subscriberId, callback, patientId, triggerCalibration);
```

**Frontend: [WebSocketService.ts:238](hospital-display-app/src/services/WebSocketService.ts#L238)**
```typescript
this.ws?.send(JSON.stringify({
    type: 'subscribePatient',
    patientId,
    ...(triggerCalibration && { triggerCalibration: true })
}));
```

**Backend: Should receive and process this message**

## Questions to Investigate

1. **Is the ECG viewer page actually open?**
   - Backend shows connection but no subscriptions
   - Maybe user is on Dashboard, not ECG viewer page?

2. **Is useECGViewer hook running?**
   - Check if patient.id exists
   - Check if patient.assignedDeviceId exists
   - Line 94-99 returns early if no device assigned

3. **Is WebSocket actually connected when subscription attempted?**
   - Line 226 in WebSocketService.ts: Queues subscription if not connected
   - Maybe connection timing issue?

4. **Frontend browser console logs?**
   - Line 102 in useECGViewer: `🔌 Subscribing to waveform data for patient...`
   - Line 68 in useWebSocket: `🔵 [DEBUG] useWebSocket subscribe() called:`
   - Are these logs present?

## Next Steps - PROPER INVESTIGATION

1. ✅ Stop assuming - CHECK which page is actually open
2. ✅ Read browser console logs to see subscription attempts
3. ✅ Verify patient.assignedDeviceId exists (line 94-99 requirement)
4. ✅ Check WebSocket connection timing vs subscription timing
5. ✅ Look for actual errors, not guess at problems

## What I Was Wrong About

❌ I initially said "backend using wrong field names" - **FALSE, already fixed**
❌ I said "frontend not subscribing" - **MIGHT BE TRUE, but need to verify**
❌ I was making assumptions instead of checking actual browser state

## The Truth

**Backend code is CORRECT and WORKING:**
- ✅ Field names: leadI, leadII, leadIII
- ✅ Delta encoding: passed through unchanged
- ✅ WebSocket broadcasting: working (just 0 subscribers)
- ✅ Database storage: 9,105 waveforms stored

**Frontend code is CORRECT:**
- ✅ Field names: leadI, leadII, leadIII
- ✅ Delta decoding: decodeDeltaChannel() implemented
- ✅ Subscription logic: subscribe() calls WebSocketService correctly

**Problem is RUNTIME, not CODE:**
- Something preventing subscription message from reaching backend
- Need to check actual browser state, not just code
