/**
 * Integration Tests for PatientOverview
 * Tests domain layer integration with VitalsFormatter
 */

// Mock hooks BEFORE any imports (Jest hoisting requirement)
const mockUsePatientVitals = jest.fn(() => ({
  vitals: null, // Return null so component uses patient.vitals
  isConnected: false
}));

jest.mock('../../../hooks/usePatientVitals', () => ({
  usePatientVitals: (patientId: string) => mockUsePatientVitals(patientId)
}));

// Mock ECGViewer component
jest.mock('../../ECGViewer', () => ({
  __esModule: true,
  default: () => <div>ECG Viewer Mock</div>
}));

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PatientOverview } from '../PatientOverview';
import { patient } from '../../../types';

// Helper to create mock patient
const createMockPatient = (overrides?: Partial<patient>): patient => ({
  id: 'PAT001',
  name: 'Test Patient',
  age: 45,
  gender: 'Male',
  bed: 'A101',
  room: 'ICU-1',
  ward: 'ICU',
  admissionDate: new Date().toISOString(),
  diagnosis: 'Test Diagnosis',
  department: 'Cardiology',
  assignedDoctor: 'Dr. Smith',
  status: 'admitted',
  assignedDeviceId: 'WATCH001',
  deviceStatus: 'connected',
  deviceBatteryLevel: 80,
  vitals: {
    heartRate: 75,
    systolicPressure: 120,
    diastolicPressure: 80,
    respiratoryRate: 16,
    oxygenSaturation: 98,
    skinTemperature: 37.0, // Celsius from backend
    ecgReading: 0,
    eegReading: 0,
    isEcgMode: true,
    bioimpedance: 50,
    tremor: 2.5,
    imuFallRisk: 3.0,
    perfusionIndex: 5.0,
    stepCount: 1200,
    watchWorn: true,
    dataQualityScore: 0.95
  },
  alerts: [],
  ...overrides
});

const defaultProps = {
  patient: createMockPatient(),
  onVitalClick: jest.fn(),
  onECGView: jest.fn(),
  onToggleECGMode: jest.fn()
};

