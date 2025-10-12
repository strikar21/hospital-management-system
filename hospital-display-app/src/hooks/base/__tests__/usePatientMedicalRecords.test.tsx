/**
 * Unit Tests for usePatientMedicalRecords
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data
 *
 * Tests generic hook operations for all medical record types
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { usePatientMedicalRecords, MedicalRecordHookConfig } from '../usePatientMedicalRecords';
import { patient, user, medication, caseSheetEntry } from '../../../types';

// Mock useDataRefresh
jest.mock('../../useDataRefresh', () => ({
  useDataRefresh: jest.fn(() => ({
    refreshMedications: jest.fn().mockResolvedValue([]),
    refreshInvestigations: jest.fn().mockResolvedValue([]),
    refreshTherapies: jest.fn().mockResolvedValue([]),
    refreshCaseEntries: jest.fn().mockResolvedValue([])
  }))
}));

// Mock caseEntryTransformer
jest.mock('../../../utils/caseEntryTransformer', () => ({
  transformAndAddCaseEntry: jest.fn((result, addFn) => {
    if (result?.caseEntry) {
      addFn({
        id: result.caseEntry.id,
        timestamp: result.caseEntry.timestamp,
        type: result.caseEntry.entryType,
        description: result.caseEntry.description,
        performedBy: result.caseEntry.performedBy,
        canEdit: true
      });
    }
  })
}));

describe('usePatientMedicalRecords', () => {
  // Mock data
  const mockPatient: patient = {
    id: 'PAT001',
    name: 'John Doe',
    mrn: 'MRN001',
    age: 45,
    gender: 'male' as 'male',
    admissionDate: new Date().toISOString(),
    roomNumber: '101',
    bedNumber: 'A',
    condition: 'stable' as 'stable',
    deviceId: null
  };

  const mockUser: user = {
    id: 'USER001',
    staffId: 'DOC001',
    name: 'Dr. Smith',
    role: 'doctor' as 'doctor',
    department: 'Medicine'
  };

  const mockMedications: medication[] = [
    {
      id: 'MED001',
      name: 'Aspirin',
      dosage: '500mg',
      frequency: 'twice daily',
      route: 'PO',
      duration: '7 days',
      status: 'active',
      prescribedBy: 'DOC001',
      startDate: new Date().toISOString(),
      createdAt: new Date().toISOString(),
      canEdit: true
    }
  ];

  const mockSetRecords = jest.fn();
  const mockAddCaseSheetEntry = jest.fn();
  const mockSetCaseEntries = jest.fn();

  interface TestFormState {
    name: string;
    dosage: string;
    frequency: string;
  }

  const defaultConfig: MedicalRecordHookConfig<medication, TestFormState> = {
    recordType: 'medications',
    recordTypePlural: 'medications',
    service: {
      add: jest.fn().mockResolvedValue({
        success: true,
        medicalRecord: {
          id: 'MED002',
          name: 'Ibuprofen',
          dosage: '400mg',
          frequency: 'three times daily',
          route: 'PO',
          duration: '5 days',
          status: 'active',
          prescribedBy: 'DOC001',
          startDate: new Date().toISOString(),
          createdAt: new Date().toISOString(),
          canEdit: true
        },
        caseEntry: {
          id: 'CE001',
          timestamp: new Date().toISOString(),
          entryType: 'medication',
          description: 'Medication prescribed',
          performedBy: 'DOC001'
        }
      })
    },
    defaultFormState: {
      name: '',
      dosage: '',
      frequency: ''
    },
    validateForm: (form) => !!(form.name && form.dosage && form.frequency),
    buildRecordData: (form, user) => ({
      name: form.name,
      dosage: form.dosage,
      frequency: form.frequency,
      route: 'PO',
      duration: '7 days',
      status: 'active',
      prescribedBy: user.staffId,
      startDate: new Date().toISOString(),
      createdAt: new Date().toISOString(),
      canEdit: true
    } as medication),
    resetFormState: {
      name: '',
      dosage: '',
      frequency: ''
    }
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ================================
  // INITIALIZATION TESTS
  // ================================

  describe('Initialization', () => {
    it('should initialize with default state', () => {
      const { result } = renderHook(() =>
        usePatientMedicalRecords(
          {
            patient: mockPatient,
            currentUser: mockUser,
            records: mockMedications,
            setRecords: mockSetRecords,
            addCaseSheetEntry: mockAddCaseSheetEntry,
            setCaseEntries: mockSetCaseEntries
          },
          defaultConfig
        )
      );

      expect(result.current.isAdding).toBe(false);
      expect(result.current.formState).toEqual({ name: '', dosage: '', frequency: '' });
      expect(result.current.adding).toBe(false);
    });

    it('should initialize with custom default form state', () => {
      const customConfig = {
        ...defaultConfig,
        defaultFormState: {
          name: 'Default Med',
          dosage: '100mg',
          frequency: 'once daily'
        }
      };

      const { result } = renderHook(() =>
        usePatientMedicalRecords(
          {
            patient: mockPatient,
            currentUser: mockUser,
            records: mockMedications,
            setRecords: mockSetRecords,
            addCaseSheetEntry: mockAddCaseSheetEntry,
            setCaseEntries: mockSetCaseEntries
          },
          customConfig
        )
      );

      expect(result.current.formState).toEqual({
        name: 'Default Med',
        dosage: '100mg',
        frequency: 'once daily'
      });
    });
  });

  // ================================
  // STATE MANAGEMENT TESTS
  // ================================

  describe('State Management', () => {
    it('should update isAdding state', () => {
      const { result } = renderHook(() =>
        usePatientMedicalRecords(
          {
            patient: mockPatient,
            currentUser: mockUser,
            records: mockMedications,
            setRecords: mockSetRecords,
            addCaseSheetEntry: mockAddCaseSheetEntry,
            setCaseEntries: mockSetCaseEntries
          },
          defaultConfig
        )
      );

      act(() => {
        result.current.setIsAdding(true);
      });

      expect(result.current.isAdding).toBe(true);
    });

    it('should update formState', () => {
      const { result } = renderHook(() =>
        usePatientMedicalRecords(
          {
            patient: mockPatient,
            currentUser: mockUser,
            records: mockMedications,
            setRecords: mockSetRecords,
            addCaseSheetEntry: mockAddCaseSheetEntry,
            setCaseEntries: mockSetCaseEntries
          },
          defaultConfig
        )
      );

      act(() => {
        result.current.setFormState({
          name: 'Aspirin',
          dosage: '500mg',
          frequency: 'twice daily'
        });
      });

      expect(result.current.formState).toEqual({
        name: 'Aspirin',
        dosage: '500mg',
        frequency: 'twice daily'
      });
    });
  });

  // ================================
  // HANDLE ADD TESTS
  // ================================

  describe('handleAdd', () => {
    it('should add record successfully with optimistic update', async () => {
      const { result } = renderHook(() =>
        usePatientMedicalRecords(
          {
            patient: mockPatient,
            currentUser: mockUser,
            records: mockMedications,
            setRecords: mockSetRecords,
            addCaseSheetEntry: mockAddCaseSheetEntry,
            setCaseEntries: mockSetCaseEntries
          },
          defaultConfig
        )
      );

      // Set form data
      act(() => {
        result.current.setFormState({
          name: 'Ibuprofen',
          dosage: '400mg',
          frequency: 'three times daily'
        });
      });

      // Call handleAdd
      await act(async () => {
        await result.current.handleAdd();
      });

      // Verify service was called
      expect(defaultConfig.service.add).toHaveBeenCalledWith(
        'PAT001',
        expect.objectContaining({
          name: 'Ibuprofen',
          dosage: '400mg',
          frequency: 'three times daily'
        }),
        'USER001'
      );

      // Verify state was updated
      expect(mockSetRecords).toHaveBeenCalled();
      expect(mockAddCaseSheetEntry).toHaveBeenCalled();

      // Verify form was reset
      expect(result.current.formState).toEqual({ name: '', dosage: '', frequency: '' });
      expect(result.current.isAdding).toBe(false);
    });

    it('should not add record if form validation fails', async () => {
      const { result } = renderHook(() =>
        usePatientMedicalRecords(
          {
            patient: mockPatient,
            currentUser: mockUser,
            records: mockMedications,
            setRecords: mockSetRecords,
            addCaseSheetEntry: mockAddCaseSheetEntry,
            setCaseEntries: mockSetCaseEntries
          },
          defaultConfig
        )
      );

      // Set incomplete form data (missing frequency)
      act(() => {
        result.current.setFormState({
          name: 'Ibuprofen',
          dosage: '400mg',
          frequency: ''  // Missing required field
        });
      });

      // Call handleAdd
      await act(async () => {
        await result.current.handleAdd();
      });

      // Verify service was NOT called
      expect(defaultConfig.service.add).not.toHaveBeenCalled();
    });

    it('should handle add error with default error handler', async () => {
      const alertSpy = jest.spyOn(window, 'alert').mockImplementation();
      const failingConfig = {
        ...defaultConfig,
        service: {
          add: jest.fn().mockRejectedValue(new Error('Network error'))
        }
      };

      const { result } = renderHook(() =>
        usePatientMedicalRecords(
          {
            patient: mockPatient,
            currentUser: mockUser,
            records: mockMedications,
            setRecords: mockSetRecords,
            addCaseSheetEntry: mockAddCaseSheetEntry,
            setCaseEntries: mockSetCaseEntries
          },
          failingConfig
        )
      );

      // Set valid form data
      act(() => {
        result.current.setFormState({
          name: 'Ibuprofen',
          dosage: '400mg',
          frequency: 'three times daily'
        });
      });

      // Call handleAdd
      await act(async () => {
        await result.current.handleAdd();
      });

      // Verify error alert was shown
      expect(alertSpy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to add medication')
      );

      alertSpy.mockRestore();
    });

    it('should handle add error with custom error handler', async () => {
      const customErrorHandler = jest.fn();
      const configWithCustomError = {
        ...defaultConfig,
        service: {
          add: jest.fn().mockRejectedValue(new Error('Network error'))
        },
        handleAddError: customErrorHandler
      };

      const { result } = renderHook(() =>
        usePatientMedicalRecords(
          {
            patient: mockPatient,
            currentUser: mockUser,
            records: mockMedications,
            setRecords: mockSetRecords,
            addCaseSheetEntry: mockAddCaseSheetEntry,
            setCaseEntries: mockSetCaseEntries
          },
          configWithCustomError
        )
      );

      // Set valid form data
      act(() => {
        result.current.setFormState({
          name: 'Ibuprofen',
          dosage: '400mg',
          frequency: 'three times daily'
        });
      });

      // Call handleAdd
      await act(async () => {
        await result.current.handleAdd();
      });

      // Verify custom error handler was called
      expect(customErrorHandler).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({
          name: 'Ibuprofen',
          dosage: '400mg',
          frequency: 'three times daily'
        }),
        mockUser
      );
    });

    it('should prevent double submission', async () => {
      const { result } = renderHook(() =>
        usePatientMedicalRecords(
          {
            patient: mockPatient,
            currentUser: mockUser,
            records: mockMedications,
            setRecords: mockSetRecords,
            addCaseSheetEntry: mockAddCaseSheetEntry,
            setCaseEntries: mockSetCaseEntries
          },
          defaultConfig
        )
      );

      // Set valid form data
      act(() => {
        result.current.setFormState({
          name: 'Ibuprofen',
          dosage: '400mg',
          frequency: 'three times daily'
        });
      });

      // Call handleAdd twice quickly
      const promise1 = act(async () => {
        await result.current.handleAdd();
      });

      const promise2 = act(async () => {
        await result.current.handleAdd();
      });

      await Promise.all([promise1, promise2]);

      // Verify service was only called once
      expect(defaultConfig.service.add).toHaveBeenCalledTimes(1);
    });
  });

  // ================================
  // HANDLE CANCEL TESTS
  // ================================

  describe('handleCancel', () => {
    it('should reset form and hide modal', () => {
      const { result } = renderHook(() =>
        usePatientMedicalRecords(
          {
            patient: mockPatient,
            currentUser: mockUser,
            records: mockMedications,
            setRecords: mockSetRecords,
            addCaseSheetEntry: mockAddCaseSheetEntry,
            setCaseEntries: mockSetCaseEntries
          },
          defaultConfig
        )
      );

      // Set form data and show modal
      act(() => {
        result.current.setIsAdding(true);
        result.current.setFormState({
          name: 'Ibuprofen',
          dosage: '400mg',
          frequency: 'three times daily'
        });
      });

      // Cancel
      act(() => {
        result.current.handleCancel();
      });

      // Verify state was reset
      expect(result.current.isAdding).toBe(false);
      expect(result.current.formState).toEqual({ name: '', dosage: '', frequency: '' });
    });
  });

  // ================================
  // PERFORM ATOMIC OPERATION TESTS
  // ================================

  describe('performAtomicOperation', () => {
    it('should perform atomic operation with optimistic update', async () => {
      const { result } = renderHook(() =>
        usePatientMedicalRecords(
          {
            patient: mockPatient,
            currentUser: mockUser,
            records: mockMedications,
            setRecords: mockSetRecords,
            addCaseSheetEntry: mockAddCaseSheetEntry,
            setCaseEntries: mockSetCaseEntries
          },
          defaultConfig
        )
      );

      const mockOperation = jest.fn().mockResolvedValue({
        success: true,
        medicalRecord: { id: 'MED001', status: 'discontinued' },
        caseEntry: {
          id: 'CE002',
          timestamp: new Date().toISOString(),
          entryType: 'medication',
          description: 'Medication discontinued',
          performedBy: 'DOC001'
        }
      });

      const mockUpdateFn = jest.fn((prev, result) =>
        prev.map(med => med.id === 'MED001' ? result.medicalRecord : med)
      );

      await act(async () => {
        await result.current.performAtomicOperation(
          mockOperation,
          mockUpdateFn,
          'Test operation failed'
        );
      });

      // Verify operation was called
      expect(mockOperation).toHaveBeenCalled();

      // Verify update function was called
      expect(mockSetRecords).toHaveBeenCalled();

      // Verify case entry was added
      expect(mockAddCaseSheetEntry).toHaveBeenCalled();
    });

    it('should handle atomic operation error', async () => {
      const alertSpy = jest.spyOn(window, 'alert').mockImplementation();

      const { result } = renderHook(() =>
        usePatientMedicalRecords(
          {
            patient: mockPatient,
            currentUser: mockUser,
            records: mockMedications,
            setRecords: mockSetRecords,
            addCaseSheetEntry: mockAddCaseSheetEntry,
            setCaseEntries: mockSetCaseEntries
          },
          defaultConfig
        )
      );

      const mockOperation = jest.fn().mockRejectedValue(new Error('Operation failed'));
      const mockUpdateFn = jest.fn();

      await expect(
        act(async () => {
          await result.current.performAtomicOperation(
            mockOperation,
            mockUpdateFn,
            'Custom error message'
          );
        })
      ).rejects.toThrow();

      // Verify error alert was shown with custom message
      expect(alertSpy).toHaveBeenCalledWith(
        expect.stringContaining('Custom error message')
      );

      alertSpy.mockRestore();
    });
  });
});
