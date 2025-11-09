"""
Alert Manager Service - Centralized Alert Lifecycle Management

This service is the SINGLE SOURCE OF TRUTH for all alert operations:
1. Alert creation with automatic deduplication
2. Alert lifecycle management (active → acknowledged → resolved)
3. Auto-resolution when conditions clear
4. Medical-safe deduplication strategy

STRICT CAMELCASE ONLY - All fields use camelCase naming convention
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import asyncpg
import json

from .alert_detection_service import Alert

logger = logging.getLogger(__name__)


# Resolution criteria: How long vitals must be normal before auto-resolving alert
RESOLUTION_CRITERIA = {
    # Cardiac alerts
    'tachycardia': {'vitalType': 'heartRate', 'normalRange': (60, 100), 'duration': 60},
    'bradycardia': {'vitalType': 'heartRate', 'normalRange': (60, 100), 'duration': 60},
    'severeTachycardia': {'vitalType': 'heartRate', 'normalRange': (60, 100), 'duration': 120},

    # Respiratory alerts
    'tachypnea': {'vitalType': 'respiratoryRate', 'normalRange': (12, 20), 'duration': 60},
    'bradypnea': {'vitalType': 'respiratoryRate', 'normalRange': (12, 20), 'duration': 60},
    'severeRespiratoryDistress': {'vitalType': 'respiratoryRate', 'normalRange': (12, 20), 'duration': 120},

    # Oxygen saturation alerts
    'hypoxia': {'vitalType': 'oxygenSaturation', 'normalRange': (95, 100), 'duration': 30},
    'severeHypoxia': {'vitalType': 'oxygenSaturation', 'normalRange': (95, 100), 'duration': 120},
    'criticalHypoxia': {'vitalType': 'oxygenSaturation', 'normalRange': (95, 100), 'duration': 180},

    # Temperature alerts
    'fever': {'vitalType': 'temperature', 'normalRange': (36.5, 37.5), 'duration': 120},
    'hypothermia': {'vitalType': 'temperature', 'normalRange': (36.5, 37.5), 'duration': 120},

    # Early Warning Score (compound metric)
    'earlyWarningScoreMedium': {'compound': True, 'duration': 300},  # 5 minutes
    'earlyWarningScoreHigh': {'compound': True, 'duration': 600},  # 10 minutes
}


class AlertManagerService:
    """
    Centralized service for managing alert lifecycle and deduplication.

    This service ensures:
    - No duplicate alerts for ongoing conditions
    - Alerts auto-resolve when conditions clear
    - New episodes create new alerts after resolution
    - Severity escalations update existing alerts
    """

    async def createOrUpdateAlert(
        self,
        alert: Alert,
        patientId: str,
        deviceId: str,
        conn: asyncpg.Connection
    ) -> Optional[str]:
        """
        Create new alert OR update existing alert with intelligent deduplication.

        Deduplication Strategy:
        1. Check for existing active/acknowledged alert of same type
        2. If exists: Update timestamp + vital value (no new alert created)
        3. If severity escalated: Update severity and broadcast
        4. If not exists: Create new alert

        Args:
            alert: Alert object from alert_detection_service
            patientId: Patient UUID
            deviceId: Device ID that detected the alert
            conn: Database connection

        Returns:
            Alert ID if NEW alert created, None if updated existing alert
        """

        # Check for existing active, acknowledged, OR recently resolved alert of same type
        # This prevents creating duplicate alerts when conditions oscillate
        existing_alert = await conn.fetchrow('''
            SELECT id, severity, "vitalValue", "createdAt", "updatedAt", status, "resolvedAt"
            FROM patient_alerts
            WHERE "patientId" = $1
              AND type = $2
              AND (
                  status IN ('active', 'acknowledged')
                  OR (status = 'resolved' AND "resolvedAt" > NOW() - INTERVAL '15 minutes')
              )
            ORDER BY "createdAt" DESC
            LIMIT 1
        ''', patientId, alert.alertType)

        if existing_alert:
            # Alert already exists - update it instead of creating duplicate

            # Check if severity escalated (e.g., medium → high → critical)
            severity_order = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            existing_severity_level = severity_order.get(existing_alert['severity'], 0)
            new_severity_level = severity_order.get(alert.severity, 0)

            severity_escalated = new_severity_level > existing_severity_level

            # Extract vital value from alert context
            vital_value = None
            vital_type = None
            threshold_value = None

            if alert.context:
                # Try to find the vital that triggered this alert
                for vital_name in ['heartRate', 'respiratoryRate', 'oxygenSaturation', 'temperature']:
                    if vital_name in alert.context:
                        vital_value = alert.context[vital_name]
                        vital_type = vital_name
                        break

                # Extract threshold if available
                if 'threshold' in alert.context:
                    threshold_value = alert.context['threshold']

            # Check if alert was resolved and needs reactivation
            was_resolved = existing_alert['status'] == 'resolved'

            # Update existing alert (reactivate if it was resolved)
            await conn.execute('''
                UPDATE patient_alerts
                SET "updatedAt" = $1,
                    severity = $2,
                    message = $3,
                    "vitalValue" = $4,
                    "vitalType" = $5,
                    "thresholdValue" = $6,
                    confidence = $7,
                    context = $8,
                    status = $9,
                    "resolvedAt" = NULL
                WHERE id = $10
            ''',
                datetime.now(),
                alert.severity if severity_escalated else existing_alert['severity'],
                alert.message,
                vital_value,
                vital_type,
                threshold_value,
                alert.confidence,
                json.dumps(alert.context) if alert.context else None,
                'active' if was_resolved else existing_alert['status'],  # Reactivate if resolved
                existing_alert['id']
            )

            if was_resolved:
                logger.warning(
                    f"🔄 Alert reactivated: {existing_alert['id']} - {alert.alertType} - {alert.message}"
                )
            elif severity_escalated:
                logger.warning(
                    f"⬆️  Alert severity escalated: {existing_alert['id']} "
                    f"({existing_alert['severity']} → {alert.severity}) - {alert.message}"
                )
            else:
                logger.debug(
                    f"⏱️  Updated existing alert {existing_alert['id']} for {alert.alertType}"
                )

            # Return None to indicate no new alert created (prevents duplicate WebSocket broadcasts)
            return None

        # No existing alert - create new one
        alert_id = await self._createNewAlert(alert, patientId, deviceId, conn)

        return alert_id

    async def _createNewAlert(
        self,
        alert: Alert,
        patientId: str,
        deviceId: str,
        conn: asyncpg.Connection
    ) -> str:
        """
        Create a new alert in the database.

        Args:
            alert: Alert object from alert_detection_service
            patientId: Patient UUID
            deviceId: Device ID that detected the alert
            conn: Database connection

        Returns:
            Alert ID (UUID)
        """
        import uuid

        # Generate unique alert ID
        alert_id = str(uuid.uuid4())

        # Extract vital information from alert context
        vital_value = None
        vital_type = None
        threshold_value = None

        if alert.context:
            # Try to find the vital that triggered this alert
            for vital_name in ['heartRate', 'respiratoryRate', 'oxygenSaturation', 'temperature']:
                if vital_name in alert.context:
                    vital_value = alert.context[vital_name]
                    vital_type = vital_name
                    break

            # Extract threshold if available
            if 'threshold' in alert.context:
                threshold_value = alert.context['threshold']

        # Insert new alert
        await conn.execute('''
            INSERT INTO patient_alerts (
                id, "patientId", "deviceId", type, severity, message, source,
                "alertTimestamp", status, "createdAt", "updatedAt",
                "vitalType", "vitalValue", "thresholdValue", "createdBy",
                category, confidence, context
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
            )
        ''',
            alert_id,
            patientId,
            deviceId,
            alert.alertType,
            alert.severity,
            alert.message,
            alert.source,
            datetime.now(),
            'active',  # New alerts start as 'active'
            datetime.now(),
            datetime.now(),
            vital_type,
            vital_value,
            threshold_value,
            deviceId,
            alert.category,
            alert.confidence,
            json.dumps(alert.context) if alert.context else None
        )

        logger.warning(
            f"🚨 New alert created: {alert_id} - {alert.severity} - {alert.message}"
        )

        return alert_id

    async def resolveAlert(
        self,
        patientId: str,
        alertType: str,
        conn: asyncpg.Connection
    ) -> bool:
        """
        Mark alert as resolved when condition clears.

        Status: active/acknowledged → resolved

        Args:
            patientId: Patient UUID
            alertType: Type of alert to resolve
            conn: Database connection

        Returns:
            True if alert was resolved, False if no alert found
        """

        result = await conn.fetchval('''
            UPDATE patient_alerts
            SET status = 'resolved',
                "resolvedAt" = $1,
                "updatedAt" = $1
            WHERE "patientId" = $2
              AND type = $3
              AND status IN ('active', 'acknowledged')
            RETURNING id
        ''', datetime.now(), patientId, alertType)

        if result:
            logger.info(f"✅ Alert resolved: {result} (type: {alertType}) for patient {patientId}")
            return True

        return False

    async def checkForResolution(
        self,
        patientId: str,
        currentVitals: Dict[str, float],
        conn: asyncpg.Connection
    ) -> List[Dict[str, Any]]:
        """
        Check if any active/acknowledged alerts should be auto-resolved.

        Resolution Logic:
        - Check if vital readings have returned to normal range
        - Check if enough time has passed (stability period)
        - Mark alert as 'resolved' if conditions met

        Args:
            patientId: Patient UUID
            currentVitals: Current vital sign readings
            conn: Database connection

        Returns:
            List of resolved alerts with {alertId, alertType, vitalType}
        """

        resolved_alerts = []

        # Get all active/acknowledged alerts for this patient
        active_alerts = await conn.fetch('''
            SELECT id, type, "vitalType", "vitalValue", "updatedAt"
            FROM patient_alerts
            WHERE "patientId" = $1
              AND status IN ('active', 'acknowledged')
        ''', patientId)

        for alert_row in active_alerts:
            alert_type = alert_row['type']
            vital_type = alert_row['vitalType']

            # Check if we have resolution criteria for this alert type
            if alert_type not in RESOLUTION_CRITERIA:
                continue

            criteria = RESOLUTION_CRITERIA[alert_type]

            # Handle compound metrics (like Early Warning Score)
            if criteria.get('compound'):
                # TODO: Implement compound metric resolution
                # For now, skip auto-resolution of compound alerts
                continue

            # Check if vital has returned to normal range
            if vital_type and vital_type in currentVitals:
                current_value = currentVitals[vital_type]
                normal_min, normal_max = criteria['normalRange']
                required_duration = criteria['duration']  # seconds

                # Check if value is in normal range
                if normal_min <= current_value <= normal_max:
                    # Check if enough time has passed (stability period)
                    last_updated = alert_row['updatedAt']
                    time_since_update = (datetime.now() - last_updated).total_seconds()

                    if time_since_update >= required_duration:
                        # Resolve this alert
                        await self.resolveAlert(patientId, alert_type, conn)

                        resolved_alerts.append({
                            'alertId': alert_row['id'],
                            'alertType': alert_type,
                            'vitalType': vital_type
                        })

        return resolved_alerts


# Global singleton instance
alertManagerService = AlertManagerService()
