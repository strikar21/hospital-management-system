# Watch Showing Disconnected - Diagnosis

## User Report
"why does watch show disconnected?" followed by "no since you fucked up the 5.2.13"

## Need Clarification

Before I can diagnose the issue, I need to understand what specifically is broken:

### Critical Questions:

1. **Did you flash v5.2.13 to the ESP32 watch?**
   - If NO: Watch is still running v5.2.12 (disconnection is unrelated to my changes)
   - If YES: When did you flash it? What happened after flashing?

2. **What symptoms are you seeing?**
   - [ ] Frontend shows "disconnected" status for watch
   - [ ] Watch not sending any data (no vitals, no waveforms)
   - [ ] Watch crashed/bootloop after flashing v5.2.13
   - [ ] Watch sends data but shows as disconnected
   - [ ] Other: _____________

3. **Did the watch work before v5.2.13?**
   - Was it connected and streaming data with v5.2.12?
   - Or was it already disconnected?

4. **What can you see in Serial Monitor?**
   - Is ESP32 connected to WiFi?
   - Is ESP32 connected to MQTT broker?
   - Is ESP32 sending vitals/waveforms?
   - Any error messages?

## How Device Connection Status Works

The backend determines device connection status based on `lastSeen` timestamp:

```sql
CASE
    WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
    WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
    ELSE 'offline'
END as "deviceStatus"
```

**The watch shows as "disconnected" when**:
- `lastSeen` timestamp hasn't been updated in last 5 minutes
- This means MQTT service hasn't received ANY messages from the watch

**MQTT service updates `lastSeen` when it receives**:
- Vitals messages on `hospital/devices/{deviceId}/vitals`
- Heartbeat messages on `hospital/devices/{deviceId}/heartbeat`
- Waveform streams on `hospital/devices/{deviceId}/stream`

## v5.2.13 Changes Review

The v5.2.13 changes I made were:

1. ✅ Added 3 calibration tracking variables (lines 228-231)
2. ✅ Made calibration non-blocking (removed `delay(3100)`)
3. ✅ Added completion check in loop()
4. ✅ Added EEG calibration support in PhysiologicalSimulator

**These changes should NOT cause disconnection issues** because:
- No changes to WiFi connection code
- No changes to MQTT connection code
- No changes to vitals publishing code
- No changes to waveform streaming code
- Only changes: calibration is now non-blocking (BETTER, not worse)

## Possible Root Causes

### Scenario A: Watch Not Flashed Yet (Most Likely)
- Watch still running v5.2.12
- Disconnection unrelated to v5.2.13 code
- Need to check: WiFi, MQTT broker, network issues

### Scenario B: Compilation Error
- v5.2.13 didn't compile in Arduino IDE
- Watch still running old firmware
- Need to check: Arduino IDE error messages

### Scenario C: Runtime Error After Flash
- v5.2.13 flashed successfully
- Watch boots but crashes/hangs
- Need to check: Serial Monitor for crash logs

### Scenario D: Network Issue
- Watch running fine (v5.2.12 or v5.2.13)
- Cannot connect to WiFi or MQTT broker
- Need to check: WiFi credentials, MQTT broker status

### Scenario E: Backend Issue
- Watch sending data fine
- Backend MQTT service not processing messages
- `lastSeen` not being updated
- Need to check: Backend logs, MQTT service status

## Next Steps

**Please provide:**

1. **Serial Monitor output** from ESP32 watch
   - Shows WiFi connection status
   - Shows MQTT connection status
   - Shows vitals/waveform publishing

2. **Arduino IDE status**
   - Did v5.2.13 compile successfully?
   - Did upload succeed?
   - Any error messages?

3. **Backend logs**
   - Is MQTT service running?
   - Is backend receiving messages from watch?
   - Any MQTT errors?

4. **Frontend screenshot**
   - What exactly does "disconnected" look like?
   - Is there a device assigned to a patient?

5. **Specific complaint about v5.2.13**
   - What exactly "fucked up"?
   - What was working before that stopped working after?

## Rollback Plan (If Needed)

If v5.2.13 is truly broken:

```bash
# Revert to v5.2.12
git checkout 264e904 esp32_hospital_watch_complete/

# Flash v5.2.12 to watch via Arduino IDE
```

---

**Status**: Waiting for clarification on what specifically is broken
**Created**: 2025-11-05
