import { useState, useEffect, useCallback } from 'react';
import { patient } from '../types';
import { PatientService } from '../services';

interface UsePatientDataOptions {
  userId: string;
  selectedWard: string;
  showAllDepartments: boolean;
  refreshInterval?: number; // Auto-refresh interval in milliseconds
  initialPatients?: patient[]; // Preloaded patients from cache/API
}

export const usePatientData = ({
  userId,
  selectedWard,
  showAllDepartments,
  refreshInterval = 30000, // Default: 30 seconds
  initialPatients = []
}: UsePatientDataOptions) => {
  const [patients, setPatients] = useState<patient[]>(initialPatients);
  const [loading, setLoading] = useState(initialPatients.length === 0);
  const [lastSync, setLastSync] = useState(new Date());
  const [error, setError] = useState<string | null>(null);

  const loadPatients = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      let patientData: patient[];

      if (selectedWard === 'My Patients') {
        // Get all patients for now - would need user-specific filtering in backend
        patientData = await PatientService.getPatients(undefined, undefined, true);
      } else if (showAllDepartments || selectedWard === 'All Departments') {
        patientData = await PatientService.getPatients(undefined, undefined, true);
      } else {
        // Load patients for specific ward/department
        patientData = await PatientService.getPatients(selectedWard, selectedWard, false);
      }

      setPatients(patientData);
      setLastSync(new Date());

      // Loaded patients for ward - tracking completed silently
    } catch (error) {
      // Failed to load patients - handle silently
      setError(error instanceof Error ? error.message : 'Failed to load patients');
    } finally {
      setLoading(false);
    }
  }, [selectedWard, showAllDepartments]);

  // Initial load and reload when dependencies change
  useEffect(() => {
    // Only load if no initial patients provided
    if (initialPatients.length === 0) {
      console.log('📡 No preloaded patients - fetching from API');
      loadPatients();
    } else {
      console.log('📦 Using preloaded patients:', initialPatients.length);
      setLastSync(new Date());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadPatients]);

  // Auto-refresh patients
  useEffect(() => {
    if (!refreshInterval) return;

    const interval = setInterval(() => {
      // Only auto-refresh if not currently loading to prevent conflicts
      if (!loading) {
        loadPatients();
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [loadPatients, loading, refreshInterval]);

  // Patient-specific operations
  const updatePatient = useCallback(async (patientId: string, updates: Partial<patient>) => {
    // Refetch fresh data from backend using authenticated service (single source of truth)
    try {
      const patientData = await PatientService.getPatients(selectedWard, selectedWard, showAllDepartments);
      setPatients(patientData);
    } catch (refreshError) {
      // Failed to refresh patients after update - handle silently
    }
  }, [selectedWard, showAllDepartments]);

  const removePatient = useCallback(async (patientId: string) => {
    // Refetch fresh data from backend using authenticated service (single source of truth)
    try {
      const patientData = await PatientService.getPatients(selectedWard, selectedWard, showAllDepartments);
      setPatients(patientData);
    } catch (refreshError) {
      // Failed to refresh patients after removal - handle silently
    }
  }, [selectedWard, showAllDepartments]);

  const addPatient = useCallback(async (newPatient: patient) => {
    // Refetch fresh data from backend using authenticated service (single source of truth)
    try {
      const patientData = await PatientService.getPatients(selectedWard, selectedWard, showAllDepartments);
      setPatients(patientData);
    } catch (refreshError) {
      // Failed to refresh patients after addition - handle silently
    }
  }, [selectedWard, showAllDepartments]);

  const getPatientById = useCallback((patientId: string) => {
    return patients.find(p => p.id === patientId);
  }, [patients]);

  return {
    patients,
    loading,
    lastSync,
    error,
    loadPatients,
    updatePatient,
    removePatient,
    addPatient,
    getPatientById,
    totalPatients: patients.length
  };
};