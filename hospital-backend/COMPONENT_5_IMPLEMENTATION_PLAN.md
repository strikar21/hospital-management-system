# Component 5: Device Maintenance Alerts - Implementation Plan

**Status:** 🚀 IN PROGRESS
**Start Date:** October 15, 2025
**Target:** 9 alerts (104 → 113/148, 76%)
**Estimated Time:** 5-7 days

---

## Implementation Strategy

This component requires significant infrastructure before alert implementation. We'll build bottom-up: database → services → alerts → API.

---

## Phase 1: Database Schema & Migration (Day 1)

### Step 1.1: Create Migration 012
**File:** `migrations/012_device_maintenance_infrastructure.sql`

**Tables to Create:**

1. **deviceCalibration** - Calibration event tracking
2. **deviceMaintenanceHistory** - All maintenance events
3. **deviceBaselines** - Device-specific performance baselines

**Columns to Add to devices table:**
- `firmwareVersion` (TEXT)
- `lastCalibrationDate` (TIMESTAMP)
- `calibrationDueDate` (TIMESTAMP)
- `batteryHealthPercentage` (INT, 0-100)
- `totalDisconnects` (INT)
- `lastCommandSentAt` (TIMESTAMP)
- `lastCommandAckAt` (TIMESTAMP)

**Indexes to Create:**
- `idx_devicecalibration_deviceid` on deviceCalibration(deviceId)
- `idx_devicecalibration_expiresat` on deviceCalibration(expiresAt)
- `idx_devicemaintenance_deviceid` on deviceMaintenanceHistory(deviceId)
- `idx_devices_calibration_due` on devices(calibrationDueDate)
- `idx_devices_firmware` on devices(firmwareVersion)

### Step 1.2: Apply Migration
**File:** `apply_migration_012_maintenance.py`

- Connect to database
- Execute migration SQL
- Verify tables and columns created
- Log success/failure

**Estimated Time:** 2-3 hours

---

## Phase 2: Core Services (Day 2)

### Step 2.1: CalibrationService
**File:** `app/services/calibration_service.py`

**Purpose:** Manage device calibration tracking and scheduling

**Key Methods:**
```python
class CalibrationService:
    async def recordCalibration(deviceId, calibratedBy, calibrationType, sensorType, notes)
    async def getLastCalibration(deviceId)
    async def getCalibrationHistory(deviceId, limit=10)
    async def isCalibrationDue(deviceId, daysThreshold=30)
    async def getOverdueDevices(daysOverdue=45)
    async def calculateCalibrationDueDate(deviceId)
    async def getDevicesNeedingCalibration(daysThreshold=30)
```

**Business Logic:**
- Calibration expires after 30 days
- Auto-update `lastCalibrationDate` and `calibrationDueDate` in devices table
- Support different calibration types (full, sensor-specific, quick)

### Step 2.2: DeviceHealthService
**File:** `app/services/device_health_service.py`

**Purpose:** Calculate and track device health metrics

**Key Methods:**
```python
class DeviceHealthService:
    async def calculateBaseline(deviceId)
    async def getBaseline(deviceId)
    async def updateBaseline(deviceId)
    async def calculateBatteryDrainRate(deviceId)
    async def detectSensorDrift(deviceId, sensorType, currentReading)
    async def recordDisconnect(deviceId)
    async def getDisconnectCount(deviceId, timeWindowHours=24)
    async def updateBatteryHealth(deviceId, currentBatteryLevel)
    async def checkDeviceResponsiveness(deviceId)
```

**Business Logic:**
- Calculate baseline from last 7 days of vitals data
- Battery drain rate = (battery drop %) / (time hours)
- Sensor drift = statistical comparison to baseline (±2 standard deviations)
- Battery health degrades based on charge cycles and age

### Step 2.3: MaintenanceService
**File:** `app/services/maintenance_service.py`

**Purpose:** Track maintenance events and history

**Key Methods:**
```python
class MaintenanceService:
    async def recordMaintenance(deviceId, maintenanceType, performedBy, notes)
    async def getMaintenanceHistory(deviceId, limit=10)
    async def getDevicesDueMaintenance()
    async def scheduleNextMaintenance(deviceId, maintenanceType, daysUntilDue)
```

**Estimated Time:** 6-8 hours

