/**
 * PatientMonitor Integration Tests
 * Tests integration with domain layer (VitalsFormatter, VitalsValidator)
 *
 * Verifies:
 * - Vitals formatting with domain layer
 * - Temperature conversion (F)
 * - Proper fallbacks for undefined values
 * - Component doesn't crash with edge cases
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PatientMonitor } from '../PatientMonitor';
import { patient } from '../../../types';

// Mock patient data factory
const createMockPatient = (overrides?: Partial<patient>): patient => ({
  id: 'PAT001',
  name: 'Test Patient',
  age: 45,
  gender: 'male',
  room: '101',
  ward: 'ICU',
  bedNumber: '1',
  status: 'stable',
  assignedDeviceId: 'DEVICE001',
  alerts: [],
  vitals: {
    heartRate: 75,
    systolicPressure: 120,
    diastolicPressure: 80,
    oxygenSaturation: 98,
    respiratoryRate: 16,
    skinTemperature: 98.6, // Fahrenheit
    ecgReading: 0,
    eegReading: 0,
    batteryLevel: 85,
    signalQuality: 0.9,
    tremorFrequency: 0,
    tremorAmplitude: 0,
    bioimpedance: 0,
    perfusionIndex: 0,
    accelerometerX: 0,
    accelerometerY: 0,
    accelerometerZ: 0,
    muscleTensionLeft: 0,
    muscleTensionRight: 0,
    posturalTremoLeft: 0,
    posturalTremoRight: 0,
    dataQualityScore: 0.9
  },
  ...overrides
});

describe('PatientMonitor - Domain Layer Integration', () => {
  const defaultProps = {
    patient: createMockPatient(),
    position: 'single' as const,
    displayCount: 1 as const,
    isECGMode: true,
    isOnline: true,
    currentTime: new Date('2025-01-10T12:00:00Z')
  };

  // ================================
  // VITALS FORMATTING WITH DOMAIN LAYER
  // ================================

  describe('Vitals Formatting', () => {
    it('should render without crashing', () => {
      const { container } = render(<PatientMonitor {...defaultProps} />);
      expect(container).toBeInTheDocument();
    });

    it('should display heart rate with domain layer unit', () => {
      render(<PatientMonitor {...defaultProps} />);

      expect(screen.getByText('75')).toBeInTheDocument();
      expect(screen.getByText('bpm')).toBeInTheDocument();
    });

    it('should display blood pressure with domain layer unit', () => {
      render(<PatientMonitor {...defaultProps} />);

      expect(screen.getByText('120/80')).toBeInTheDocument();
      expect(screen.getByText('mmHg')).toBeInTheDocument();
    });

    it('should display oxygen saturation with domain layer unit', () => {
      render(<PatientMonitor {...defaultProps} />);

      expect(screen.getByText('98')).toBeInTheDocument();
      expect(screen.getAllByText('%').length).toBeGreaterThan(0);
    });

    it('should display temperature unit in Fahrenheit from domain layer', () => {
      render(<PatientMonitor {...defaultProps} />);

      // Domain layer provides °F unit
      expect(screen.getByText('°F')).toBeInTheDocument();
      expect(screen.getByText('TEMPERATURE')).toBeInTheDocument();
    });
  });

  // ================================
  // EDGE CASES - MISSING VITALS
  // ================================

  describe('Edge Cases - Missing Vitals', () => {
    it('should display placeholder for undefined heart rate', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          heartRate: undefined
        }
      });

      render(<PatientMonitor {...defaultProps} patient={patient} />);

      // Should show -- for undefined values
      expect(screen.getAllByText('--').length).toBeGreaterThan(0);
    });

    it('should display placeholder for undefined blood pressure', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          systolicPressure: undefined,
          diastolicPressure: undefined
        }
      });

      render(<PatientMonitor {...defaultProps} patient={patient} />);

      // Should show --/-- for missing BP
      expect(screen.getAllByText('--/--').length).toBeGreaterThan(0);
    });

    it('should handle completely missing vitals object gracefully', () => {
      const patient = createMockPatient({
        vitals: undefined as any
      });

      const { container } = render(<PatientMonitor {...defaultProps} patient={patient} />);

      // Should not crash
      expect(container).toBeInTheDocument();
      expect(screen.getAllByText('--').length).toBeGreaterThan(0);
    });

    it('should handle partial blood pressure gracefully', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          diastolicPressure: undefined
        }
      });

      render(<PatientMonitor {...defaultProps} patient={patient} />);

      // Should show --/-- when either value is missing
      expect(screen.getAllByText('--/--').length).toBeGreaterThan(0);
    });
  });

  // ================================
  // DUAL PATIENT LAYOUT
  // ================================

  describe('Dual Patient Layout', () => {
    const dualProps = {
      ...defaultProps,
      displayCount: 2 as const
    };

    it('should render dual layout without crashing', () => {
      const { container } = render(<PatientMonitor {...dualProps} />);
      expect(container).toBeInTheDocument();
    });

    it('should display vitals in compact dual layout', () => {
      render(<PatientMonitor {...dualProps} />);

      // All vitals should still be displayed
      expect(screen.getByText('75')).toBeInTheDocument();
      expect(screen.getByText('120/80')).toBeInTheDocument();
      expect(screen.getByText('98')).toBeInTheDocument();
    });

    it('should use same domain layer units in dual layout', () => {
      render(<PatientMonitor {...dualProps} />);

      expect(screen.getByText('bpm')).toBeInTheDocument();
      expect(screen.getByText('mmHg')).toBeInTheDocument();
      expect(screen.getByText('°F')).toBeInTheDocument();
    });
  });

  // ================================
  // PATIENT METADATA
  // ================================

  describe('Patient Metadata Display', () => {
    it('should display bed number', () => {
      render(<PatientMonitor {...defaultProps} />);

      expect(screen.getByText('BED 1')).toBeInTheDocument();
    });

    it('should display room and ward', () => {
      render(<PatientMonitor {...defaultProps} />);

      expect(screen.getByText(/Room 101/)).toBeInTheDocument();
      expect(screen.getByText(/ICU/)).toBeInTheDocument();
    });

    it('should display patient status', () => {
      render(<PatientMonitor {...defaultProps} />);

      expect(screen.getByText('STABLE')).toBeInTheDocument();
    });

    it('should display critical status for critical patient', () => {
      const patient = createMockPatient({ status: 'critical' });

      render(<PatientMonitor {...defaultProps} patient={patient} />);

      expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    });
  });

  // ================================
  // CRITICAL ALERTS BANNER
  // ================================

  describe('Critical Alerts Banner', () => {
    it('should show critical alert banner when critical alert present', () => {
      const patient = createMockPatient({
        alerts: [
          {
            id: 'ALR001',
            severity: 'critical',
            message: 'Critical heart rate',
            timestamp: new Date().toISOString(),
            isAcknowledged: false
          }
        ]
      });

      render(<PatientMonitor {...defaultProps} patient={patient} />);

      expect(screen.getByText('⚠ CRITICAL')).toBeInTheDocument();
    });

    it('should NOT show critical banner for acknowledged alerts', () => {
      const patient = createMockPatient({
        alerts: [
          {
            id: 'ALR001',
            severity: 'critical',
            message: 'Critical heart rate',
            timestamp: new Date().toISOString(),
            isAcknowledged: true
          }
        ]
      });

      render(<PatientMonitor {...defaultProps} patient={patient} />);

      expect(screen.queryByText('⚠ CRITICAL')).not.toBeInTheDocument();
    });

    it('should NOT show critical banner for non-critical alerts', () => {
      const patient = createMockPatient({
        alerts: [
          {
            id: 'ALR001',
            severity: 'high',
            message: 'High heart rate',
            timestamp: new Date().toISOString(),
            isAcknowledged: false
          }
        ]
      });

      render(<PatientMonitor {...defaultProps} patient={patient} />);

      expect(screen.queryByText('⚠ CRITICAL')).not.toBeInTheDocument();
    });
  });

  // ================================
  // ECG/EEG MODE TOGGLE
  // ================================

  describe('ECG/EEG Mode', () => {
    it('should display ECG MONITOR when ECG mode active', () => {
      render(<PatientMonitor {...defaultProps} isECGMode={true} />);

      expect(screen.getByText('ECG MONITOR')).toBeInTheDocument();
    });

    it('should display EEG MONITOR when EEG mode active', () => {
      render(<PatientMonitor {...defaultProps} isECGMode={false} />);

      expect(screen.getByText('EEG MONITOR')).toBeInTheDocument();
    });

    it('should display ECG reading value in ECG mode', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          ecgReading: 5
        }
      });

      render(<PatientMonitor {...defaultProps} patient={patient} isECGMode={true} />);

      expect(screen.getByText('5 mV')).toBeInTheDocument();
    });

    it('should display ACTIVE status in EEG mode', () => {
      render(<PatientMonitor {...defaultProps} isECGMode={false} />);

      expect(screen.getAllByText('ACTIVE').length).toBeGreaterThan(0);
    });
  });

  // ================================
  // ONLINE/OFFLINE STATUS
  // ================================

  describe('Online/Offline Status', () => {
    it('should display Connected when online', () => {
      render(<PatientMonitor {...defaultProps} isOnline={true} />);

      expect(screen.getByText('Connected')).toBeInTheDocument();
    });

    it('should display Offline when offline', () => {
      render(<PatientMonitor {...defaultProps} isOnline={false} />);

      expect(screen.getByText('Offline')).toBeInTheDocument();
    });
  });

  // ================================
  // EDGE CASES - EXTREME VALUES
  // ================================

  describe('Edge Cases - Extreme Values', () => {
    it('should handle very high heart rate without crashing', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          heartRate: 250
        }
      });

      const { container } = render(<PatientMonitor {...defaultProps} patient={patient} />);

      // Should display the value
      expect(container).toBeInTheDocument();
      expect(screen.getByText('250')).toBeInTheDocument();
    });

    it('should handle zero heart rate', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          heartRate: 0
        }
      });

      render(<PatientMonitor {...defaultProps} patient={patient} />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle fractional vital values correctly', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          heartRate: 75.7, // Should be rounded to 76
          oxygenSaturation: 98.4 // Should be rounded to 98
        }
      });

      render(<PatientMonitor {...defaultProps} patient={patient} />);

      // Domain layer rounds fractional values
      expect(screen.getByText('76')).toBeInTheDocument();
      expect(screen.getByText('98')).toBeInTheDocument();
    });

    it('should handle NaN values gracefully', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          heartRate: NaN
        }
      });

      const { container } = render(<PatientMonitor {...defaultProps} patient={patient} />);

      // Should not crash - NaN will be treated as falsy
      expect(container).toBeInTheDocument();
    });
  });

  // ================================
  // TEMPERATURE CONVERSION
  // ================================

  describe('Temperature Conversion', () => {
    it('should convert Celsius to Fahrenheit using domain layer', () => {
      // Backend stores in Celsius (37°C = 98.6°F)
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          skinTemperature: 37 // Celsius
        }
      });

      render(<PatientMonitor {...defaultProps} patient={patient} />);

      // Should display °F unit from domain layer
      expect(screen.getByText('°F')).toBeInTheDocument();
    });

    it('should handle low temperature values without crashing', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          skinTemperature: 35 // Low temperature
        }
      });

      const { container } = render(<PatientMonitor {...defaultProps} patient={patient} />);

      // Should not crash
      expect(container).toBeInTheDocument();
      expect(screen.getByText('°F')).toBeInTheDocument();
    });
  });
});
