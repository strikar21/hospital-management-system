# WebSocket Message Not Received - Root Cause Analysis

## Problem
Frontend sends waveform calibration requests, but backend `handleClientMessage()` function is never called - NO debug logs appear.

## Evidence

### Frontend Logs (Working)
```
🔧 Waveform calibration requested for patient: 081a5294-da91-4c74-bb8a-e5062f5851dd
```
Frontend IS sending the WebSocket message with `triggerWaveformCalibration: true`.

### Backend Logs (Missing)
```
# Expected but NOT appearing:
🔵 DEBUG: Received WebSocket message: type=subscribePatient...
🔵 DEBUG: subscribePatient - patientId=081a5294..., triggerWaveformCalibration=...
```

Backend shows:
- ✅ WebSocket broadcasts OUT (waveforms to frontend)
- ❌ NO WebSocket messages IN (from frontend)
- ❌ `handleClientMessage()` function is NEVER called

## Code Analysis

### WebSocket Message Flow (websocket.py:64-67)
```python
# Handle incoming messages from client
async for data in websocket.iter_text():
    try:
        message = json.loads(data)
        await handleClientMessage(connectionId, message)  # <-- THIS IS NEVER REACHED
```

### Debug Logging Added (websocket.py:91-140)
```python
async def handleClientMessage(connectionId: str, message: Dict[str, Any]) -> None:
    """Handle incoming messages from WebSocket clients"""

    logger.info(f"🔵 DEBUG: Received WebSocket message: type={message.get('type')}, keys={list(message.keys())}")
    # ... 10+ debug log statements
```

**All debug logs are missing** → `handleClientMessage()` is NOT being executed → `iter_text()` is NOT receiving messages.

## Root Cause Hypothesis

**The WebSocket connection is ONE-WAY** - backend can send to frontend, but frontend messages are not being received by backend.

Possible causes:
1. **Client-side issue**: Frontend WebSocket is not actually sending messages (though logs say it is)
2. **Network/proxy issue**: Messages are being sent but not reaching backend
3. **Backend routing issue**: Messages arrive but are not routed to `iter_text()` loop
4. **Connection state issue**: Connection is established for outgoing but not incoming messages

## Diagnostic Plan

### Test 1: Add logging BEFORE message parsing
Add logs at the `iter_text()` level to confirm messages are received:

```python
# Line 64
async for data in websocket.iter_text():
    logger.info(f"🟢 RAW WebSocket message received: {data[:200]}")  # <-- NEW
    try:
        message = json.loads(data)
        logger.info(f"🟢 Parsed message: {message}")  # <-- NEW
        await handleClientMessage(connectionId, message)
```

If these logs appear → message IS received, parsing issue
If these logs DON'T appear → message NOT received by backend

### Test 2: Check frontend WebSocket send
Confirm frontend actually calls `ws.send()`:

```typescript
// WebSocketService.ts:239
this.ws?.send(JSON.stringify(message));
console.log(`📡 Message SENT to backend:`, JSON.stringify(message));  // <-- Verify this appears
```

### Test 3: Network inspection
Use browser DevTools → Network → WS tab → Check if message actually sent over network.

## Next Steps

1. Add raw message logging at `iter_text()` level
2. Restart backend
3. Test waveform calibration request from frontend
4. Check if `🟢 RAW WebSocket message received` appears in logs
5. Based on results, identify exact point of failure

## Files to Modify

`hospital-backend/app/api/v1/websocket.py:64-67` - Add logging before message parsing
