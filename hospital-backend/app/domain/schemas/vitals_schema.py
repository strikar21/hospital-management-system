"""
Vitals schema - Single source of truth for vitals data structure.

This schema is mirrored in frontend:
    hospital-display-app/src/data/schemas/Vital.schema.ts

Any changes here MUST be reflected in frontend schema.

Usage:
    from app.domain.schemas import VitalsRecord

    vitals: VitalsRecord = {
        'heartRate': 75,
        'oxygenSaturation': 98,
        'patientId': 'P001',
        'deviceId': 'D001',
        'timestamp': datetime.now(timezone.utc)
    }
"""

from typing import TypedDict, Optional
from datetime import datetime


class VitalsRecord(TypedDict, total=False):
    """
    Complete vitals data structure.

    Fields are all optional to handle partial vital readings.
    All numeric vitals can be None if sensor not connected/reading invalid.

    Frontend Mirror: hospital-display-app/src/data/schemas/Vital.schema.ts
    """

    # ========================================
    # CARDIOVASCULAR VITALS
    # ========================================
    heartRate: Optional[int]              # BPM (beats per minute)
    systolicPressure: Optional[int]       # mmHg
    diastolicPressure: Optional[int]      # mmHg

    # ========================================
    # RESPIRATORY VITALS
    # ========================================
    respiratoryRate: Optional[int]        # Breaths per minute
    oxygenSaturation: Optional[int]       # Percentage (0-100)

    # ========================================
    # TEMPERATURE
    # ========================================
    skinTemperature: Optional[float]      # Fahrenheit

    # ========================================
    # NEUROLOGICAL/CARDIAC MONITORING
    # ========================================
    ecgReading: Optional[int]             # mV * 100 (so 120 = 1.2mV)
    eegReading: Optional[int]             # μV (microvolts)
    isEcgMode: Optional[bool]             # True = ECG mode, False = EEG mode

    # ========================================
    # ADVANCED SENSOR VITALS (Phase 2)
    # ========================================
    bioimpedance: Optional[float]         # 20-50Ω thoracic impedance (MAX86178)
    tremor: Optional[float]               # 0-10 scale (BMI323)
    imuFallRisk: Optional[float]          # 0-10 numeric fall risk (BMI323 IMU)
    perfusionIndex: Optional[float]       # 0-20% perfusion index (MAX86178)
    stepCount: Optional[int]              # Cumulative step count (BMI323)
    watchWorn: Optional[bool]             # Watch worn status (MAX86178 proximity)
    lastMovementTime: Optional[int]       # Last movement timestamp in ms (BMI323)

    # ========================================
    # ECG COMPUTED METRICS (Backend calculates from ADS1299)
    # ========================================
    ecg_rrInterval: Optional[int]         # RR interval in ms
    ecg_qrsDuration: Optional[int]        # QRS duration in ms
    ecg_qtInterval: Optional[int]         # QT interval in ms
    ecg_axis: Optional[int]               # Heart axis in degrees
    ecg_rhythm: Optional[str]             # Detected rhythm (sinus, afib, etc.)
    ecg_stSegment: Optional[str]          # ST segment status (normal, elevated, depressed)

    # ========================================
    # EEG COMPUTED METRICS (Backend calculates from ADS1299)
    # ========================================
    eeg_alphaPower: Optional[float]       # Alpha band (8-13 Hz)
    eeg_betaPower: Optional[float]        # Beta band (13-30 Hz)
    eeg_thetaPower: Optional[float]       # Theta band (4-8 Hz)
    eeg_deltaPower: Optional[float]       # Delta band (0.5-4 Hz)
    eeg_gammaPower: Optional[float]       # Gamma band (30-100 Hz)
    eeg_dominantFrequency: Optional[float] # Dominant frequency in Hz
    eeg_seizureActivity: Optional[bool]   # Seizure detection flag

    # ========================================
    # METADATA (Required fields)
    # ========================================
    patientId: str                        # Patient UUID (REQUIRED)
    deviceId: str                         # Device UUID (REQUIRED)
    timestamp: datetime                   # Measurement timestamp (REQUIRED)
    lastDataReceived: datetime            # Last successful data receipt
    dataQualityScore: float               # 0-1 scale for overall quality
    batteryLevel: Optional[int]           # Device battery 0-100
    signalQuality: Optional[int]          # Signal quality 0-100


class VitalsThresholds(TypedDict):
    """
    Vital sign threshold values for alert generation.

    Based on standard adult clinical guidelines.
    Compliant with Medical Council of India (MCI) monitoring standards.
    """
    criticalLow: Optional[float]          # Critical low threshold (immediate intervention)
    warningLow: Optional[float]           # Warning low threshold (monitor closely)
    warningHigh: Optional[float]          # Warning high threshold (monitor closely)
    criticalHigh: Optional[float]         # Critical high threshold (immediate intervention)
    unit: str                             # Unit of measurement (bpm, %, mmHg, °F, etc.)


# Standard clinical thresholds (used by alert detection)
VITAL_THRESHOLDS = {
    'heartrate': VitalsThresholds(
        criticalLow=40,
        warningLow=50,
        warningHigh=120,
        criticalHigh=150,
        unit='bpm'
    ),
    'oxygensaturation': VitalsThresholds(
        criticalLow=85,
        warningLow=90,
        warningHigh=None,
        criticalHigh=None,
        unit='%'
    ),
    'bloodpressuresystolic': VitalsThresholds(
        criticalLow=80,
        warningLow=90,
        warningHigh=140,
        criticalHigh=180,
        unit='mmHg'
    ),
    'temperature': VitalsThresholds(
        criticalLow=95.0,
        warningLow=97.0,
        warningHigh=100.4,
        criticalHigh=103.0,
        unit='°F'
    ),
    'respiratoryrate': VitalsThresholds(
        criticalLow=10,
        warningLow=12,
        warningHigh=20,
        criticalHigh=30,
        unit='/min'
    )
}
