"""
Arrhythmia Detection Service
Analyzes heart rate patterns to detect irregular rhythms

MEDICAL DISCLAIMER:
This is a basic screening algorithm for demonstration purposes only.
NOT intended for diagnostic use. NOT FDA or CDSCO approved.
Production systems must use validated medical algorithms and obtain regulatory approval.

Based on Medical Council of India (MCI) cardiac monitoring guidelines.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import statistics

logger = logging.getLogger(__name__)

class ArrhythmiaDetectionService:
    """
    Basic arrhythmia detection from heart rate variability analysis

    Detects:
    - Atrial Fibrillation (AFib): Irregular rapid rhythm
    - Ventricular Tachycardia (VTach): Fast regular rhythm
    - Sick Sinus Syndrome: Slow irregular rhythm
    - General Irregular Rhythm: High variability patterns
    """

    # Clinical thresholds based on MCI cardiac monitoring guidelines
    HRV_HIGH_THRESHOLD = 50  # Standard deviation > 50 indicates irregular rhythm
    HRV_MODERATE_THRESHOLD = 30  # Moderate variability threshold
    HRV_LOW_THRESHOLD = 20  # Low variability indicates regular rhythm

    MIN_READINGS_FOR_ANALYSIS = 10  # Need at least 10 readings for reliable HRV
    ANALYSIS_WINDOW_MINUTES = 5  # Analyze last 5 minutes of data

    async def detect_arrhythmia(
        self,
        patient_id: str,
        device_id: str,
        current_heart_rate: int,
        conn
    ) -> Optional[Dict]:
        """
        Detect arrhythmia patterns from heart rate history

        Args:
            patient_id: Patient UUID
            device_id: Device ID that sent the data
            current_heart_rate: Current heart rate reading (bpm)
            conn: Database connection for querying history

        Returns:
            Alert dictionary if arrhythmia detected, None otherwise
        """
        logger.info(f"🔍 ARRHYTHMIA DETECTION CALLED - Patient: {patient_id}, Device: {device_id}, Current HR: {current_heart_rate}")

        try:
            # Get recent heart rate history for pattern analysis
            recent_hr = await self._get_recent_heart_rates(patient_id, conn)

            logger.info(f"📊 Retrieved {len(recent_hr)} recent heart rate readings")
            if len(recent_hr) > 0:
                logger.info(f"📊 HR values: {recent_hr}")

            if len(recent_hr) < self.MIN_READINGS_FOR_ANALYSIS:
                logger.warning(
                    f"⚠️ Insufficient data for arrhythmia detection: "
                    f"{len(recent_hr)} readings (need {self.MIN_READINGS_FOR_ANALYSIS})"
                )
                return None

            # Calculate Heart Rate Variability (HRV) - standard deviation
            hrv = statistics.stdev(recent_hr)
            mean_hr = statistics.mean(recent_hr)

            logger.info(
                f"📈 ARRHYTHMIA ANALYSIS:\n"
                f"  - Current HR: {current_heart_rate} bpm\n"
                f"  - Mean HR: {mean_hr:.1f} bpm\n"
                f"  - HRV (stdev): {hrv:.2f} bpm\n"
                f"  - Readings: {len(recent_hr)}"
            )

            # Pattern detection using clinical criteria
            alert = None

            # 1. Atrial Fibrillation (AFib) Detection
            # Criteria: Rapid irregular rhythm (100-180 bpm with high variability)
            logger.debug(f"🔍 Checking AFib: mean_hr={mean_hr:.1f} (100-180?), hrv={hrv:.2f} (>{self.HRV_HIGH_THRESHOLD}?)")
            if 100 <= mean_hr <= 180 and hrv > self.HRV_HIGH_THRESHOLD:
                logger.warning(f"🚨 AFib CRITERIA MET! Creating alert...")
                alert = await self._create_arrhythmia_alert(
                    patient_id, device_id,
                    'AFIB_SUSPECTED',
                    f'Possible Atrial Fibrillation - Irregular rapid rhythm '
                    f'(HR: {mean_hr:.0f} bpm, HRV: {hrv:.1f})',
                    'critical',
                    {'meanHR': mean_hr, 'hrv': hrv, 'readings': len(recent_hr)},
                    conn
                )
                logger.info(f"✅ AFib alert created: {alert}")

            # 2. Ventricular Tachycardia (VTach) Detection
            # Criteria: Fast regular rhythm (>150 bpm with low variability)
            elif mean_hr > 150 and hrv < self.HRV_LOW_THRESHOLD:
                logger.warning(f"🚨 VTach CRITERIA MET! Creating alert...")
                alert = await self._create_arrhythmia_alert(
                    patient_id, device_id,
                    'VTACH_SUSPECTED',
                    f'Possible Ventricular Tachycardia - Fast regular rhythm '
                    f'(HR: {mean_hr:.0f} bpm)',
                    'critical',
                    {'meanHR': mean_hr, 'hrv': hrv, 'readings': len(recent_hr)},
                    conn
                )
                logger.info(f"✅ VTach alert created: {alert}")

            # 3. Sick Sinus Syndrome Detection
            # Criteria: Slow irregular rhythm (<50 bpm with moderate variability)
            elif mean_hr < 50 and hrv > self.HRV_MODERATE_THRESHOLD:
                logger.warning(f"🚨 Sick Sinus CRITERIA MET! Creating alert...")
                alert = await self._create_arrhythmia_alert(
                    patient_id, device_id,
                    'SICK_SINUS_SUSPECTED',
                    f'Possible Sick Sinus Syndrome - Slow irregular rhythm '
                    f'(HR: {mean_hr:.0f} bpm, HRV: {hrv:.1f})',
                    'critical',
                    {'meanHR': mean_hr, 'hrv': hrv, 'readings': len(recent_hr)},
                    conn
                )
                logger.info(f"✅ Sick Sinus alert created: {alert}")

            # 4. General Irregular Rhythm Detection
            # Criteria: High variability without specific pattern
            elif hrv > self.HRV_HIGH_THRESHOLD:
                logger.warning(f"🚨 Irregular Rhythm CRITERIA MET! Creating alert...")
                alert = await self._create_arrhythmia_alert(
                    patient_id, device_id,
                    'IRREGULAR_RHYTHM',
                    f'Irregular Heart Rhythm Detected (HRV: {hrv:.1f})',
                    'high',
                    {'meanHR': mean_hr, 'hrv': hrv, 'readings': len(recent_hr)},
                    conn
                )
                logger.info(f"✅ Irregular Rhythm alert created: {alert}")
            else:
                logger.info(f"✅ No arrhythmia detected - all patterns within normal limits")

            if alert:
                logger.warning(
                    f"🚨 ARRHYTHMIA DETECTED: {alert['alertType']} - {alert['message']}"
                )
            else:
                logger.info(f"✅ Arrhythmia detection complete - no alerts generated")

            return alert

        except Exception as e:
            logger.error(f"❌ Arrhythmia detection error: {e}", exc_info=True)
            # Non-blocking - don't crash vitals storage if detection fails
            return None

    async def _get_recent_heart_rates(
        self,
        patient_id: str,
        conn,
        limit: int = 20
    ) -> List[float]:
        """
        Get recent heart rate readings for pattern analysis

        Args:
            patient_id: Patient UUID
            conn: Database connection
            limit: Maximum number of readings (default 20)

        Returns:
            List of heart rate values (newest first)
        """
        cutoff_time = datetime.now() - timedelta(minutes=self.ANALYSIS_WINDOW_MINUTES)

        rows = await conn.fetch('''
            SELECT value
            FROM vitals_timeseries
            WHERE "patientId" = $1
            AND vitaltype = 'heartrate'
            AND time >= $2
            ORDER BY time DESC
            LIMIT $3
        ''', patient_id, cutoff_time, limit)

        return [float(row['value']) for row in rows]

    async def _create_arrhythmia_alert(
        self,
        patient_id: str,
        device_id: str,
        alert_type: str,
        message: str,
        severity: str,
        metadata: Dict,
        conn
    ) -> Dict:
        """
        Create arrhythmia alert in patient_alerts table

        Args:
            patient_id: Patient UUID
            device_id: Device ID that detected the arrhythmia
            alert_type: Type code (AFIB_SUSPECTED, VTACH_SUSPECTED, etc.)
            message: Human-readable alert message for medical staff
            severity: 'critical' or 'high'
            metadata: Additional data (meanHR, hrv, readings count)
            conn: Database connection

        Returns:
            Alert dictionary for WebSocket broadcast
        """
        alert_id = await conn.fetchval('''
            INSERT INTO patient_alerts (
                "patientId", type, message, severity, status,
                "vitalType", "vitalValue", "createdAt", "createdBy"
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        ''', patient_id, 'arrhythmia', message, severity, 'active',
             alert_type, metadata.get('meanHR'), datetime.now(), device_id)

        logger.warning(f"Alert created: {alert_id} - {severity} - {message}")

        return {
            'alertId': alert_id,
            'alertType': alert_type,
            'message': message,
            'severity': severity,
            'metadata': metadata
        }

# Global service instance
arrhythmia_detection_service = ArrhythmiaDetectionService()
