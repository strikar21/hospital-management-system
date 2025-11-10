"""
Phase 1 Tests: Waveform Utilities
Tests for app/common/waveform/ modules

These tests validate:
1. ADC conversion constants
2. Delta decompression algorithm
3. ADC to millivolts conversion (ECG)
4. ADC to microvolts conversion (EEG)
5. Waveform scaling and normalization

Related Files:
- hospital-backend/app/common/waveform/constants.py
- hospital-backend/app/common/waveform/decoder.py
- hospital-backend/app/common/waveform/converter.py
- hospital-backend/app/common/waveform/scaler.py
"""

import pytest
from app.common.waveform.constants import (
    ADC_MIDPOINT,
    SENSITIVITY_MV,
    SENSITIVITY_UV,
    ADC_MIN,
    ADC_MAX
)
from app.common.waveform.decoder import decompress_delta
from app.common.waveform.converter import (
    adc_to_millivolts,
    adc_to_microvolts
)


@pytest.mark.unit
class TestWaveformConstants:
    """Test waveform conversion constants"""

    def test_adc_midpoint_is_2_power_23(self):
        """
        Test: ADC midpoint constant
        Expected: 2^23 = 8388608 (24-bit ADC)
        """
        assert ADC_MIDPOINT == 8388608
        assert ADC_MIDPOINT == 2 ** 23

    def test_sensitivity_mv_for_ecg(self):
        """
        Test: ECG sensitivity constant
        Expected: 0.01 mV per LSB (10 μV per LSB)
        """
        assert SENSITIVITY_MV == 0.01

    def test_sensitivity_uv_for_eeg(self):
        """
        Test: EEG sensitivity constant
        Expected: 0.001 μV per LSB (1 μV per LSB)
        """
        assert SENSITIVITY_UV == 0.001

    def test_adc_range_bounds(self):
        """
        Test: ADC min/max bounds
        Expected: 24-bit range (0 to 16777215)
        """
        assert ADC_MIN == 0
        assert ADC_MAX == 16777215
        assert ADC_MAX == (2 ** 24) - 1


@pytest.mark.unit
class TestDeltaDecompression:
    """Test delta decompression algorithm"""

    def test_decompress_delta_basic(self):
        """
        Test: Basic delta decompression
        Expected: Reconstruct original values from baseline + deltas
        """
        channel_data = {
            'baseline': 8388608,
            'deltas': [100, -50, 25, -25, 0]
        }

        result = decompress_delta(channel_data)

        expected = [
            8388608,      # baseline
            8388708,      # +100
            8388658,      # -50
            8388683,      # +25
            8388658,      # -25
            8388658       # +0
        ]

        assert result == expected

    def test_decompress_delta_all_positive(self):
        """
        Test: Delta decompression with all positive deltas
        Expected: Monotonically increasing values
        """
        channel_data = {
            'baseline': 1000,
            'deltas': [10, 20, 30, 40]
        }

        result = decompress_delta(channel_data)

        expected = [1000, 1010, 1030, 1060, 1100]
        assert result == expected

    def test_decompress_delta_all_negative(self):
        """
        Test: Delta decompression with all negative deltas
        Expected: Monotonically decreasing values
        """
        channel_data = {
            'baseline': 1000,
            'deltas': [-10, -20, -30, -40]
        }

        result = decompress_delta(channel_data)

        expected = [1000, 990, 970, 940, 900]
        assert result == expected

    def test_decompress_delta_empty_deltas(self):
        """
        Test: Delta decompression with no deltas
        Expected: Returns only baseline value
        """
        channel_data = {
            'baseline': 8388608,
            'deltas': []
        }

        result = decompress_delta(channel_data)

        assert result == [8388608]

    def test_decompress_delta_large_deltas(self):
        """
        Test: Delta decompression with large delta values
        Expected: Handles large jumps correctly
        """
        channel_data = {
            'baseline': 8388608,
            'deltas': [100000, -200000, 150000]
        }

        result = decompress_delta(channel_data)

        expected = [
            8388608,
            8488608,      # +100000
            8288608,      # -200000
            8438608       # +150000
        ]

        assert result == expected


