"""
EEG Analysis Service
Medical-grade EEG analysis with FFT power spectrum and seizure detection
STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
"""

import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EEGAnalysisResult:
    """Results from EEG analysis"""
    # Power spectrum (band powers in μV²)
    alphaPower: Optional[float] = None  # 8-13 Hz (relaxation, eyes closed)
    betaPower: Optional[float] = None   # 13-30 Hz (active thinking, focus)
    thetaPower: Optional[float] = None  # 4-8 Hz (drowsiness, meditation)
    deltaPower: Optional[float] = None  # 0.5-4 Hz (deep sleep)
    gammaPower: Optional[float] = None  # 30-100 Hz (cognitive processing)

    # Frequency analysis
    dominantFrequency: Optional[float] = None  # Peak frequency in Hz
    spectralEdge: Optional[float] = None       # 95% power cutoff frequency

    # Clinical indicators
    seizureActivity: Optional[bool] = None     # Detected seizure patterns
    seizureConfidence: Optional[float] = None  # Confidence in seizure detection

    # Band power ratios (clinical indicators)
    alphaBetaRatio: Optional[float] = None     # Relaxation indicator
    thetaBetaRatio: Optional[float] = None     # Attention/ADHD indicator
    deltaAlphaRatio: Optional[float] = None    # Alertness indicator

    # Quality metrics
    signalQuality: Optional[float] = None      # 0.0 to 1.0
    confidence: Optional[float] = None         # Analysis confidence


