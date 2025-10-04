import { useState, useEffect, useCallback } from 'react';
import { patient } from '../types';
import { PatientService } from '../services';
import { getApiUrl } from '../config/apiConfig';

interface UsePatientDataOptions {
  userId: string;
  selectedWard: string;
  showAllDepartments: boolean;
  refreshInterval?: number; // Auto-refresh interval in milliseconds
}

export const usePatientData = ({
  userId,
  selectedWard,
  showAllDepartments,
  refreshInterval = 30000 // Default: 30 seconds
}: UsePatientDataOptions) => {
  const [patients, setPatients] = useState<patient[]>([]);
  const [loading, setLoading] = useState(false);
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
    loadPatients();
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
    // Refetch fresh data from backend (single source of truth)
    try {
      const response = await fetch(getApiUrl('/patients'));
      if (response.ok) {
        const data = await response.json();
        setPatients(data.patients || data);
      }
    } catch (refreshError) {
      // Failed to refresh patients after update - handle silently
    }
  }, []);

  const removePatient = useCallback(async (patientId: string) => {
    // Refetch fresh data from backend (single source of truth)
    try {
      const response = await fetch(getApiUrl('/patients'));
      if (response.ok) {
        const data = await response.json();
        setPatients(data.patients || data);
      }
    } catch (refreshError) {
      // Failed to refresh patients after removal - handle silently
    }
  }, []);

  const addPatient = useCallback(async (newPatient: patient) => {
    // Refetch fresh data from backend (single source of truth)
    try {
      const response = await fetch(getApiUrl('/patients'));
      if (response.ok) {
        const data = await response.json();
        setPatients(data.patients || data);
      }
    } catch (refreshError) {
      // Failed to refresh patients after addition - handle silently
    }
  }, []);

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