---

## Phase 3: Battery Alerts (Day 3)

### Step 3.1: Basic Battery Monitoring
**File:** `app/services/alert_detection_service.py`

**Add Method:** `_detectBatteryAlerts()`

#### Alert 1: criticalBatteryLevel
```python
if batteryLevel and batteryLevel < 10:
    alerts.append(Alert(
        alertType='criticalBatteryLevel',
        severity='high',
        message=f'CRITICAL BATTERY - Device {deviceId} battery at {batteryLevel}%',
        source='Backend',
        confidence=1.0,
        patientId=patientId,
        deviceId=deviceId,
        timestamp=timestamp,
        context={'batteryLevel': batteryLevel},
        category='device'
    ))
```

#### Alert 2: lowBatteryWarning
```python
if batteryLevel and 10 <= batteryLevel < 20:
    alerts.append(Alert(
        alertType='lowBatteryWarning',
        severity='medium',
        message=f'LOW BATTERY - Device {deviceId} battery at {batteryLevel}%',
        source='Backend',
        confidence=0.95,
        patientId=patientId,
        deviceId=deviceId,
        timestamp=timestamp,
        context={'batteryLevel': batteryLevel},
        category='device'
    ))
```

### Step 3.2: Battery Degradation Detection
**Integration with DeviceHealthService**

#### Alert 3: batteryDegradation
```python
drainRate = await deviceHealthService.calculateBatteryDrainRate(deviceId)
baseline = await deviceHealthService.getBaseline(deviceId)

if baseline and drainRate > baseline.batteryDrainRatePerHour * 2:
    alerts.append(Alert(
        alertType='batteryDegradation',
        severity='medium',
        message=f'BATTERY DEGRADATION - Device {deviceId} draining 2x faster than normal',
        source='Backend',
        confidence=0.85,
        patientId=patientId,
        deviceId=deviceId,
        timestamp=timestamp,
        context={
            'currentDrainRate': drainRate,
            'baselineDrainRate': baseline.batteryDrainRatePerHour
        },
        category='device'
    ))
```

**Integration:** Call from `detectAlerts()` method

**Estimated Time:** 3-4 hours

---

## Phase 4: Calibration Alerts (Day 4-5)

### Step 4.1: Calibration Tracking Background Task
**File:** `app/services/calibration_monitor.py`

**Purpose:** Background task checking calibration status every hour

```python
class CalibrationMonitor:
    def __init__(self):
        self.isRunning = False
        self.checkIntervalSeconds = 3600  # 1 hour

    async def start(self)
    async def stop(self)
    async def _monitorLoop(self)
    async def _checkCalibrationStatus(self)
    async def _generateCalibrationAlert(deviceData, alertType)
```

**Startup Integration:** Add to `main.py` startup_event()

### Step 4.2: Calibration Required Alert

#### Alert 4: calibrationRequired
```python
devices = await calibrationService.getDevicesNeedingCalibration(daysThreshold=30)

for device in devices:
    daysSinceCalibration = (now - device.lastCalibrationDate).days

    alerts.append(Alert(
        alertType='calibrationRequired',
        severity='high',
        message=f'CALIBRATION REQUIRED - Device {device.id} not calibrated in {daysSinceCalibration} days',
        source='Backend',
        confidence=0.95,
        patientId=device.currentPatientId,
        deviceId=device.id,
        timestamp=datetime.now(),
        context={
            'daysSinceCalibration': daysSinceCalibration,
            'lastCalibrationDate': device.lastCalibrationDate.isoformat()
        },
        category='device'
    ))
```

#### Alert 5: calibrationOverdue
```python
devices = await calibrationService.getOverdueDevices(daysOverdue=45)

for device in devices:
    daysSinceCalibration = (now - device.lastCalibrationDate).days

    alerts.append(Alert(
        alertType='calibrationOverdue',
        severity='critical',
        message=f'CALIBRATION OVERDUE - Device {device.id} CRITICALLY overdue ({daysSinceCalibration} days)',
        source='Backend',
        confidence=1.0,
        patientId=device.currentPatientId,
        deviceId=device.id,
        timestamp=datetime.now(),
        context={
            'daysSinceCalibration': daysSinceCalibration,
            'lastCalibrationDate': device.lastCalibrationDate.isoformat()
        },
        category='device'
    ))
```

