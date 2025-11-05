# Calibration Pulse Request Research Plan

## Issue
"now calibration pulse request doesnt come to the watch ever"

## Research Questions

1. **What is the calibration pulse request flow?**
   - Frontend → Backend → MQTT → ESP32?
   - Direct frontend → ESP32?
   - What topic/endpoint is used?

2. **Where is calibration pulse triggered?**
   - Frontend button/UI?
   - Backend automatic trigger?
   - When should it happen?

3. **How does ESP32 receive calibration requests?**
   - MQTT topic subscription?
   - HTTP endpoint?
   - WebSocket message?

4. **What did we change recently that might have broken this?**
   - ESP32 mode switching code (v5.2.12)?
   - Backend MQTT changes?
   - Frontend WebSocket changes?

5. **Was calibration pulse working before?**
   - Check old documentation
   - Check git history
   - Find when it last worked

## Research Steps

1. Search for "calibration" in ESP32 code
2. Search for "calibration" in backend code
3. Search for "calibration" in frontend code
4. Check MQTT topic subscriptions in ESP32
5. Check if ESP32 is subscribing to the right topics
6. Check backend MQTT publishing for calibration commands
7. Check frontend UI for calibration button/trigger
8. Check recent git changes that might have affected this

## Files to Check

### ESP32:
- `esp32_hospital_watch_complete.ino` - MQTT subscriptions, calibration handling

### Backend:
- `app/services/mqtt_service.py` - MQTT publishing
- `app/api/v1/device_management.py` - Device commands endpoint
- `app/api/v1/websocket.py` - WebSocket commands

### Frontend:
- `src/components/ECGViewer/` - ECG viewer calibration button
- `src/hooks/useECGViewer.ts` - Calibration trigger logic
- `src/services/WebSocketService.ts` - WebSocket command sending

## Next Steps

After research, determine:
1. Where the calibration flow is broken
2. What changed to break it
3. Root cause of the issue
4. Proper fix (no quick fixes!)
