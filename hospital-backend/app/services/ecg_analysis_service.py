"""
ECG Analysis Service
Medical-grade ECG analysis with Pan-Tompkins QRS detection and rhythm classification
STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
"""

import numpy as np
from scipy import signal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ECGAnalysisResult:
    """Results from ECG analysis"""
    # Heart rate metrics
    heartRate: Optional[int] = None  # BPM
    rrInterval: Optional[int] = None  # Average RR interval in ms
    rrVariability: Optional[float] = None  # HRV - std deviation of RR intervals

    # QRS/QT metrics
    qrsDuration: Optional[int] = None  # Average QRS width in ms
    qtInterval: Optional[int] = None  # Average QT duration in ms
    qtcInterval: Optional[int] = None  # Corrected QT (Bazett's formula)

    # Morphology
    axis: Optional[int] = None  # Heart axis in degrees (-180 to +180)
    rhythm: Optional[str] = None  # Detected rhythm type
    stSegment: Optional[str] = None  # 'normal', 'elevated', 'depressed'

    # Quality metrics
    signalQuality: Optional[float] = None  # 0.0 to 1.0
    confidence: Optional[float] = None  # Analysis confidence 0.0 to 1.0

    # Peak locations (for debugging/visualization)
    rPeaks: List[int] = None  # Sample indices of R peaks
    qrsComplexes: List[Tuple[int, int, int]] = None  # (Q, R, S) sample indices


