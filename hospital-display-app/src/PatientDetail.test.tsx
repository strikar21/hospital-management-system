import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import PatientDetail from './PatientDetail';
import { patient, user } from './types';

// Mock the services
jest.mock('./services', () => ({
  PatientService: {
    getPatient: jest.fn(),
    updatePatient: jest.fn(),
  },
  MedicationService: {
    getMedications: jest.fn(),
    addMedication: jest.fn(),
  },
  InvestigationService: {
    getInvestigations: jest.fn(),
    addInvestigation: jest.fn(),
  },
  TherapyService: {
    getTherapies: jest.fn(),
    addTherapy: jest.fn(),
  },
}));

// Mock CaseSheetBook component
jest.mock('./CaseSheetBook', () => {
  return function MockCaseSheetBook() {
    return <div data-testid="case-sheet-book">Case Sheet Book</div>;
  };
});

const mockPatient: patient = {
  id: 'test-patient-1',
  firstName: 'John',
  lastName: 'Doe',
  age: 45,
  gender: 'Male',
  room: '101',
  bed: 'A',
  admissionDate: '2023-10-01',
  diagnosis: 'Test diagnosis',
  vitals: {
    heartRate: 75,
    systolicPressure: 120,
    diastolicPressure: 80,
    respiratoryRate: 16,
    oxygenSaturation: 98,
    skinTemperature: 98.6,
    ecgReading: 72,
    eegReading: 15,
    timestamp: new Date().toISOString(),
    lastUpdated: new Date().toISOString(),
    isEcgMode: true,
    dataQualityScore: 95
  },
  medications: [],
  investigations: [],
  therapies: [],
  notes: [],
  alerts: [],
  caseSheet: [],
  status: 'active',
  mrn: 'MRN123456',
};

const mockUser: user = {
  id: 'test-user-1',
  name: 'Dr. Test',
  role: 'Doctor'
};

const defaultProps = {
  patient: mockPatient,
  currentUser: mockUser,
  onClose: jest.fn(),
  onVitalClick: jest.fn(),
  onECGView: jest.fn(),
  onToggleECGMode: jest.fn(),
  onPatientDischarge: jest.fn(),
};

describe('PatientDetail', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders without crashing', async () => {
    await act(async () => {
      render(<PatientDetail {...defaultProps} />);
    });

    // Test basic elements that should always be present
    expect(screen.getByText('Male')).toBeInTheDocument();
    expect(screen.getByText('101')).toBeInTheDocument(); // Room number
    expect(screen.getByText('45')).toBeInTheDocument(); // Age
  });

  test('renders tab navigation', async () => {
    await act(async () => {
      render(<PatientDetail {...defaultProps} />);
    });

    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Medications')).toBeInTheDocument();
    expect(screen.getByText('Investigations')).toBeInTheDocument();
    expect(screen.getByText('Therapy')).toBeInTheDocument();
    expect(screen.getByText('Notes')).toBeInTheDocument();
    expect(screen.getByText('Case Sheet')).toBeInTheDocument();
  });

  test('shows close button', async () => {
    await act(async () => {
      render(<PatientDetail {...defaultProps} />);
    });

    const closeButton = screen.getByTitle('Close');
    expect(closeButton).toBeInTheDocument();
  });

  test('displays patient status', async () => {
    await act(async () => {
      render(<PatientDetail {...defaultProps} />);
    });

    expect(screen.getByText('ACTIVE')).toBeInTheDocument();
  });

  test('handles minimal vitals gracefully', async () => {
    const patientWithMinimalVitals = {
      ...mockPatient,
      vitals: {
        heartRate: 0,
        systolicPressure: 0,
        diastolicPressure: 0,
        respiratoryRate: 0,
        oxygenSaturation: 0,
        skinTemperature: 0,
        ecgReading: 0,
        eegReading: 0,
        timestamp: new Date().toISOString(),
        lastUpdated: new Date().toISOString(),
        isEcgMode: true,
        dataQualityScore: 0
      }
    };

    await act(async () => {
      expect(() => {
        render(<PatientDetail {...defaultProps} patient={patientWithMinimalVitals} />);
      }).not.toThrow();
    });
  });
});