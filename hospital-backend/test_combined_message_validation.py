"""
Test that Pydantic models correctly handle combined vitals+waveform messages
Run this to verify backend models accept 1-second combined messages
"""
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.neural_vitals import VitalsRealtimeMessage, WaveformSnapshotMessage

def test_ecg_combined_message():
    """Test combined message with ECG waveform"""
    print("\n" + "="*70)
    print("TEST 1: ECG Combined Message Validation")
    print("="*70)

    test_message = {
        "deviceId": "fit-00001",
        "patientId": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": datetime.now(),
        "mode": "ecg",
        "heartRate": 75,
        "respiratoryRate": 16,
        "skinTemperature": 36.5,
        "oxygenSaturation": 98,
        "batteryLevel": 85,
        "signalQuality": 0.95,
        "sampleRate": 250,
        "duration": 1,
        "compression": "delta",
        "ecgWaveform": {
            "limb": {
                "leadI": {"baseline": 8388608, "deltas": list(range(250))},
                "leadII": {"baseline": 8388610, "deltas": list(range(250))},
                "leadIII": {"baseline": 8388605, "deltas": list(range(250))}
            }
        }
    }

    try:
        # Step 1: Validate combined message
        print("\n[1/3] Validating VitalsRealtimeMessage with ECG waveform...")
        vitals = VitalsRealtimeMessage(**test_message)
        print(f"[PASS] VitalsRealtimeMessage validated successfully")
        print(f"   - Device ID: {vitals.deviceId}")
        print(f"   - Mode: {vitals.mode}")
        print(f"   - Heart Rate: {vitals.heartRate} BPM")
        print(f"   - Sample Rate: {vitals.sampleRate} Hz")
        print(f"   - Duration: {vitals.duration} sec")
        print(f"   - Has ECG Waveform: {vitals.ecgWaveform is not None}")
        print(f"   - Has EEG Waveform: {vitals.eegWaveform is not None}")

        # Step 2: Extract waveform for separate storage (simulating backend logic)
        print("\n[2/3] Extracting waveform data for separate storage...")
        waveform_data = {
            'deviceId': vitals.deviceId,
            'patientId': vitals.patientId,
            'timestamp': vitals.timestamp,
            'mode': vitals.mode,
            'sampleRate': vitals.sampleRate,
            'duration': vitals.duration,
            'compression': vitals.compression,
            'quality': vitals.quality.dict() if vitals.quality else None,
            'sequence': vitals.sequence,
            'metadata': vitals.metadata
        }

        # Add ECG waveform (this is the critical line 390-391 logic)
        if vitals.mode == 'ecg' and vitals.ecgWaveform:
            waveform_data['ecgWaveform'] = vitals.ecgWaveform.dict()

        # Step 3: Create WaveformSnapshotMessage
        print("[3/3] Creating WaveformSnapshotMessage...")
        waveform = WaveformSnapshotMessage(**waveform_data)
        print(f"[PASS] WaveformSnapshotMessage created successfully")
        print(f"   - Mode: {waveform.mode}")
        print(f"   - Sample Rate: {waveform.sampleRate} Hz")
        print(f"   - Duration: {waveform.duration} sec")
        print(f"   - Has ECG Waveform: {waveform.ecgWaveform is not None}")
        print(f"   - Has EEG Waveform: {waveform.eegWaveform is not None}")

        if waveform.ecgWaveform:
            print(f"   - ECG Lead I samples: {len(waveform.ecgWaveform.limb.leadI.deltas)}")

        print("\n" + "="*70)
        print("[PASS] TEST 1 PASSED: ECG combined message works correctly")
        print("="*70)
        return True

    except Exception as e:
        print(f"\n[FAIL] TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        print("="*70)
        return False

def test_eeg_combined_message():
    """Test combined message with EEG waveform"""
    print("\n" + "="*70)
    print("TEST 2: EEG Combined Message Validation")
    print("="*70)

    test_message = {
        "deviceId": "fit-00001",
        "patientId": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": datetime.now(),
        "mode": "eeg",
        "heartRate": 75,
        "respiratoryRate": 16,
        "skinTemperature": 36.5,
        "oxygenSaturation": 98,
        "batteryLevel": 85,
        "signalQuality": 0.95,
        "sampleRate": 250,
        "duration": 1,
        "compression": "delta",
        "eegWaveform": {
            "frontal": {
                "Fp1": {"baseline": 8388608, "deltas": list(range(250))},
                "Fp2": {"baseline": 8388610, "deltas": list(range(250))},
                "F3": {"baseline": 8388605, "deltas": list(range(250))},
                "F4": {"baseline": 8388607, "deltas": list(range(250))}
            },
            "central": {
                "C3": {"baseline": 8388600, "deltas": list(range(250))},
                "C4": {"baseline": 8388615, "deltas": list(range(250))}
            },
            "occipital": {
                "O1": {"baseline": 8388608, "deltas": list(range(250))},
                "O2": {"baseline": 8388611, "deltas": list(range(250))}
            }
        }
    }

    try:
        # Step 1: Validate combined message
        print("\n[1/3] Validating VitalsRealtimeMessage with EEG waveform...")
        vitals = VitalsRealtimeMessage(**test_message)
        print(f"[PASS] VitalsRealtimeMessage validated successfully")
        print(f"   - Device ID: {vitals.deviceId}")
        print(f"   - Mode: {vitals.mode}")
        print(f"   - Heart Rate: {vitals.heartRate} BPM")
        print(f"   - Sample Rate: {vitals.sampleRate} Hz")
        print(f"   - Duration: {vitals.duration} sec")
        print(f"   - Has ECG Waveform: {vitals.ecgWaveform is not None}")
        print(f"   - Has EEG Waveform: {vitals.eegWaveform is not None}")

        # Step 2: Extract waveform for separate storage (simulating backend logic)
        print("\n[2/3] Extracting waveform data for separate storage...")
        waveform_data = {
            'deviceId': vitals.deviceId,
            'patientId': vitals.patientId,
            'timestamp': vitals.timestamp,
            'mode': vitals.mode,
            'sampleRate': vitals.sampleRate,
            'duration': vitals.duration,
            'compression': vitals.compression,
            'quality': vitals.quality.dict() if vitals.quality else None,
            'sequence': vitals.sequence,
            'metadata': vitals.metadata
        }

        # Add EEG waveform (this is the critical line 392-393 logic - TESTING THE FIX)
        if vitals.mode == 'eeg' and vitals.eegWaveform:
            waveform_data['eegWaveform'] = vitals.eegWaveform.dict()  # ✅ Correct key after bug fix

        # Step 3: Create WaveformSnapshotMessage
        print("[3/3] Creating WaveformSnapshotMessage...")
        waveform = WaveformSnapshotMessage(**waveform_data)
        print(f"[PASS] WaveformSnapshotMessage created successfully")
        print(f"   - Mode: {waveform.mode}")
        print(f"   - Sample Rate: {waveform.sampleRate} Hz")
        print(f"   - Duration: {waveform.duration} sec")
        print(f"   - Has ECG Waveform: {waveform.ecgWaveform is not None}")
        print(f"   - Has EEG Waveform: {waveform.eegWaveform is not None}")

        if waveform.eegWaveform:
            print(f"   - EEG Fp1 samples: {len(waveform.eegWaveform.frontal.Fp1.deltas)}")

        print("\n" + "="*70)
        print("[PASS] TEST 2 PASSED: EEG combined message works correctly")
        print("="*70)
        return True

    except Exception as e:
        print(f"\n[FAIL] TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        print("="*70)
        return False

def test_vitals_only_message():
    """Test message with vitals but no waveform (should also work)"""
    print("\n" + "="*70)
    print("TEST 3: Vitals-Only Message (No Waveform)")
    print("="*70)

    test_message = {
        "deviceId": "fit-00001",
        "patientId": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": datetime.now(),
        "mode": "ecg",
        "heartRate": 75,
        "respiratoryRate": 16,
        "skinTemperature": 36.5,
        "oxygenSaturation": 98,
        "batteryLevel": 85,
        "signalQuality": 0.95
        # No sampleRate, duration, or waveform fields
    }

    try:
        print("\n[1/1] Validating VitalsRealtimeMessage without waveform...")
        vitals = VitalsRealtimeMessage(**test_message)
        print(f"[PASS] VitalsRealtimeMessage validated successfully")
        print(f"   - Mode: {vitals.mode}")
        print(f"   - Heart Rate: {vitals.heartRate} BPM")
        print(f"   - Sample Rate: {vitals.sampleRate}")
        print(f"   - Has Waveform: {vitals.ecgWaveform is not None or vitals.eegWaveform is not None}")

        print("\n" + "="*70)
        print("[PASS] TEST 3 PASSED: Vitals-only message works correctly")
        print("="*70)
        return True

    except Exception as e:
        print(f"\n[FAIL] TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        print("="*70)
        return False

if __name__ == "__main__":
    print("\n")
    print("=" * 70)
    print(" " * 10 + "PYDANTIC MODEL VALIDATION TEST SUITE")
    print(" " * 15 + "Combined Vitals + Waveform Messages")
    print("=" * 70)

    results = []

    results.append(("ECG Combined Message", test_ecg_combined_message()))
    results.append(("EEG Combined Message", test_eeg_combined_message()))
    results.append(("Vitals-Only Message", test_vitals_only_message()))

    # Summary
    print("\n\n")
    print("=" * 70)
    print(" " * 25 + "TEST SUMMARY")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"  {test_name:50} {status:15}")
        if not passed:
            all_passed = False

    print("=" * 70)

    if all_passed:
        print(" " * 15 + "ALL TESTS PASSED - MODELS ARE READY")
        print("=" * 70)
        sys.exit(0)
    else:
        print(" " * 12 + "SOME TESTS FAILED - MODELS NEED FIXING")
        print("=" * 70)
        sys.exit(1)