class EEGAnalysisService:
    """
    EEG Analysis Service implementing medical-grade algorithms:
    - FFT power spectrum analysis
    - Band power calculation (delta, theta, alpha, beta, gamma)
    - Seizure detection (spike-wave patterns)
    - Asymmetry analysis (left vs right hemisphere)
    """

    def __init__(self, sampleRate: int = 250):
        """
        Initialize EEG analysis service

        Args:
            sampleRate: Sample rate in Hz (default 250 Hz for ADS1298)
        """
        self.sampleRate = sampleRate
        self.nyquistFreq = sampleRate / 2.0

        # EEG frequency bands (Hz)
        self.deltaBand = (0.5, 4.0)    # Deep sleep
        self.thetaBand = (4.0, 8.0)    # Drowsiness, meditation
        self.alphaBand = (8.0, 13.0)   # Relaxed, eyes closed
        self.betaBand = (13.0, 30.0)   # Active thinking, focus
        self.gammaBand = (30.0, 100.0) # Cognitive processing

        # Seizure detection parameters
        self.spikeThreshold = 3.0  # Z-score threshold for spike detection
        self.spikeMinWidth = int(0.02 * sampleRate)  # 20ms minimum spike width
        self.spikeMaxWidth = int(0.07 * sampleRate)  # 70ms maximum spike width
        self.seizureMinSpikes = 5  # Minimum spikes to consider seizure

        # Filter parameters
        self.notchFreq = 50.0  # Hz (power line interference - 50Hz in India, 60Hz in US)
        self.notchQ = 30.0     # Quality factor for notch filter

        logger.info(f"✅ EEG Analysis Service initialized (sample rate: {sampleRate} Hz)")

    def analyzeEEG(self, waveformData: Dict[str, any], mode: str = 'eeg') -> EEGAnalysisResult:
        """
        Analyze EEG waveform data and return comprehensive analysis

        Args:
            waveformData: Dictionary with EEG channel data
            mode: 'ecg' or 'eeg' (must be 'eeg')

        Returns:
            EEGAnalysisResult with all calculated metrics
        """
        if mode != 'eeg':
            logger.warning(f"⚠️ Skipping EEG analysis - mode is {mode}, not 'eeg'")
            return EEGAnalysisResult()

        try:
            # Extract frontal channel (Fp1-Fp2 or F3-C3)
            channelData = self._extractFrontalChannel(waveformData)

            if channelData is None or len(channelData) < self.sampleRate:
                logger.warning("⚠️ Insufficient EEG data for analysis")
                return EEGAnalysisResult(signalQuality=0.0, confidence=0.0)

            # Step 1: Preprocess signal (notch filter + bandpass)
            filteredSignal = self._preprocessSignal(channelData)

            # Step 2: Calculate power spectrum using FFT
            frequencies, powerSpectrum = self._calculatePowerSpectrum(filteredSignal)

            # Step 3: Calculate band powers
            deltaPower = self._calculateBandPower(frequencies, powerSpectrum, self.deltaBand)
            thetaPower = self._calculateBandPower(frequencies, powerSpectrum, self.thetaBand)
            alphaPower = self._calculateBandPower(frequencies, powerSpectrum, self.alphaBand)
            betaPower = self._calculateBandPower(frequencies, powerSpectrum, self.betaBand)
            gammaPower = self._calculateBandPower(frequencies, powerSpectrum, self.gammaBand)

            # Step 4: Calculate dominant frequency
            dominantFreq = self._findDominantFrequency(frequencies, powerSpectrum)

            # Step 5: Calculate spectral edge frequency (95% power)
            spectralEdge = self._calculateSpectralEdge(frequencies, powerSpectrum)

            # Step 6: Detect seizure activity (spike-wave patterns)
            seizureDetected, seizureConfidence = self._detectSeizureActivity(filteredSignal)

            # Step 7: Calculate band power ratios
            alphaBetaRatio = alphaPower / (betaPower + 1e-10) if betaPower > 0 else 0.0
            thetaBetaRatio = thetaPower / (betaPower + 1e-10) if betaPower > 0 else 0.0
            deltaAlphaRatio = deltaPower / (alphaPower + 1e-10) if alphaPower > 0 else 0.0

            # Step 8: Calculate signal quality
            signalQuality = self._calculateSignalQuality(channelData, filteredSignal)
            confidence = self._calculateConfidence(signalQuality, len(channelData))

            result = EEGAnalysisResult(
                alphaPower=round(alphaPower, 2),
                betaPower=round(betaPower, 2),
                thetaPower=round(thetaPower, 2),
                deltaPower=round(deltaPower, 2),
                gammaPower=round(gammaPower, 2),
                dominantFrequency=round(dominantFreq, 2),
                spectralEdge=round(spectralEdge, 2),
                seizureActivity=seizureDetected,
                seizureConfidence=round(seizureConfidence, 2),
                alphaBetaRatio=round(alphaBetaRatio, 2),
                thetaBetaRatio=round(thetaBetaRatio, 2),
                deltaAlphaRatio=round(deltaAlphaRatio, 2),
                signalQuality=round(signalQuality, 2),
                confidence=round(confidence, 2)
            )

            logger.info(f"✅ EEG Analysis complete: Alpha={alphaPower:.1f} μV², "
                       f"Seizure={'YES' if seizureDetected else 'NO'}")
            return result

        except Exception as e:
            logger.error(f"❌ EEG analysis failed: {e}", exc_info=True)
            return EEGAnalysisResult(signalQuality=0.0, confidence=0.0)

    def _extractFrontalChannel(self, waveformData: Dict) -> Optional[np.ndarray]:
        """
        Extract frontal EEG channel (best for seizure detection)
        Priority: Fp1, Fp2, F3, F4
        """
        try:
            # Try frontal channels first
            if 'frontal' in waveformData:
                frontalChannels = waveformData['frontal']
                for channelName in ['fp1', 'fp2', 'f3', 'f4']:
                    if channelName in frontalChannels:
                        channel = frontalChannels[channelName]

                        # Handle delta encoding
                        if isinstance(channel, dict) and 'baseline' in channel and 'deltas' in channel:
                            baseline = channel['baseline']
                            deltas = np.array(channel['deltas'])
                            signal = np.cumsum(np.concatenate([[baseline], deltas]))
                            return signal
                        elif isinstance(channel, list):
                            return np.array(channel)

            # Fallback: try central channels
            if 'central' in waveformData:
                centralChannels = waveformData['central']
                for channelName in ['c3', 'c4']:
                    if channelName in centralChannels:
                        channel = centralChannels[channelName]
                        if isinstance(channel, list):
                            return np.array(channel)

            # Last resort: use first available channel
            if isinstance(waveformData, (list, np.ndarray)):
                return np.array(waveformData)

            logger.warning("⚠️ Could not extract frontal channel from EEG data")
            return None

        except Exception as e:
            logger.error(f"❌ Error extracting EEG channel: {e}")
            return None

    def _preprocessSignal(self, rawSignal: np.ndarray) -> np.ndarray:
        """
        Preprocess EEG signal:
        1. Notch filter at 50Hz (remove power line interference for India)
        2. Bandpass filter 0.5-100Hz (remove DC drift and high-freq noise)
        """
        # Notch filter at 50Hz (India power line frequency)
        b_notch, a_notch = signal.iirnotch(self.notchFreq, self.notchQ, self.sampleRate)
        notched = signal.filtfilt(b_notch, a_notch, rawSignal)

        # Bandpass filter 0.5-100Hz
        sos = signal.butter(4, [0.5, 100.0], btype='bandpass', fs=self.sampleRate, output='sos')
        filtered = signal.sosfilt(sos, notched)

        return filtered

    def _calculatePowerSpectrum(self, signal_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate power spectrum using FFT
        Returns: (frequencies, power_spectrum)
        """
        # Apply Hamming window to reduce spectral leakage
        windowed = signal_data * np.hamming(len(signal_data))

        # Compute FFT
        fftValues = fft(windowed)
        frequencies = fftfreq(len(signal_data), 1.0 / self.sampleRate)

        # Get positive frequencies only
        positiveMask = frequencies > 0
        frequencies = frequencies[positiveMask]

        # Calculate power spectrum (magnitude squared)
        powerSpectrum = np.abs(fftValues[positiveMask]) ** 2

        return frequencies, powerSpectrum

    def _calculateBandPower(self, frequencies: np.ndarray, powerSpectrum: np.ndarray,
                           band: Tuple[float, float]) -> float:
        """
        Calculate total power in a specific frequency band

        Args:
            frequencies: Frequency array from FFT
            powerSpectrum: Power spectrum from FFT
            band: Frequency band (minHz, maxHz)

        Returns:
            Total power in band (μV²)
        """
        minFreq, maxFreq = band

        # Find indices within band
        bandMask = (frequencies >= minFreq) & (frequencies <= maxFreq)

        if not np.any(bandMask):
            return 0.0

        # Integrate power over band (trapezoidal rule)
        bandPower = np.trapz(powerSpectrum[bandMask], frequencies[bandMask])

        return bandPower

    def _findDominantFrequency(self, frequencies: np.ndarray, powerSpectrum: np.ndarray) -> float:
        """Find frequency with maximum power (peak frequency)"""
        # Focus on 0.5-50Hz range (typical EEG range)
        mask = (frequencies >= 0.5) & (frequencies <= 50.0)

        if not np.any(mask):
            return 0.0

        filteredFreqs = frequencies[mask]
        filteredPower = powerSpectrum[mask]

        peakIdx = np.argmax(filteredPower)
        dominantFreq = filteredFreqs[peakIdx]

        return dominantFreq

    def _calculateSpectralEdge(self, frequencies: np.ndarray, powerSpectrum: np.ndarray) -> float:
        """
        Calculate spectral edge frequency (SEF95)
        Frequency below which 95% of total power is contained
        """
        # Focus on 0.5-50Hz range
        mask = (frequencies >= 0.5) & (frequencies <= 50.0)

        if not np.any(mask):
            return 0.0

        filteredFreqs = frequencies[mask]
        filteredPower = powerSpectrum[mask]

        # Calculate cumulative power
        totalPower = np.sum(filteredPower)
        if totalPower == 0:
            return 0.0

        cumulativePower = np.cumsum(filteredPower)
        cumulativeRatio = cumulativePower / totalPower

        # Find frequency where cumulative power reaches 95%
        sef95Idx = np.argmax(cumulativeRatio >= 0.95)
        sef95 = filteredFreqs[sef95Idx]

        return sef95

    def _detectSeizureActivity(self, signal: np.ndarray) -> Tuple[bool, float]:
        """
        Detect seizure activity using spike detection
        Seizures show:
        - High-amplitude spikes (>3 standard deviations)
        - Rhythmic spike-wave patterns (3Hz for absence seizures)
        - Sustained high-frequency activity

        Returns: (seizureDetected, confidence)
        """
        # Calculate z-score (standardized signal)
        mean = np.mean(signal)
        std = np.std(signal)
        if std == 0:
            return False, 0.0

        zScore = (signal - mean) / std

        # Detect spikes (z-score > threshold)
        spikes = np.abs(zScore) > self.spikeThreshold
        spikeIndices = np.where(spikes)[0]

        if len(spikeIndices) < self.seizureMinSpikes:
            return False, 0.0

        # Check spike widths (20-70ms for epileptic spikes)
        validSpikes = 0
        spikeGroups = np.split(spikeIndices, np.where(np.diff(spikeIndices) > 10)[0] + 1)

        for group in spikeGroups:
            if len(group) >= self.spikeMinWidth and len(group) <= self.spikeMaxWidth:
                validSpikes += 1

        if validSpikes < self.seizureMinSpikes:
            return False, 0.1

        # Calculate inter-spike intervals
        if len(spikeIndices) > 1:
            isiSamples = np.diff(spikeIndices)
            isiMs = (isiSamples / self.sampleRate) * 1000

            # Check for rhythmic pattern (3Hz = 333ms interval for absence seizures)
            # Or fast activity (10-20Hz = 50-100ms for tonic-clonic)
            rhythmic3Hz = np.sum((isiMs > 300) & (isiMs < 400)) > 5  # Absence seizure
            fastActivity = np.sum((isiMs > 50) & (isiMs < 150)) > 10  # Tonic-clonic

            if rhythmic3Hz or fastActivity:
                # High confidence seizure detection
                confidence = min(1.0, validSpikes / (self.seizureMinSpikes * 3))
                return True, confidence

        # Moderate confidence (many spikes but no clear rhythm)
        if validSpikes >= self.seizureMinSpikes * 2:
            return True, 0.6

        return False, 0.3

    def _calculateSignalQuality(self, rawSignal: np.ndarray, filteredSignal: np.ndarray) -> float:
        """
        Calculate EEG signal quality (0.0 to 1.0)
        Based on:
        - Signal variance (should be moderate, not flatline or saturated)
        - Noise level (high-frequency content)
        - Artifact detection (extreme values)
        """
        # Check for flatline
        if np.std(rawSignal) < 0.1:
            return 0.0

        # Check for saturation (values near ADC limits)
        # Assuming ADS1298 with ±2.4V range and 24-bit resolution
        saturationThreshold = 2.0  # Volts
        if np.max(np.abs(rawSignal)) > saturationThreshold:
            return 0.3

        # Calculate SNR
        signalPower = np.var(filteredSignal)
        noisePower = np.var(rawSignal - filteredSignal)
        snr = signalPower / (noisePower + 1e-10)

        # Normalize SNR to 0-1 (SNR > 5 is good for EEG)
        snrScore = min(1.0, snr / 5.0)

        # Check for extreme artifacts (z-score > 10)
        zScore = (rawSignal - np.mean(rawSignal)) / (np.std(rawSignal) + 1e-10)
        artifactCount = np.sum(np.abs(zScore) > 10)
        artifactScore = max(0.0, 1.0 - (artifactCount / len(rawSignal)))

        # Combined quality score
        quality = (snrScore * 0.7) + (artifactScore * 0.3)

        return max(0.0, min(1.0, quality))

    def _calculateConfidence(self, signalQuality: float, dataLength: int) -> float:
        """Calculate confidence in analysis results"""
        # Need at least 2 seconds of data for reliable analysis
        minSamples = 2 * self.sampleRate

        if dataLength < minSamples:
            return 0.2
        elif dataLength < minSamples * 2:
            return 0.5 * signalQuality
        else:
            return signalQuality


# Singleton instance
eegAnalysisService = EEGAnalysisService(sampleRate=250)