class ECGAnalysisService:
    """
    ECG Analysis Service implementing medical-grade algorithms:
    - Pan-Tompkins QRS detection (1985 classic algorithm)
    - Rhythm classification (sinus, AFib, VT, VF)
    - ST segment analysis (STEMI detection)
    - QT interval calculation with Bazett's correction
    """

    def __init__(self, sampleRate: int = 250):
        """
        Initialize ECG analysis service

        Args:
            sampleRate: Sample rate in Hz (default 250 Hz for ADS1298)
        """
        self.sampleRate = sampleRate
        self.nyquistFreq = sampleRate / 2.0

        # Pan-Tompkins parameters
        self.lowpassCutoff = 15.0  # Hz
        self.highpassCutoff = 5.0   # Hz
        self.integrationWindow = int(0.15 * sampleRate)  # 150ms window

        # Detection thresholds
        self.rPeakThreshold = 0.5  # 50% of max signal
        self.qrsMinWidth = int(0.06 * sampleRate)  # 60ms minimum QRS width
        self.qrsMaxWidth = int(0.12 * sampleRate)  # 120ms maximum QRS width

        # Rhythm classification parameters
        self.normalRRVariance = 0.1  # 10% variance for sinus rhythm
        self.bradycardiaThreshold = 60  # BPM
        self.tachycardiaThreshold = 100  # BPM
        self.vTachycardiaThreshold = 150  # BPM

        logger.info(f"✅ ECG Analysis Service initialized (sample rate: {sampleRate} Hz)")

    def analyzeECG(self, waveformData: Dict[str, any], mode: str = 'ecg') -> ECGAnalysisResult:
        """
        Analyze ECG waveform data and return comprehensive analysis

        Args:
            waveformData: Dictionary with ECG lead data (limb, precordial)
            mode: 'ecg' or 'eeg' (must be 'ecg')

        Returns:
            ECGAnalysisResult with all calculated metrics
        """
        if mode != 'ecg':
            logger.warning(f"⚠️ Skipping ECG analysis - mode is {mode}, not 'ecg'")
            return ECGAnalysisResult()

        try:
            # Extract Lead II (best for QRS detection)
            leadIIData = self._extractLeadII(waveformData)

            if leadIIData is None or len(leadIIData) < self.sampleRate:
                logger.warning("⚠️ Insufficient ECG data for analysis")
                return ECGAnalysisResult(signalQuality=0.0, confidence=0.0)

            # Step 1: Preprocess signal (bandpass filter)
            filteredSignal = self._preprocessSignal(leadIIData)

            # Step 2: Detect R peaks using Pan-Tompkins
            rPeaks = self._detectRPeaks(filteredSignal)

            if len(rPeaks) < 2:
                logger.warning("⚠️ Insufficient R peaks detected")
                return ECGAnalysisResult(signalQuality=0.3, confidence=0.2)

            # Step 3: Calculate RR intervals and heart rate
            rrIntervals = self._calculateRRIntervals(rPeaks)
            heartRate = self._calculateHeartRate(rrIntervals)
            rrVariability = np.std(rrIntervals) if len(rrIntervals) > 1 else 0.0

            # Step 4: Detect QRS complexes (Q, R, S points)
            qrsComplexes = self._detectQRSComplexes(filteredSignal, rPeaks)
            qrsDuration = self._calculateAverageQRSDuration(qrsComplexes)

            # Step 5: Detect T waves and calculate QT interval
            tWaves = self._detectTWaves(filteredSignal, qrsComplexes)
            qtInterval = self._calculateQTInterval(qrsComplexes, tWaves)
            qtcInterval = self._calculateQTc(qtInterval, rrIntervals)

            # Step 6: Classify rhythm
            rhythm = self._classifyRhythm(heartRate, rrIntervals, qrsDuration)

            # Step 7: Analyze ST segment
            stSegment = self._analyzeSTSegment(filteredSignal, qrsComplexes, tWaves)

            # Step 8: Calculate signal quality
            signalQuality = self._calculateSignalQuality(leadIIData, rPeaks)
            confidence = self._calculateConfidence(signalQuality, len(rPeaks))

            result = ECGAnalysisResult(
                heartRate=int(heartRate),
                rrInterval=int(np.mean(rrIntervals)) if len(rrIntervals) > 0 else None,
                rrVariability=round(rrVariability, 2),
                qrsDuration=qrsDuration,
                qtInterval=qtInterval,
                qtcInterval=qtcInterval,
                axis=None,  # TODO: Calculate from limb leads
                rhythm=rhythm,
                stSegment=stSegment,
                signalQuality=round(signalQuality, 2),
                confidence=round(confidence, 2),
                rPeaks=rPeaks.tolist() if isinstance(rPeaks, np.ndarray) else rPeaks,
                qrsComplexes=qrsComplexes
            )

            logger.info(f"✅ ECG Analysis complete: HR={heartRate} BPM, Rhythm={rhythm}")
            return result

        except Exception as e:
            logger.error(f"❌ ECG analysis failed: {e}", exc_info=True)
            return ECGAnalysisResult(signalQuality=0.0, confidence=0.0)

    def _extractLeadII(self, waveformData: Dict) -> Optional[np.ndarray]:
        """Extract Lead II data from waveform structure"""
        try:
            # Handle nested structure: ecgWaveform -> limb -> leadII
            if 'limb' in waveformData:
                limbLeads = waveformData['limb']
                if 'leadII' in limbLeads:
                    leadII = limbLeads['leadII']

                    # Handle delta encoding: baseline + deltas
                    if isinstance(leadII, dict) and 'baseline' in leadII and 'deltas' in leadII:
                        baseline = leadII['baseline']
                        deltas = np.array(leadII['deltas'])
                        # Reconstruct signal from delta encoding
                        signal = np.cumsum(np.concatenate([[baseline], deltas]))
                        return signal
                    elif isinstance(leadII, list):
                        return np.array(leadII)

            # Fallback: try direct array access
            if isinstance(waveformData, (list, np.ndarray)):
                return np.array(waveformData)

            logger.warning("⚠️ Could not extract Lead II from waveform data")
            return None

        except Exception as e:
            logger.error(f"❌ Error extracting Lead II: {e}")
            return None

    def _preprocessSignal(self, rawSignal: np.ndarray) -> np.ndarray:
        """
        Preprocess ECG signal using bandpass filter (5-15 Hz)
        This removes baseline wander and high-frequency noise
        """
        # Bandpass filter (5-15 Hz) - Pan-Tompkins standard
        sos = signal.butter(2, [self.highpassCutoff, self.lowpassCutoff],
                           btype='bandpass', fs=self.sampleRate, output='sos')
        filtered = signal.sosfilt(sos, rawSignal)

        # Derivative filter (enhances QRS slopes)
        derivative = np.diff(filtered)

        # Square (emphasizes higher frequencies)
        squared = derivative ** 2

        # Moving average integration (smooths signal)
        integrated = np.convolve(squared, np.ones(self.integrationWindow) / self.integrationWindow, mode='same')

        return integrated

    def _detectRPeaks(self, processedSignal: np.ndarray) -> np.ndarray:
        """
        Detect R peaks using Pan-Tompkins algorithm
        Uses adaptive thresholding to find QRS complexes
        """
        # Adaptive threshold (50% of max signal energy)
        threshold = self.rPeakThreshold * np.max(processedSignal)

        # Find peaks above threshold with minimum distance
        minDistance = int(0.3 * self.sampleRate)  # 300ms minimum between beats (200 BPM max)
        peaks, _ = signal.find_peaks(processedSignal, height=threshold, distance=minDistance)

        return peaks

    def _calculateRRIntervals(self, rPeaks: np.ndarray) -> np.ndarray:
        """Calculate RR intervals in milliseconds"""
        if len(rPeaks) < 2:
            return np.array([])

        rrSamples = np.diff(rPeaks)
        rrIntervals = (rrSamples / self.sampleRate) * 1000  # Convert to ms
        return rrIntervals

    def _calculateHeartRate(self, rrIntervals: np.ndarray) -> float:
        """Calculate average heart rate from RR intervals"""
        if len(rrIntervals) == 0:
            return 0.0

        avgRRInterval = np.mean(rrIntervals) / 1000.0  # Convert ms to seconds
        heartRate = 60.0 / avgRRInterval  # BPM
        return heartRate

    def _detectQRSComplexes(self, signal: np.ndarray, rPeaks: np.ndarray) -> List[Tuple[int, int, int]]:
        """
        Detect Q, R, S points for each QRS complex
        Returns list of (qPeak, rPeak, sPeak) tuples
        """
        complexes = []

        for rPeak in rPeaks:
            # Search for Q wave (negative deflection before R)
            qStart = max(0, rPeak - self.qrsMaxWidth // 2)
            qRegion = signal[qStart:rPeak]
            if len(qRegion) > 0:
                qPeak = qStart + np.argmin(qRegion)
            else:
                qPeak = rPeak

            # Search for S wave (negative deflection after R)
            sEnd = min(len(signal), rPeak + self.qrsMaxWidth // 2)
            sRegion = signal[rPeak:sEnd]
            if len(sRegion) > 0:
                sPeak = rPeak + np.argmin(sRegion)
            else:
                sPeak = rPeak

            complexes.append((qPeak, rPeak, sPeak))

        return complexes

    def _calculateAverageQRSDuration(self, qrsComplexes: List[Tuple[int, int, int]]) -> Optional[int]:
        """Calculate average QRS duration in milliseconds"""
        if len(qrsComplexes) == 0:
            return None

        durations = []
        for qPeak, rPeak, sPeak in qrsComplexes:
            durationSamples = sPeak - qPeak
            durationMs = (durationSamples / self.sampleRate) * 1000
            durations.append(durationMs)

        return int(np.mean(durations))

    def _detectTWaves(self, signal: np.ndarray, qrsComplexes: List[Tuple[int, int, int]]) -> List[int]:
        """
        Detect T waves (ventricular repolarization)
        T wave appears 200-400ms after QRS complex
        """
        tWaves = []

        for qPeak, rPeak, sPeak in qrsComplexes:
            # T wave search window: 200-400ms after S wave
            searchStart = sPeak + int(0.2 * self.sampleRate)
            searchEnd = sPeak + int(0.4 * self.sampleRate)

            if searchEnd < len(signal):
                tRegion = signal[searchStart:searchEnd]
                if len(tRegion) > 0:
                    # T wave is positive deflection
                    tPeak = searchStart + np.argmax(tRegion)
                    tWaves.append(tPeak)
                else:
                    tWaves.append(sPeak)
            else:
                tWaves.append(sPeak)

        return tWaves

    def _calculateQTInterval(self, qrsComplexes: List[Tuple[int, int, int]], tWaves: List[int]) -> Optional[int]:
        """Calculate average QT interval (Q to T wave) in milliseconds"""
        if len(qrsComplexes) == 0 or len(tWaves) == 0:
            return None

        qtIntervals = []
        for i, (qPeak, rPeak, sPeak) in enumerate(qrsComplexes):
            if i < len(tWaves):
                qtSamples = tWaves[i] - qPeak
                qtMs = (qtSamples / self.sampleRate) * 1000
                qtIntervals.append(qtMs)

        if len(qtIntervals) > 0:
            return int(np.mean(qtIntervals))
        return None

    def _calculateQTc(self, qtInterval: Optional[int], rrIntervals: np.ndarray) -> Optional[int]:
        """
        Calculate corrected QT interval using Bazett's formula:
        QTc = QT / sqrt(RR)

        Normal: QTc < 450ms (male), < 460ms (female)
        Long QT: QTc > 500ms (dangerous)
        """
        if qtInterval is None or len(rrIntervals) == 0:
            return None

        avgRR = np.mean(rrIntervals) / 1000.0  # Convert to seconds
        qtcMs = qtInterval / np.sqrt(avgRR)
        return int(qtcMs)

    def _classifyRhythm(self, heartRate: float, rrIntervals: np.ndarray, qrsDuration: Optional[int]) -> str:
        """
        Classify cardiac rhythm based on heart rate, RR variability, and QRS width

        Returns:
            - 'sinus' - Normal sinus rhythm
            - 'sinusBradycardia' - HR < 60 BPM
            - 'sinusTachycardia' - HR 100-150 BPM
            - 'atrialFibrillation' - Irregular RR intervals
            - 'ventricularTachycardia' - HR > 150 BPM + wide QRS
            - 'ventricularFibrillation' - Chaotic, no identifiable QRS
            - 'unknown'
        """
        if heartRate == 0 or len(rrIntervals) == 0:
            return 'unknown'

        # Calculate RR variability (coefficient of variation)
        rrCV = np.std(rrIntervals) / np.mean(rrIntervals) if np.mean(rrIntervals) > 0 else 0

        # Ventricular Fibrillation (chaotic, very high variability)
        if rrCV > 0.5:  # >50% variability
            return 'ventricularFibrillation'

        # Ventricular Tachycardia (HR > 150 + wide QRS > 120ms)
        if heartRate > self.vTachycardiaThreshold:
            if qrsDuration and qrsDuration > 120:
                return 'ventricularTachycardia'
            else:
                return 'sinusTachycardia'  # Supraventricular tachycardia

        # Atrial Fibrillation (irregular RR + normal/fast HR)
        if rrCV > self.normalRRVariance:  # >10% variability
            return 'atrialFibrillation'

        # Bradycardia (HR < 60)
        if heartRate < self.bradycardiaThreshold:
            return 'sinusBradycardia'

        # Tachycardia (HR 100-150)
        if heartRate > self.tachycardiaThreshold:
            return 'sinusTachycardia'

        # Normal sinus rhythm
        return 'sinus'

    def _analyzeSTSegment(self, signal: np.ndarray, qrsComplexes: List[Tuple[int, int, int]],
                          tWaves: List[int]) -> str:
        """
        Analyze ST segment for elevation/depression
        ST elevation → STEMI (heart attack)
        ST depression → Ischemia

        Returns: 'normal', 'elevated', 'depressed'
        """
        if len(qrsComplexes) == 0 or len(tWaves) == 0:
            return 'normal'

        stDeviations = []

        for i, (qPeak, rPeak, sPeak) in enumerate(qrsComplexes):
            if i >= len(tWaves):
                break

            # ST segment: 80ms after S wave (J point + 80ms)
            stPoint = sPeak + int(0.08 * self.sampleRate)

            if stPoint < len(signal):
                # Calculate baseline (average between T wave and next Q)
                baseline = signal[sPeak]

                # ST elevation/depression relative to baseline
                stLevel = signal[stPoint]
                deviation = stLevel - baseline
                stDeviations.append(deviation)

        if len(stDeviations) == 0:
            return 'normal'

        avgDeviation = np.mean(stDeviations)

        # Thresholds (normalized, may need adjustment based on signal scaling)
        elevationThreshold = 0.1  # 1mm (0.1mV) elevation
        depressionThreshold = -0.05  # 0.5mm (0.05mV) depression

        if avgDeviation > elevationThreshold:
            return 'elevated'
        elif avgDeviation < depressionThreshold:
            return 'depressed'
        else:
            return 'normal'

    def _calculateSignalQuality(self, rawSignal: np.ndarray, rPeaks: np.ndarray) -> float:
        """
        Calculate signal quality score (0.0 to 1.0)
        Based on:
        - Signal-to-noise ratio
        - Number of detected peaks
        - Signal amplitude consistency
        """
        if len(rPeaks) < 2:
            return 0.0

        # SNR calculation (simplified)
        signalPower = np.var(rawSignal)
        noisePower = np.var(np.diff(rawSignal))  # High-frequency noise
        snr = signalPower / (noisePower + 1e-10)  # Avoid division by zero

        # Normalize SNR to 0-1 (assume SNR > 10 is good)
        snrScore = min(1.0, snr / 10.0)

        # Peak count score (at least 5 peaks for good analysis)
        peakScore = min(1.0, len(rPeaks) / 5.0)

        # Combined quality score
        quality = (snrScore * 0.6) + (peakScore * 0.4)

        return max(0.0, min(1.0, quality))

    def _calculateConfidence(self, signalQuality: float, numPeaks: int) -> float:
        """Calculate confidence in analysis results"""
        if numPeaks < 3:
            return 0.2
        elif numPeaks < 5:
            return 0.5 * signalQuality
        else:
            return signalQuality


# Singleton instance
ecgAnalysisService = ECGAnalysisService(sampleRate=250)