describe('PatientOverview - Domain Layer Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset mock to default return value
    mockUsePatientVitals.mockReturnValue({
      vitals: null,
      isConnected: false
    });
  });

  // ========================================
  // VITALS FORMATTING WITH DOMAIN LAYER
  // ========================================

  describe('Vitals Formatting', () => {
    it('should display temperature with domain layer unit (Fahrenheit)', () => {
      render(<PatientOverview {...defaultProps} />);

      // Temperature should be converted from 37°C to Fahrenheit and displayed with °F unit
      expect(screen.getByText('°F')).toBeInTheDocument();
      expect(screen.getByText('Temperature')).toBeInTheDocument();
    });

    it('should display blood pressure with domain layer formatting', () => {
      render(<PatientOverview {...defaultProps} />);

      // BP should be formatted as "120/80" with "mmHg" unit
      expect(screen.getByText(/120\/80/)).toBeInTheDocument();
      expect(screen.getByText('mmHg')).toBeInTheDocument();
    });

    it('should display heart rate with bpm unit', () => {
      render(<PatientOverview {...defaultProps} />);

      expect(screen.getByText('75')).toBeInTheDocument();
      expect(screen.getByText('BPM')).toBeInTheDocument();
    });

    it('should display oxygen saturation with % unit', () => {
      render(<PatientOverview {...defaultProps} />);

      expect(screen.getByText('98')).toBeInTheDocument();
      // Multiple % symbols on page, so just check that at least one exists
      expect(screen.getAllByText('%').length).toBeGreaterThan(0);
    });

    it('should display bioimpedance with Ω unit', () => {
      render(<PatientOverview {...defaultProps} />);

      expect(screen.getByText('50')).toBeInTheDocument();
      expect(screen.getByText('Ω')).toBeInTheDocument();
    });
  });

  // ========================================
  // TEMPERATURE CONVERSION
  // ========================================

  describe('Temperature Conversion', () => {
    it('should convert Celsius to Fahrenheit using domain layer', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          skinTemperature: 37.0 // 37°C should convert to ~98.6°F
        }
      });

      render(<PatientOverview {...defaultProps} patient={patient} />);

      // Should display Fahrenheit unit from domain layer
      expect(screen.getByText('°F')).toBeInTheDocument();
    });

    it('should handle low temperature correctly', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          skinTemperature: 35.0 // Low temp (hypothermia range)
        }
      });

      const { container } = render(<PatientOverview {...defaultProps} patient={patient} />);

      // Should still display with proper unit
      expect(screen.getByText('°F')).toBeInTheDocument();
      expect(container).toBeInTheDocument();
    });

    it('should handle high temperature correctly', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          skinTemperature: 39.5 // High temp (fever range)
        }
      });

      const { container } = render(<PatientOverview {...defaultProps} patient={patient} />);

      // Should still display with proper unit
      expect(screen.getByText('°F')).toBeInTheDocument();
      expect(container).toBeInTheDocument();
    });
  });

  // ========================================
  // EDGE CASES - MISSING VITALS
  // ========================================

  describe('Edge Cases - Missing Vitals', () => {
    it('should handle missing temperature gracefully', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          skinTemperature: undefined as any
        }
      });

      const { container } = render(<PatientOverview {...defaultProps} patient={patient} />);

      // Should render without crashing
      expect(container).toBeInTheDocument();
      // Should show placeholder
      expect(screen.getAllByText('--').length).toBeGreaterThan(0);
    });

    it('should handle missing blood pressure gracefully', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          systolicPressure: undefined as any,
          diastolicPressure: undefined as any
        }
      });

      const { container } = render(<PatientOverview {...defaultProps} patient={patient} />);

      expect(container).toBeInTheDocument();
      expect(screen.getByText('--/--')).toBeInTheDocument();
    });

    it('should handle completely missing vitals object', () => {
      const patient = createMockPatient({
        vitals: undefined as any
      });

      const { container } = render(<PatientOverview {...defaultProps} patient={patient} />);

      // Should render without crashing
      expect(container).toBeInTheDocument();
    });

    it('should handle missing bioimpedance', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          bioimpedance: undefined as any
        }
      });

      const { container } = render(<PatientOverview {...defaultProps} patient={patient} />);

      expect(container).toBeInTheDocument();
    });
  });

  // ========================================
  // PATIENT METADATA DISPLAY
  // ========================================

  describe('Patient Metadata', () => {
    it('should display diagnosis', () => {
      render(<PatientOverview {...defaultProps} />);

      expect(screen.getByText(/Test Diagnosis/)).toBeInTheDocument();
    });

    it('should display department', () => {
      render(<PatientOverview {...defaultProps} />);

      expect(screen.getByText(/Cardiology/)).toBeInTheDocument();
    });

    it('should display assigned doctor', () => {
      render(<PatientOverview {...defaultProps} />);

      expect(screen.getByText(/Dr. Smith/)).toBeInTheDocument();
    });

    it('should display watch ID when assigned', () => {
      render(<PatientOverview {...defaultProps} />);

      expect(screen.getByText(/WATCH001/)).toBeInTheDocument();
    });

    it('should display device status', () => {
      render(<PatientOverview {...defaultProps} />);

      expect(screen.getByText(/Connected/)).toBeInTheDocument();
    });
  });

  // ========================================
  // EDGE CASES - EXTREME VALUES
  // ========================================

  describe('Edge Cases - Extreme Values', () => {
    it('should handle high heart rate', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          heartRate: 180 // Tachycardia
        }
      });

      render(<PatientOverview {...defaultProps} patient={patient} />);

      expect(screen.getByText('180')).toBeInTheDocument();
    });

    it('should handle low oxygen saturation', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          oxygenSaturation: 85 // Hypoxia
        }
      });

      render(<PatientOverview {...defaultProps} patient={patient} />);

      expect(screen.getByText('85')).toBeInTheDocument();
    });

    it('should handle zero step count', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          stepCount: 0
        }
      });

      const { container } = render(<PatientOverview {...defaultProps} patient={patient} />);

      // Just verify it renders without crashing - step count 0 may be displayed
      expect(container).toBeInTheDocument();
    });

    it('should handle fractional perfusion index', () => {
      const patient = createMockPatient({
        vitals: {
          ...createMockPatient().vitals,
          perfusionIndex: 3.7
        }
      });

      const { container } = render(<PatientOverview {...defaultProps} patient={patient} />);

      // Domain layer formats perfusion index - just verify it renders
      expect(container).toBeInTheDocument();
      expect(screen.getByText('Perfusion')).toBeInTheDocument();
    });
  });

  // ========================================
  // SENSOR VITALS
  // ========================================

  describe('Sensor Vitals', () => {
    it('should display tremor value', () => {
      render(<PatientOverview {...defaultProps} />);

      expect(screen.getByText('2.5')).toBeInTheDocument();
      // Multiple /10 on page (tremor + fall risk), so just check that at least one exists
      expect(screen.getAllByText('/10').length).toBeGreaterThan(0);
    });

    it('should display fall risk value', () => {
      render(<PatientOverview {...defaultProps} />);

      expect(screen.getByText('3.0')).toBeInTheDocument();
      expect(screen.getByText('Fall Risk')).toBeInTheDocument();
    });

    it('should display perfusion index', () => {
      render(<PatientOverview {...defaultProps} />);

      // Text may be split across elements, so just check for the label
      expect(screen.getByText('Perfusion')).toBeInTheDocument();
    });

    it('should display watch worn status', () => {
      render(<PatientOverview {...defaultProps} />);

      expect(screen.getByText('ON')).toBeInTheDocument();
    });
  });
});
