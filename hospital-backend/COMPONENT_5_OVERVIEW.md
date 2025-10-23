# Component 5: Device Maintenance Alerts - Overview

**Status:** 🔄 PLANNING
**Estimated Complexity:** HIGH (5-7 days)
**Alert Count:** 9 alerts
**Target Progress:** 104 → 113 alerts (76% of 148 total)

---

## Overview

Component 5 implements device health and maintenance monitoring alerts to ensure ESP32 watches and other medical devices remain operational and accurate. This component tracks calibration status, battery health, connectivity patterns, and sensor accuracy over time.

**Key Challenge:** Requires new infrastructure for device calibration tracking, maintenance scheduling, and historical device performance analysis.

---

## Proposed Alerts (9 Total)

### Battery & Power Management (3 alerts)

#### 1. **criticalBatteryLevel**
- **Trigger:** Device battery <10%
- **Severity:** High
- **Purpose:** Prevent device shutdown during patient monitoring
- **Implementation:** Check battery level from device heartbeat/vitals data

#### 2. **lowBatteryWarning**
- **Trigger:** Device battery <20%
- **Severity:** Medium
- **Purpose:** Proactive warning before critical level
- **Implementation:** Check battery level from device heartbeat/vitals data

#### 3. **batteryDegradation**
- **Trigger:** Battery draining >2x faster than baseline
- **Severity:** Medium
- **Purpose:** Detect battery aging or hardware issues
- **Implementation:** Compare current drain rate to device baseline
- **Requires:** Historical battery tracking

### Calibration & Accuracy (3 alerts)

#### 4. **calibrationRequired**
- **Trigger:** Device not calibrated in >30 days
- **Severity:** High
- **Purpose:** Ensure measurement accuracy per medical standards
- **Implementation:** Track last calibration date per device
- **Requires:** Device calibration tracking table

#### 5. **calibrationOverdue**
- **Trigger:** Device not calibrated in >45 days
- **Severity:** Critical
- **Purpose:** Prevent use of uncalibrated devices
- **Implementation:** Track last calibration date, escalate from calibrationRequired
- **Requires:** Device calibration tracking table

#### 6. **sensorDrift**
- **Trigger:** Sensor readings consistently outside expected range vs. baseline
- **Severity:** High
- **Purpose:** Detect sensor degradation requiring recalibration
- **Implementation:** Statistical analysis of sensor readings vs. device baseline
- **Requires:** Device baseline data, statistical analysis

### Connectivity & Reliability (3 alerts)

#### 7. **frequentDisconnects**
- **Trigger:** >5 disconnections in 24 hours
- **Severity:** Medium
- **Purpose:** Identify faulty devices or connectivity issues
- **Implementation:** Track disconnect events per device
- **Requires:** Connection event logging

#### 8. **deviceUnresponsive**
- **Trigger:** No response to backend commands for >5 minutes
- **Severity:** High
- **Purpose:** Detect device freeze/crash
- **Implementation:** Track last command acknowledgment time
- **Requires:** Command-response tracking

#### 9. **firmwareUpdateRequired**
- **Trigger:** Device firmware version < minimum required version
- **Severity:** Medium
- **Purpose:** Ensure security patches and feature compatibility
- **Implementation:** Compare device firmware version to required version
- **Requires:** Device firmware version tracking, version management system

---

## Required Infrastructure

### 1. Database Schema Extensions

#### New Table: `deviceCalibration`
```sql
CREATE TABLE deviceCalibration (
    calibrationId SERIAL PRIMARY KEY,
    deviceId TEXT NOT NULL,
    calibratedAt TIMESTAMP NOT NULL,
    calibratedBy TEXT,  -- Staff ID
    calibrationType TEXT,  -- 'full', 'sensor_specific', 'quick'
    sensorType TEXT,  -- 'heartRate', 'spo2', 'temperature', 'all'
    notes TEXT,
    expiresAt TIMESTAMP,  -- calibratedAt + 30 days
    FOREIGN KEY (deviceId) REFERENCES devices(id),
    FOREIGN KEY (calibratedBy) REFERENCES staff(id)
);
```

#### New Table: `deviceMaintenanceHistory`
```sql
CREATE TABLE deviceMaintenanceHistory (
    maintenanceId SERIAL PRIMARY KEY,
    deviceId TEXT NOT NULL,
    maintenanceType TEXT,  -- 'calibration', 'repair', 'battery_replacement', 'firmware_update'
    performedAt TIMESTAMP NOT NULL,
    performedBy TEXT,  -- Staff ID
    notes TEXT,
    nextMaintenanceDue TIMESTAMP,
    FOREIGN KEY (deviceId) REFERENCES devices(id),
    FOREIGN KEY (performedBy) REFERENCES staff(id)
);
```

#### New Table: `deviceBaselines`
```sql
CREATE TABLE deviceBaselines (
    baselineId SERIAL PRIMARY KEY,
    deviceId TEXT NOT NULL UNIQUE,
    batteryDrainRatePerHour FLOAT,  -- % per hour at normal usage
    averageHeartRateVariance FLOAT,
    averageSpO2Variance FLOAT,
    averageTemperatureVariance FLOAT,
    baselineCalculatedAt TIMESTAMP,
    baselineUpdatedAt TIMESTAMP,
    FOREIGN KEY (deviceId) REFERENCES devices(id)
);
```