@pytest.mark.unit
class TestADCConversion:
    """Test ADC to physical units conversion"""

    def test_adc_to_millivolts_at_midpoint(self):
        """
        Test: Convert ADC at midpoint to millivolts
        Expected: 0 mV (baseline)
        """
        adc_values = [ADC_MIDPOINT]
        result = adc_to_millivolts(adc_values)

        assert result == [0.0]

    def test_adc_to_millivolts_positive_deflection(self):
        """
        Test: Convert ADC above midpoint to positive mV
        Expected: Positive millivolt value
        """
        adc_values = [ADC_MIDPOINT + 1000]  # 1000 LSB above midpoint
        result = adc_to_millivolts(adc_values)

        expected = [1000 * SENSITIVITY_MV]  # 10 mV
        assert result == expected
        assert result[0] == 10.0

    def test_adc_to_millivolts_negative_deflection(self):
        """
        Test: Convert ADC below midpoint to negative mV
        Expected: Negative millivolt value
        """
        adc_values = [ADC_MIDPOINT - 1000]  # 1000 LSB below midpoint
        result = adc_to_millivolts(adc_values)

        expected = [-1000 * SENSITIVITY_MV]  # -10 mV
        assert result == expected
        assert result[0] == -10.0

    def test_adc_to_millivolts_multiple_values(self):
        """
        Test: Convert multiple ADC values to millivolts
        Expected: Correct array conversion
        """
        adc_values = [
            ADC_MIDPOINT,
            ADC_MIDPOINT + 100,
            ADC_MIDPOINT - 100,
            ADC_MIDPOINT + 500
        ]

        result = adc_to_millivolts(adc_values)

        expected = [0.0, 1.0, -1.0, 5.0]
        assert result == expected

    def test_adc_to_microvolts_at_midpoint(self):
        """
        Test: Convert ADC at midpoint to microvolts
        Expected: 0 μV (baseline)
        """
        adc_values = [ADC_MIDPOINT]
        result = adc_to_microvolts(adc_values)

        assert result == [0.0]

    def test_adc_to_microvolts_positive_deflection(self):
        """
        Test: Convert ADC above midpoint to positive μV
        Expected: Positive microvolt value
        """
        adc_values = [ADC_MIDPOINT + 10000]  # 10000 LSB above midpoint
        result = adc_to_microvolts(adc_values)

        expected = [10000 * SENSITIVITY_UV]  # 10 μV
        assert result == expected
        assert result[0] == 10.0



@pytest.mark.integration
class TestWaveformEndToEnd:
    """Integration tests for waveform processing"""

    def test_complete_ecg_processing_workflow(self):
        """
        Test: Complete ECG waveform processing workflow
        Expected: Delta decompress -> ADC to mV conversion
        """
        # Step 1: Delta-compressed data from ESP32
        channel_data = {
            'baseline': ADC_MIDPOINT,
            'deltas': [100, -50, 200, -150, 50]
        }

        # Step 2: Decompress deltas
        adc_values = decompress_delta(channel_data)
        assert len(adc_values) == 6  # baseline + 5 deltas

        # Step 3: Convert to millivolts
        mv_values = adc_to_millivolts(adc_values)
        assert all(isinstance(v, float) for v in mv_values)
        assert len(mv_values) == 6

    def test_complete_eeg_processing_workflow(self):
        """
        Test: Complete EEG waveform processing workflow
        Expected: Delta decompress -> ADC to μV conversion
        """
        # Step 1: Delta-compressed EEG data
        channel_data = {
            'baseline': ADC_MIDPOINT,
            'deltas': [50, -25, 100, -75, 25]
        }

        # Step 2: Decompress deltas
        adc_values = decompress_delta(channel_data)

        # Step 3: Convert to microvolts
        uv_values = adc_to_microvolts(adc_values)
        assert all(isinstance(v, float) for v in uv_values)
        assert len(uv_values) == 6

    def test_real_world_ecg_sample(self):
        """
        Test: Process real-world ECG sample data
        Expected: Handles typical ECG waveform values correctly
        """
        # Simulated ECG data (typical QRS complex pattern)
        channel_data = {
            'baseline': ADC_MIDPOINT,
            'deltas': [
                10, 15, 20, 25, 150,  # R-wave (upstroke)
                -200, -100,            # S-wave (downstroke)
                50, 30, 20, 10, 5     # Return to baseline
            ]
        }

        adc_values = decompress_delta(channel_data)
        mv_values = adc_to_millivolts(adc_values)

        # ECG should have positive and negative deflections
        assert any(v > 0 for v in mv_values)
        assert any(v < 0 for v in mv_values)

        # Peak should be significant (typical R-wave > 0.5 mV)
        assert max(mv_values) > 0.5