### Step 4.3: Sensor Drift Detection

#### Alert 6: sensorDrift
**Triggered during vitals processing**

```python
async def _detectSensorDriftAlerts(vitalsData, patientId, deviceId, timestamp):
    alerts = []
    baseline = await deviceHealthService.getBaseline(deviceId)

    if not baseline:
        return alerts

    # Check heart rate sensor
    if 'heartRate' in vitalsData:
        isDrift = await deviceHealthService.detectSensorDrift(
            deviceId, 'heartRate', vitalsData['heartRate']
        )
        if isDrift:
            alerts.append(Alert(
                alertType='sensorDrift',
                severity='high',
                message=f'SENSOR DRIFT - Device {deviceId} heart rate sensor showing abnormal variance',
                source='Backend',
                confidence=0.80,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'sensorType': 'heartRate'},
                category='device'
            ))

    # Similar checks for SpO2, temperature

    return alerts
```

**Estimated Time:** 6-8 hours

---

## Phase 5: Connectivity & Reliability Alerts (Day 6)

### Step 5.1: Connection Event Tracking

**Modify:** `app/services/mqtt_service.py` or `app/services/websocket_manager.py`

Add disconnect tracking:
```python
async def onDeviceDisconnect(deviceId):
    await deviceHealthService.recordDisconnect(deviceId)

    # Check for frequent disconnects
    disconnectCount = await deviceHealthService.getDisconnectCount(deviceId, timeWindowHours=24)

    if disconnectCount > 5:
        # Trigger frequentDisconnects alert
        await alertDetectionService.generateDeviceAlert(
            deviceId=deviceId,
            alertType='frequentDisconnects',
            severity='medium'
        )
```

#### Alert 7: frequentDisconnects
```python
alerts.append(Alert(
    alertType='frequentDisconnects',
    severity='medium',
    message=f'FREQUENT DISCONNECTS - Device {deviceId} disconnected {disconnectCount} times in 24 hours',
    source='Backend',
    confidence=0.90,
    patientId=patientId,
    deviceId=deviceId,
    timestamp=datetime.now(),
    context={'disconnectCount': disconnectCount},
    category='device'
))
```

### Step 5.2: Device Responsiveness Monitoring

**Background Task:** Check command acknowledgments

#### Alert 8: deviceUnresponsive
```python
async def _checkDeviceResponsiveness(self):
    devices = await getDevicesWithPendingCommands()

    for device in devices:
        if device.lastCommandSentAt and not device.lastCommandAckAt:
            timeSinceCommand = (datetime.now() - device.lastCommandSentAt).total_seconds() / 60

            if timeSinceCommand > 5:
                alerts.append(Alert(
                    alertType='deviceUnresponsive',
                    severity='high',
                    message=f'DEVICE UNRESPONSIVE - Device {device.id} not responding for {timeSinceCommand:.0f} minutes',
                    source='Backend',
                    confidence=0.85,
                    patientId=device.currentPatientId,
                    deviceId=device.id,
                    timestamp=datetime.now(),
                    context={'minutesUnresponsive': timeSinceCommand},
                    category='device'
                ))
```

### Step 5.3: Firmware Version Check

#### Alert 9: firmwareUpdateRequired
```python
MINIMUM_FIRMWARE_VERSION = "2.0.0"

devices = await getActiveDevices()

for device in devices:
    if device.firmwareVersion and compareVersions(device.firmwareVersion, MINIMUM_FIRMWARE_VERSION) < 0:
        alerts.append(Alert(
            alertType='firmwareUpdateRequired',
            severity='medium',
            message=f'FIRMWARE UPDATE REQUIRED - Device {device.id} running outdated firmware v{device.firmwareVersion}',
            source='Backend',
            confidence=0.95,
            patientId=device.currentPatientId,
            deviceId=device.id,
            timestamp=datetime.now(),
            context={
                'currentVersion': device.firmwareVersion,
                'minimumVersion': MINIMUM_FIRMWARE_VERSION
            },
            category='device'
        ))
```

**Estimated Time:** 5-6 hours

---

## Phase 6: API Endpoints (Day 7)

### Step 6.1: Calibration Endpoints
**File:** `app/api/v2/calibration.py`