#### Extend `devices` Table
```sql
ALTER TABLE devices ADD COLUMN firmwareVersion TEXT;
ALTER TABLE devices ADD COLUMN lastCalibrationDate TIMESTAMP;
ALTER TABLE devices ADD COLUMN calibrationDueDate TIMESTAMP;
ALTER TABLE devices ADD COLUMN batteryHealthPercentage INT;  -- 0-100, degrades over time
ALTER TABLE devices ADD COLUMN totalDisconnects INT DEFAULT 0;
ALTER TABLE devices ADD COLUMN lastCommandSentAt TIMESTAMP;
ALTER TABLE devices ADD COLUMN lastCommandAckAt TIMESTAMP;
```

### 2. New Services

#### `CalibrationService`
- Track calibration schedules
- Calculate calibration due dates
- Record calibration events
- Query overdue devices

#### `DeviceHealthService`
- Calculate battery drain rates
- Compare sensor readings to baselines
- Detect sensor drift
- Track device reliability metrics

#### `MaintenanceScheduler`
- Background task checking calibration status
- Generate maintenance alerts
- Track maintenance history

### 3. API Endpoints

#### Calibration Management
- `POST /api/v2/devices/{deviceId}/calibrate` - Record calibration
- `GET /api/v2/devices/calibration/overdue` - List overdue devices
- `GET /api/v2/devices/{deviceId}/calibration-history` - Get calibration history

#### Maintenance Tracking
- `POST /api/v2/devices/{deviceId}/maintenance` - Record maintenance
- `GET /api/v2/devices/{deviceId}/maintenance-history` - Get maintenance history
- `GET /api/v2/devices/maintenance/due` - List devices needing maintenance

#### Device Health
- `GET /api/v2/devices/{deviceId}/health` - Get device health metrics
- `GET /api/v2/devices/{deviceId}/baselines` - Get device baselines
- `POST /api/v2/devices/{deviceId}/baselines/recalculate` - Recalculate baselines

---

## Implementation Phases

### Phase 1: Database Schema (1 day)
- Create migration for new tables
- Extend devices table
- Add indexes for performance

### Phase 2: Basic Battery Alerts (1 day)
- Implement criticalBatteryLevel
- Implement lowBatteryWarning
- Simple battery level checks from existing data

### Phase 3: Calibration Infrastructure (2 days)
- CalibrationService implementation
- Calibration tracking endpoints
- calibrationRequired alert
- calibrationOverdue alert

### Phase 4: Device Health Analysis (2 days)
- DeviceHealthService implementation
- Baseline calculation logic
- batteryDegradation alert
- sensorDrift alert

### Phase 5: Connectivity Monitoring (1 day)
- Connection event tracking
- frequentDisconnects alert
- deviceUnresponsive alert
- firmwareUpdateRequired alert

---

## Complexity Analysis

### High Complexity Factors:

1. **Historical Data Requirements**
   - Need to track device performance over time
   - Statistical analysis for sensor drift detection
   - Baseline calculation algorithms

2. **New Domain Logic**
   - Medical device calibration standards
   - Battery health modeling
   - Sensor drift detection algorithms

3. **Multiple New Services**
   - CalibrationService
   - DeviceHealthService
   - MaintenanceScheduler

4. **API Surface Expansion**
   - 8+ new endpoints
   - Integration with existing device management

5. **Compliance Considerations**
   - Medical device calibration requirements (Indian standards)
   - Audit trail for calibration events
   - Maintenance documentation requirements

---

## Alternative Approach: Simplified Version

### Quick Win: Basic Device Health (2-3 days)

Implement only the **easy wins** without complex infrastructure:

#### Simple Alerts (5 alerts):
1. **criticalBatteryLevel** - Use existing battery data
2. **lowBatteryWarning** - Use existing battery data
3. **calibrationRequired** - Add lastCalibrationDate to devices, simple date check
4. **frequentDisconnects** - Count disconnects from existing connection tracking
5. **firmwareUpdateRequired** - Simple version comparison

**Skip for now:**
- batteryDegradation (requires historical tracking)
- calibrationOverdue (duplicate of calibrationRequired)
- sensorDrift (requires complex baseline analysis)
- deviceUnresponsive (requires command-response infrastructure)

This gets **5 alerts** (109/148 = 74%) with **minimal complexity**.

---

## Recommendation

Given the complexity of full Component 5, I recommend:

### Option A: Simplified Component 5 (2-3 days)
- Implement 5 basic device health alerts
- Skip complex infrastructure
- Gets to 109/148 (74%)
- Lower risk, faster delivery

### Option B: Full Component 5 (5-7 days)
- Implement all 9 alerts
- Build complete calibration & maintenance infrastructure
- Gets to 113/148 (76%)
- Production-grade device management
- Higher complexity and time investment

### Option C: Skip to Other Components
- Focus on remaining alert categories
- Return to device maintenance later
- Different risk/reward profile

---

## Decision Point

**Which approach would you like to take?**

1. **Simplified Component 5** (5 alerts, 2-3 days)
2. **Full Component 5** (9 alerts, 5-7 days)
3. **Skip Component 5** for now, move to other alerts

Let me know your preference and I'll create the detailed implementation plan.
