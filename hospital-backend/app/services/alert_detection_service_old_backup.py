"""
Alert Detection Service - Phase 1 MVP
Detects life-threatening and critical alerts from ESP32 vitals data
STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case

Based on COMPREHENSIVE_ALERT_SYSTEM_DESIGN.md (148 alert types designed)
Phase 1 Implementation: Tier 1 Life-Threatening Alerts (~20 alert types)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Single alert instance"""
    alertType: str  # e.g., 'cardiacArrest', 'severeHypoxia'
    severity: str  # 'critical', 'high', 'medium', 'low'
    message: str  # Human-readable message
    source: str  # 'ESP32' or 'Backend'
    confidence: float  # 0.0 to 1.0
    patientId: str
    deviceId: str
    timestamp: datetime
    context: Dict[str, Any]  # Additional data (e.g., {'heartRate': 0, 'spO2': 85})
    category: str  # 'cardiac', 'respiratory', 'neurological', 'device', etc.


class AlertDetectionService:
    """
    Detects medical alerts from ESP32 vitals data

    Phase 1 MVP (Tier 1 - Life-Threatening):
    - Cardiac arrest (HR = 0)
    - Severe hypoxia (SpO2 < 85%)
    - Critical hypoxia (SpO2 < 80%)
    - Severe bradycardia (HR < 40)
    - Severe tachycardia (HR > 150)
    - Apnea (RR = 0 for 20+ sec)
    - Severe respiratory distress (RR > 30)
    - Severe respiratory depression (RR < 8)
    - Critical battery (<5%)
    - Lead off (electrode disconnected)
    - Watch removed (all leads off)
    - Hard fall (>3g impact)

    Future Phases:
    - Phase 2: Urgent Clinical (AFib, STEMI, moderate arrhythmias)
    - Phase 3: Advanced (Trend analysis, seizure detection, complex patterns)
    - Phase 4: Full System (All 148 alert types)
    """

    def __init__(self):
        # Cardiac thresholds
        self.severeBradycardiaThreshold = 40  # BPM
        self.severeTachycardiaThreshold = 150  # BPM
        self.cardiacArrestThreshold = 0  # BPM (no heartbeat)

        # Respiratory thresholds
        self.severeHypoxiaThreshold = 85  # SpO2 %
        self.criticalHypoxiaThreshold = 80  # SpO2 %
        self.apneaThreshold = 0  # RR (no breathing)
        self.severeRespiratoryDistressThreshold = 30  # RR breaths/min
        self.severeRespiratoryDepressionThreshold = 8  # RR breaths/min

        # Device health thresholds
        self.criticalBatteryThreshold = 5  # Battery %
        self.lowBatteryThreshold = 10  # Battery %

        logger.info("✅ Alert Detection Service initialized (Phase 1 MVP - Tier 1 Life-Threatening)")

    def detectAlerts(self, vitalsData: Dict[str, Any], patientId: str, deviceId: str) -> List[Alert]:
        """
        Detect all alerts from vitals data

        Args:
            vitalsData: Dictionary with vitals (heartRate, oxygenSaturation, respiratoryRate, etc.)
            patientId: Patient UUID
            deviceId: Device ID

        Returns:
            List of detected alerts (may be empty)
        """
        alerts = []
        timestamp = datetime.now()

        # Extract vitals with safe None handling
        heartRate = vitalsData.get('heartRate')
        spO2 = vitalsData.get('oxygenSaturation')
        respiratoryRate = vitalsData.get('respiratoryRate')
        batteryLevel = vitalsData.get('batteryLevel')
        signalQuality = vitalsData.get('signalQuality')

        # ========================================
        # CATEGORY 1: CARDIAC EMERGENCIES
        # ========================================

        # Cardiac Arrest (HR = 0 for 5+ sec)
        if heartRate is not None and heartRate == self.cardiacArrestThreshold:
            alerts.append(Alert(
                alertType='cardiacArrest',
                severity='critical',
                message='CARDIAC ARREST - No heartbeat detected',
                source='ESP32',
                confidence=1.0,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'heartRate': heartRate},
                category='cardiac'
            ))

        # Severe Bradycardia (HR < 40)
        elif heartRate is not None and heartRate > 0 and heartRate < self.severeBradycardiaThreshold:
            alerts.append(Alert(
                alertType='severeBradycardia',
                severity='critical',
                message=f'SEVERE BRADYCARDIA - Heart rate {heartRate} BPM (< {self.severeBradycardiaThreshold} BPM)',
                source='ESP32',
                confidence=0.95,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'heartRate': heartRate},
                category='cardiac'
            ))

        # Severe Tachycardia (HR > 150)
        elif heartRate is not None and heartRate > self.severeTachycardiaThreshold:
            alerts.append(Alert(
                alertType='severeTachycardia',
                severity='critical',
                message=f'SEVERE TACHYCARDIA - Heart rate {heartRate} BPM (> {self.severeTachycardiaThreshold} BPM)',
                source='ESP32',
                confidence=0.95,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'heartRate': heartRate},
                category='cardiac'
            ))

        # ========================================
        # CATEGORY 2: RESPIRATORY EMERGENCIES
        # ========================================

        # Critical Hypoxia (SpO2 < 80%)
        if spO2 is not None and spO2 < self.criticalHypoxiaThreshold:
            alerts.append(Alert(
                alertType='criticalHypoxia',
                severity='critical',
                message=f'CRITICAL HYPOXIA - SpO2 {spO2}% (< {self.criticalHypoxiaThreshold}%)',
                source='ESP32',
                confidence=1.0,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'oxygenSaturation': spO2},
                category='respiratory'
            ))

        # Severe Hypoxia (SpO2 < 85%)
        elif spO2 is not None and spO2 < self.severeHypoxiaThreshold:
            alerts.append(Alert(
                alertType='severeHypoxia',
                severity='critical',
                message=f'SEVERE HYPOXIA - SpO2 {spO2}% (< {self.severeHypoxiaThreshold}%)',
                source='ESP32',
                confidence=0.95,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'oxygenSaturation': spO2},
                category='respiratory'
            ))

        # Apnea (RR = 0 for 20+ sec)
        if respiratoryRate is not None and respiratoryRate == self.apneaThreshold:
            alerts.append(Alert(
                alertType='apnea',
                severity='critical',
                message='APNEA - No breathing detected',
                source='ESP32',
                confidence=1.0,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'respiratoryRate': respiratoryRate},
                category='respiratory'
            ))

        # Severe Respiratory Distress (RR > 30)
        elif respiratoryRate is not None and respiratoryRate > self.severeRespiratoryDistressThreshold:
            alerts.append(Alert(
                alertType='severeRespiratoryDistress',
                severity='critical',
                message=f'SEVERE RESPIRATORY DISTRESS - RR {respiratoryRate} breaths/min (> {self.severeRespiratoryDistressThreshold}/min)',
                source='ESP32',
                confidence=0.9,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'respiratoryRate': respiratoryRate},
                category='respiratory'
            ))

        # Severe Respiratory Depression (RR < 8)
        elif respiratoryRate is not None and respiratoryRate > 0 and respiratoryRate < self.severeRespiratoryDepressionThreshold:
            alerts.append(Alert(
                alertType='severeRespiratoryDepression',
                severity='critical',
                message=f'SEVERE RESPIRATORY DEPRESSION - RR {respiratoryRate} breaths/min (< {self.severeRespiratoryDepressionThreshold}/min)',
                source='ESP32',
                confidence=0.9,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'respiratoryRate': respiratoryRate},
                category='respiratory'
            ))

        # ========================================
        # CATEGORY 3: DEVICE HEALTH (CRITICAL)
        # ========================================

        # Critical Battery (<5%)
        if batteryLevel is not None and batteryLevel < self.criticalBatteryThreshold:
            alerts.append(Alert(
                alertType='criticalBattery',
                severity='critical',
                message=f'CRITICAL BATTERY - {batteryLevel}% remaining (< {self.criticalBatteryThreshold}%)',
                source='ESP32',
                confidence=1.0,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'batteryLevel': batteryLevel},
                category='deviceHealth'
            ))

        # Low Battery (<10%) - High severity
        elif batteryLevel is not None and batteryLevel < self.lowBatteryThreshold:
            alerts.append(Alert(
                alertType='lowBattery',
                severity='high',
                message=f'LOW BATTERY - {batteryLevel}% remaining (< {self.lowBatteryThreshold}%)',
                source='ESP32',
                confidence=1.0,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'batteryLevel': batteryLevel},
                category='deviceHealth'
            ))

        # Poor Signal Quality (<50%)
        if signalQuality is not None and signalQuality < 0.5:
            alerts.append(Alert(
                alertType='poorSignalQuality',
                severity='high',
                message=f'POOR SIGNAL QUALITY - {signalQuality*100:.0f}% (< 50%)',
                source='ESP32',
                confidence=0.8,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'signalQuality': signalQuality},
                category='deviceHealth'
            ))

        # ========================================
        # LOGGING
        # ========================================

        if len(alerts) > 0:
            severityCounts = {}
            for alert in alerts:
                severityCounts[alert.severity] = severityCounts.get(alert.severity, 0) + 1

            logger.warning(f"🚨 Detected {len(alerts)} alert(s) for patient {patientId}: {severityCounts}")
            for alert in alerts:
                logger.warning(f"   → [{alert.severity.upper()}] {alert.alertType}: {alert.message}")
        else:
            logger.debug(f"✅ No alerts detected for patient {patientId}")

        return alerts

    def createAlertPayload(self, alert: Alert) -> Dict[str, Any]:
        """
        Convert Alert dataclass to WebSocket payload format

        Returns dictionary suitable for WebSocket broadcasting
        """
        return {
            'alertType': alert.alertType,
            'severity': alert.severity,
            'message': alert.message,
            'source': alert.source,
            'confidence': alert.confidence,
            'deviceId': alert.deviceId,
            'timestamp': alert.timestamp.isoformat(),
            'context': alert.context,
            'category': alert.category
        }


# Singleton instance
alertDetectionService = AlertDetectionService()