**Endpoints:**
- `POST /api/v2/devices/{deviceId}/calibrate` - Record calibration
- `GET /api/v2/devices/calibration/overdue` - List overdue devices
- `GET /api/v2/devices/{deviceId}/calibration-history` - Calibration history

### Step 6.2: Maintenance Endpoints
**File:** `app/api/v2/maintenance.py`

**Endpoints:**
- `POST /api/v2/devices/{deviceId}/maintenance` - Record maintenance
- `GET /api/v2/devices/{deviceId}/maintenance-history` - Maintenance history
- `GET /api/v2/devices/maintenance/due` - Devices needing maintenance

### Step 6.3: Device Health Endpoints
**File:** `app/api/v2/device_health.py`

**Endpoints:**
- `GET /api/v2/devices/{deviceId}/health` - Health metrics
- `GET /api/v2/devices/{deviceId}/baselines` - Device baselines
- `POST /api/v2/devices/{deviceId}/baselines/recalculate` - Recalculate baselines

**Estimated Time:** 4-5 hours

---

## Testing Plan

### Unit Tests
- CalibrationService methods
- DeviceHealthService calculations
- Alert detection logic

### Integration Tests
- End-to-end calibration workflow
- Battery degradation detection with mock data
- Sensor drift detection with baseline data

### Manual Tests
- Calibration API endpoints
- Alert generation with real devices
- Background task execution

**Estimated Time:** 4-6 hours

---

## Implementation Checklist

### Phase 1: Database (Day 1)
- [ ] Create migration 012 SQL file
- [ ] Create migration application script
- [ ] Apply migration to database
- [ ] Verify tables and columns created
- [ ] Test indexes created

### Phase 2: Services (Day 2)
- [ ] Create CalibrationService
- [ ] Create DeviceHealthService
- [ ] Create MaintenanceService
- [ ] Write service unit tests
- [ ] Create singleton instances

### Phase 3: Battery Alerts (Day 3)
- [ ] Implement _detectBatteryAlerts() method
- [ ] Add criticalBatteryLevel alert
- [ ] Add lowBatteryWarning alert
- [ ] Add batteryDegradation alert
- [ ] Integrate into detectAlerts()
- [ ] Test with mock battery data

### Phase 4: Calibration Alerts (Day 4-5)
- [ ] Create CalibrationMonitor service
- [ ] Implement background monitoring task
- [ ] Add calibrationRequired alert
- [ ] Add calibrationOverdue alert
- [ ] Add sensorDrift alert
- [ ] Integrate monitor into main.py
- [ ] Test calibration alerts

### Phase 5: Connectivity Alerts (Day 6)
- [ ] Add disconnect tracking
- [ ] Implement frequentDisconnects alert
- [ ] Implement deviceUnresponsive alert
- [ ] Implement firmwareUpdateRequired alert
- [ ] Test connectivity alerts

### Phase 6: API Endpoints (Day 7)
- [ ] Create calibration endpoints
- [ ] Create maintenance endpoints
- [ ] Create device health endpoints
- [ ] Test all endpoints with Postman/curl
- [ ] Update API documentation

### Phase 7: Integration & Testing
- [ ] Integration testing
- [ ] End-to-end workflow testing
- [ ] Performance testing
- [ ] Create completion report

---

## Success Criteria

✅ **All 9 alerts implemented and functional**
✅ **Database schema created and migrated**
✅ **Services implemented and tested**
✅ **API endpoints operational**
✅ **Background tasks running**
✅ **Alert count: 113/148 (76%)**
✅ **Documentation complete**

---

## Risk Mitigation

### Risk 1: Baseline Calculation Complexity
**Mitigation:** Start with simple variance calculation, iterate if needed

### Risk 2: Historical Data Requirements
**Mitigation:** Use existing vitals data, extend gradually

### Risk 3: Indian Calibration Standards Unknown
**Mitigation:** Use conservative 30-day calibration cycle, adjust based on research

### Risk 4: Command-Response Infrastructure Missing
**Mitigation:** Implement basic command tracking, expand if needed

---

## Next Steps

Ready to start Phase 1: Database Schema & Migration?

**I'll begin by creating:**
1. Migration 012 SQL file
2. Migration application script
3. Applying migration to database

Proceed with Phase 1?
