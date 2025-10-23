"""
Neural Vitals Models - 8-12 Channel ECG/EEG Data Structures
All models use camelCase naming as per project standards
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Literal, Any
from datetime import datetime
from decimal import Decimal


# ============================================
# SIGNAL QUALITY MODELS
# ============================================

class SignalQuality(BaseModel):
    """Signal quality metrics for ECG/EEG"""
    overall: float = Field(..., ge=0.0, le=1.0, description="Overall signal quality (0-1)")
    leadOff: Optional[List[bool]] = Field(None, description="Lead-off detection per channel")
    noise: Optional[List[float]] = Field(None, description="Noise level per channel (0-1)")
    impedance: Optional[List[float]] = Field(None, description="Impedance per channel (kOhm)")

    class Config:
        from_attributes = True


# ============================================
# ECG ANALYSIS MODELS
# ============================================

class ECGAnalysis(BaseModel):
    """Computed ECG analysis metrics - calculated on backend or ESP32"""
    rrInterval: Optional[int] = Field(None, description="RR interval in milliseconds")
    qrsDuration: Optional[int] = Field(None, description="QRS duration in milliseconds")
    qtInterval: Optional[int] = Field(None, description="QT interval in milliseconds")
    axis: Optional[int] = Field(None, description="Heart axis in degrees")
    rhythm: Optional[str] = Field(None, description="Detected rhythm (sinus, afib, etc.)")
    stSegment: Optional[Literal['normal', 'elevated', 'depressed']] = Field(None, description="ST segment analysis")

    class Config:
        from_attributes = True


class ECGLeadValues(BaseModel):
    """Current ECG lead values (instantaneous or averaged)"""
    leadI: Optional[float] = None
    leadII: Optional[float] = None
    leadIII: Optional[float] = None
    aVR: Optional[float] = None
    aVL: Optional[float] = None
    aVF: Optional[float] = None
    v1: Optional[float] = None
    v2: Optional[float] = None
    v3: Optional[float] = None
    v4: Optional[float] = None
    v5: Optional[float] = None
    v6: Optional[float] = None

    class Config:
        from_attributes = True


# ============================================
# EEG ANALYSIS MODELS
# ============================================

class EEGBandPowers(BaseModel):
    """EEG frequency band powers in µV²"""
    alpha: float = Field(..., ge=0, description="Alpha band (8-13 Hz)")
    beta: float = Field(..., ge=0, description="Beta band (13-30 Hz)")
    theta: float = Field(..., ge=0, description="Theta band (4-8 Hz)")
    delta: float = Field(..., ge=0, description="Delta band (0.5-4 Hz)")
    gamma: Optional[float] = Field(None, ge=0, description="Gamma band (30-100 Hz)")

    class Config:
        from_attributes = True


class EEGAnalysis(BaseModel):
    """Computed EEG analysis metrics - calculated on backend"""
    bandPowers: EEGBandPowers
    dominantFrequency: float = Field(..., ge=0, le=100, description="Dominant frequency in Hz")
    asymmetry: Optional[float] = Field(None, description="Left-right hemispheric asymmetry")
    seizureActivity: bool = Field(False, description="Seizure detection flag")

    class Config:
        from_attributes = True


class EEGChannelValues(BaseModel):
    """Current EEG channel values (instantaneous or averaged)"""
    Fp1: Optional[float] = None  # Frontal pole 1
    Fp2: Optional[float] = None  # Frontal pole 2
    F3: Optional[float] = None   # Frontal 3
    F4: Optional[float] = None   # Frontal 4
    C3: Optional[float] = None   # Central 3
    C4: Optional[float] = None   # Central 4
    O1: Optional[float] = None   # Occipital 1
    O2: Optional[float] = None   # Occipital 2

    class Config:
        from_attributes = True


# ============================================
# WAVEFORM DATA STRUCTURES
# ============================================

class ChannelData(BaseModel):
    """Delta-encoded channel data for bandwidth efficiency"""
    baseline: int = Field(..., description="Baseline value for delta encoding")
    deltas: List[int] = Field(..., description="Delta values from baseline")

    class Config:
        from_attributes = True

    def decompress(self) -> List[int]:
        """Decompress delta-encoded data back to original values"""
        values = [self.baseline]
        for delta in self.deltas:
            values.append(values[-1] + delta)
        return values


class ECGLimbLeads(BaseModel):
    """ECG limb leads (3 channels minimum)"""
    leadI: ChannelData
    leadII: ChannelData
    leadIII: ChannelData

    class Config:
        from_attributes = True


class ECGPrecordialLeads(BaseModel):
    """ECG precordial leads (optional, 5 channels)"""
    v1: Optional[ChannelData] = None
    v2: Optional[ChannelData] = None
    v3: Optional[ChannelData] = None
    v4: Optional[ChannelData] = None
    v5: Optional[ChannelData] = None

    class Config:
        from_attributes = True


class ECGDerivedLeads(BaseModel):
    """ECG derived leads (optional, calculated from limb leads)"""
    aVR: Optional[ChannelData] = None
    aVL: Optional[ChannelData] = None
    aVF: Optional[ChannelData] = None
    v6: Optional[ChannelData] = None

    class Config:
        from_attributes = True


class ECGEvent(BaseModel):
    """Detected ECG event within waveform"""
    timestamp: int = Field(..., description="Milliseconds from start of snapshot")
    eventType: str = Field(..., description="Event type (pvc, pac, etc.)")
    confidence: float = Field(..., ge=0.0, le=1.0)
    location: Optional[str] = Field(None, description="Lead where event was detected")

    class Config:
        from_attributes = True


class ECGWaveformData(BaseModel):
    """Complete 12-lead ECG waveform data"""
    limb: ECGLimbLeads  # Required: 3 leads minimum
    precordial: Optional[ECGPrecordialLeads] = None  # Optional: V1-V5
    derived: Optional[ECGDerivedLeads] = None  # Optional: aVR, aVL, aVF, V6
    events: Optional[List[ECGEvent]] = Field(None, description="Detected events in waveform")

    class Config:
        from_attributes = True


class EEGFrontalChannels(BaseModel):
    """EEG frontal channels (4 channels)"""
    Fp1: ChannelData
    Fp2: ChannelData
    F3: ChannelData
    F4: ChannelData

    class Config:
        from_attributes = True


class EEGCentralChannels(BaseModel):
    """EEG central channels (2 channels)"""
    C3: ChannelData
    C4: ChannelData

    class Config:
        from_attributes = True


class EEGOccipitalChannels(BaseModel):
    """EEG occipital channels (2 channels)"""
    O1: ChannelData
    O2: ChannelData

    class Config:
        from_attributes = True


class EEGWaveformData(BaseModel):
    """Complete 8-channel EEG waveform data"""
    frontal: EEGFrontalChannels  # Required: Fp1, Fp2, F3, F4
    central: EEGCentralChannels  # Required: C3, C4
    occipital: EEGOccipitalChannels  # Required: O1, O2
    analysis: Optional[EEGAnalysis] = None

    class Config:
        from_attributes = True


# ============================================
# VITALS REALTIME MESSAGE (MQTT)
# ============================================

class VitalsRealtimeMessage(BaseModel):
    """
    Real-time vitals + waveform combined message - Published every 1 second
    MQTT Topic: hospital/devices/{deviceId}/vitals

    Contains both basic vitals AND 1-second waveform snapshot in single message.
    This reduces MQTT overhead and provides perfect time synchronization.
    """
    # Device identification
    deviceId: str
    patientId: str
    timestamp: datetime
    mode: Literal['ecg', 'eeg'] = Field(..., description="Operating mode")

    # Basic vitals (always present)
    heartRate: Optional[int] = Field(None, ge=30, le=250, description="Heart rate in BPM")
    respiratoryRate: Optional[int] = Field(None, ge=5, le=60, description="Respiratory rate per minute")
    skinTemperature: Optional[float] = Field(None, ge=30.0, le=45.0, description="Skin temperature in Celsius")
    oxygenSaturation: Optional[int] = Field(None, ge=0, le=100, description="SpO2 percentage")
    bloodPressureSystolic: Optional[int] = Field(None, ge=60, le=200, description="Systolic blood pressure in mmHg")
    bloodPressureDiastolic: Optional[int] = Field(None, ge=40, le=130, description="Diastolic blood pressure in mmHg")
    batteryLevel: Optional[int] = Field(None, ge=0, le=100, description="Device battery percentage")
    signalQuality: Optional[float] = Field(None, ge=0.0, le=1.0, description="Overall signal quality")

    # Waveform data (1-second snapshot - 250 samples per channel)
    sampleRate: Optional[int] = Field(None, description="Sampling rate in Hz (typically 250)")
    duration: Optional[int] = Field(None, description="Duration of waveform snapshot in seconds (typically 1)")
    compression: Optional[str] = Field('delta', description="Compression method")

    # ECG waveform (mode='ecg')
    ecgWaveform: Optional[ECGWaveformData] = Field(None, description="1-second ECG waveform snapshot")

    # EEG waveform (mode='eeg')
    eegWaveform: Optional[EEGWaveformData] = Field(None, description="1-second EEG waveform snapshot")

    # ECG mode analysis (optional - backend calculates from waveform)
    ecgAnalysis: Optional[ECGAnalysis] = None
    ecgLeads: Optional[ECGLeadValues] = None

    # EEG mode analysis (optional - backend calculates from waveform)
    eegAnalysis: Optional[EEGAnalysis] = None
    eegChannels: Optional[EEGChannelValues] = None

    # Quality metrics
    quality: Optional[SignalQuality] = None

    # Metadata
    sequence: Optional[int] = Field(None, description="Message sequence number")
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

    @validator('mode')
    def validate_mode_data(cls, v, values):
        """Ensure ECG data is present if mode is 'ecg', and EEG data if mode is 'eeg'"""
        # This is lenient validation - allows partial data during development
        return v


# ============================================
# WAVEFORM SNAPSHOT MESSAGE (MQTT)
# ============================================

class WaveformSnapshotMessage(BaseModel):
    """
    Waveform snapshot message - Published every 10 seconds
    MQTT Topic: hospital/devices/{deviceId}/waveform
    """
    # Device identification
    deviceId: str
    patientId: str
    timestamp: datetime
    mode: Literal['ecg', 'eeg']

    # Waveform parameters
    sampleRate: int = Field(..., description="Sampling rate in Hz (e.g., 250, 500)")
    duration: int = Field(..., description="Duration of snapshot in seconds")
    compression: Optional[str] = Field('delta', description="Compression method")

    # Waveform data (one or the other based on mode)
    ecgWaveform: Optional[ECGWaveformData] = None
    eegWaveform: Optional[EEGWaveformData] = None

    # Quality metrics
    quality: Optional[SignalQuality] = None

    # Metadata
    sequence: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# ============================================
# NEURAL EVENT MESSAGE (MQTT)
# ============================================

class NeuralEventMessage(BaseModel):
    """
    Neural event message - Published when arrhythmia or seizure detected
    MQTT Topic: hospital/devices/{deviceId}/event
    """
    # Device identification
    deviceId: str
    patientId: str
    timestamp: datetime
    mode: Literal['ecg', 'eeg']

    # Event details
    eventType: str = Field(..., description="Event type (bradycardia, tachycardia, seizure, etc.)")
    severity: Literal['low', 'medium', 'high', 'critical']
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")

    # Context
    sampleRate: Optional[int] = None
    duration: Optional[int] = None
    context: Optional[Dict[str, Any]] = Field(None, description="Event context (vitals at time of event)")

    # Waveform snippet (optional - small segment showing the event)
    waveform: Optional[Dict[str, Any]] = Field(None, description="Waveform snippet around event")

    # Recommended actions
    actions: Optional[List[str]] = Field(None, description="Recommended clinical actions")

    # Metadata
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# ============================================
# DATABASE MODELS (for TimescaleDB storage)
# ============================================

class VitalsRealtimeDB(BaseModel):
    """Model for vitals_realtime table in TimescaleDB"""
    time: datetime
    patientId: str
    deviceId: str
    mode: str

    # Basic vitals
    heartRate: Optional[int] = None
    respiratoryRate: Optional[int] = None
    skinTemperature: Optional[Decimal] = None
    oxygenSaturation: Optional[int] = None
    batteryLevel: Optional[int] = None
    signalQuality: Optional[Decimal] = None

    # ECG analysis
    rrInterval: Optional[int] = None
    qrsDuration: Optional[int] = None
    qtInterval: Optional[int] = None
    axis: Optional[int] = None
    rhythm: Optional[str] = None
    stSegment: Optional[str] = None

    # EEG analysis
    alphaPower: Optional[Decimal] = None
    betaPower: Optional[Decimal] = None
    thetaPower: Optional[Decimal] = None
    deltaPower: Optional[Decimal] = None
    gammaPower: Optional[Decimal] = None
    dominantFrequency: Optional[Decimal] = None
    seizureActivity: Optional[bool] = None

    # Quality
    quality: Optional[Dict[str, Any]] = None

    # Metadata
    sequence: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class WaveformSnapshotDB(BaseModel):
    """Model for waveform_snapshots table in TimescaleDB"""
    time: datetime
    patientId: str
    deviceId: str
    mode: str
    sampleRate: int
    duration: int

    # ECG channels (JSONB)
    ecgLimbLeads: Optional[Dict[str, Any]] = None
    ecgPrecordialLeads: Optional[Dict[str, Any]] = None
    ecgDerivedLeads: Optional[Dict[str, Any]] = None
    ecgEvents: Optional[List[Dict[str, Any]]] = None

    # EEG channels (JSONB)
    eegFrontalChannels: Optional[Dict[str, Any]] = None
    eegCentralChannels: Optional[Dict[str, Any]] = None
    eegOccipitalChannels: Optional[Dict[str, Any]] = None
    eegAnalysis: Optional[Dict[str, Any]] = None

    # Quality
    quality: Optional[Dict[str, Any]] = None

    # Metadata
    sequence: Optional[int] = None
    compression: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class NeuralEventDB(BaseModel):
    """Model for neural_events table in TimescaleDB"""
    time: datetime
    patientId: str
    deviceId: str
    eventType: str
    severity: str
    confidence: Decimal
    mode: str

    # Optional waveform context
    sampleRate: Optional[int] = None
    duration: Optional[int] = None
    context: Optional[Dict[str, Any]] = None
    waveform: Optional[Dict[str, Any]] = None
    actions: Optional[List[str]] = None

    # Workflow tracking
    acknowledged: bool = False
    acknowledgedBy: Optional[str] = None
    acknowledgedAt: Optional[datetime] = None
    resolved: bool = False
    resolvedAt: Optional[datetime] = None

    # Metadata
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# ============================================
# API RESPONSE MODELS
# ============================================

class VitalsRealtimeResponse(BaseModel):
    """API response for current vitals"""
    patientId: str
    deviceId: str
    timestamp: datetime
    mode: str

    # Basic vitals
    heartRate: Optional[int] = None
    respiratoryRate: Optional[int] = None
    skinTemperature: Optional[float] = None
    oxygenSaturation: Optional[int] = None
    batteryLevel: Optional[int] = None
    signalQuality: Optional[float] = None

    # Nested ECG/EEG objects
    ecg: Optional[Dict[str, Any]] = None
    eeg: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class WaveformSnapshotResponse(BaseModel):
    """API response for waveform snapshot"""
    timestamp: datetime
    mode: str
    sampleRate: int
    duration: int
    waveform: Dict[str, Any]  # ECG or EEG waveform data
    quality: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class NeuralEventResponse(BaseModel):
    """API response for neural event"""
    eventId: str
    timestamp: datetime
    eventType: str
    severity: str
    confidence: float
    mode: str
    acknowledged: bool
    resolved: bool
    context: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
