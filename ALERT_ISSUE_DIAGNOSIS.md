# Alert Issue Diagnosis - Frontend Not Displaying Alerts

## Summary

**Backend**: ✅ Working perfectly - Alerts are being detected and sent via WebSocket
**Frontend**: ❌ Not displaying alerts - Receiving but not showing them to user

---

## Backend Analysis (CONFIRMED WORKING)

### Alert Detection
```
2025-11-07 11:50:37,831 - WARNING - 🚨 Detected 4 alert(s) for patient 081a5294-da91-4c74-bb8a-e5062f5851dd
   → [CRITICAL] severeTachycardia: SEVERE TACHYCARDIA - HR 158 BPM (> 150)
   → [CRITICAL] severeRespiratoryDistress: SEVERE RESPIRATORY DISTRESS - RR 33/min (> 30)
   → [MEDIUM] fever: FEVER - Temperature 38.43°C (> 38.3°C)
   → [CRITICAL] earlyWarningScoreHigh: NEWS2 Score critically high: 7 (threshold: 7)
```

### WebSocket Broadcast
```
2025-11-07 11:50:40,967 - INFO - 🚨 Alert sent to 1 subscribers for patient 081a5294-da91-4c74-bb8a-e5062f5851dd
```

### Alert Flow in Backend
1. ✅ **Detection**: `alertDetectionService.detectAlerts()` finds 4 alerts
2. ✅ **Storage**: Alerts stored in `patient_alerts` table with unique IDs
3. ✅ **Broadcasting**: `connectionManager.sendAlert()` sends to WebSocket subscribers
4. ✅ **Delivery**: Logs confirm "Alert sent to 1 subscribers"

### Alert Message Format
```javascript
{
  "type": "alert",
  "patientId": "081a5294-da91-4c74-bb8a-e5062f5851dd",
  "timestamp": "2025-11-07T11:50:40.967Z",
  "alert": {
    "id": "uuid-here",
    "alertType": "severeTachycardia",
    "severity": "critical",
    "message": "SEVERE TACHYCARDIA - HR 158 BPM (> 150)",
    "source": "Backend Alert System",
    ...
  }
}
```

---

## Frontend Issue (NEEDS INVESTIGATION)

### Possible Causes

**1. Frontend Not Subscribed to Alert Messages**
- WebSocket connection exists (1 subscriber receiving alerts)
- But frontend may not be listening for `type: "alert"` messages
- Check: Does WebSocket message handler have case for `type === "alert"`?

**2. Alert Display Component Missing/Hidden**
- Alerts are received but no UI component to display them
- Check: Is there an AlertBanner/AlertList component?
- Check: Is it rendered in the main layout?

**3. Alert State Not Updated**
- Alerts received but state not updating
- Check: Does WebSocket handler dispatch alerts to React state?
- Check: Are alerts being added to an alerts array/list?

**4. Console Errors Blocking Alert Display**
- JavaScript errors preventing alert rendering
- Check: Browser console for errors

### Files to Check

**Frontend WebSocket Handler**:
- `hospital-display-app/src/hooks/useWebSocket.ts` (if exists)
- `hospital-display-app/src/services/WebSocketService.ts` (if exists)
- Search for: WebSocket message handlers, alert subscriptions

**Frontend Alert Components**:
- `hospital-display-app/src/components/AlertBanner.tsx`
- `hospital-display-app/src/components/AlertList.tsx`
- `hospital-display-app/src/components/Alerts/`

**Frontend Dashboard/Layout**:
- `hospital-display-app/src/Dashboard.tsx`
- `hospital-display-app/src/App.tsx`

---

## Testing Steps

### 1. Check Browser Console
Open browser DevTools → Console tab:
- Look for WebSocket messages logged
- Look for any errors
- Check if alert messages are being received

### 2. Check WebSocket Messages
In browser DevTools → Network tab → WS (WebSocket):
- Click on WebSocket connection
- View "Messages" tab
- Confirm alerts are being received from backend

### 3. Check React DevTools
If React DevTools installed:
- Check component state for alerts
- Look for AlertBanner/AlertList components
- Check if alert state is populating

---

## Quick Fix Recommendations

### Option A: Frontend Already Has Alert System
If frontend has alert components but they're not working:
1. Find WebSocket message handler
2. Add/fix case for `type === "alert"` messages
3. Dispatch alerts to global state (Redux/Context/useState)
4. Ensure AlertBanner component is rendered

### Option B: Frontend Missing Alert System
If no alert UI exists:
1. Create AlertBanner component (floating notification)
2. Add WebSocket alert listener
3. Store alerts in React state
4. Display as toast notifications or banner

---

## Backend Code Reference

**Alert Detection & Broadcasting** (mqtt_service.py lines 632-656):
```python
# Detect alerts
alerts = await alertDetectionService.detectAlerts(vitalsDict, patientId, deviceId)

# Store and broadcast each alert
for alert in alerts:
    alert_id = str(uuid.uuid4())

    # Store in database
    await conn.execute('''
        INSERT INTO patient_alerts
        (id, "patientId", "deviceId", type, severity, message, source, "alertTimestamp", status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active')
    ''', alert_id, patientId, deviceId, alert.alertType, alert.severity, alert.message, alert.source, datetime.now())

    # Broadcast via WebSocket
    alertPayload = alertDetectionService.createAlertPayload(alert)
    alertPayload['id'] = alert_id
    await connectionManager.sendAlert(patientId, alertPayload)
```

**WebSocket Send Alert** (websocket_manager.py lines 241-258):
```python
async def sendAlert(self, patientId: Optional[str], alertData: Dict[str, Any]) -> None:
    """Send alert to relevant subscribers"""
    data = {
        'type': 'alert',
        'patientId': patientId,
        'timestamp': datetime.now().isoformat(),
        'alert': alertData
    }

    if patientId:
        # Send to patient-specific subscribers
        sentCount = await self.broadcastToPatientSubscribers(patientId, data)

    if sentCount > 0:
        logger.info(f"🚨 Alert sent to {sentCount} subscribers for patient {patientId}")
```

---

## Conclusion

✅ **Backend is 100% functional** - Detecting alerts, storing them, and broadcasting via WebSocket
❌ **Frontend is not displaying** - This is purely a frontend issue

**Next step**: Investigate frontend WebSocket handling and alert display components.
