/**
 * useDashboard - Custom hook for Dashboard state management and effects
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Centralized dashboard state, effects, and business logic for medical system
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { user, patient, roomproximity, appsettings } from '../types';
import { PatientService, VitalService } from '../services';
import { PermissionUtils } from '../utils/permissionUtils';
import { useAutoLogout } from './useAutoLogout';
import { usePatientData } from './usePatientData';
import auditService from '../services/auditService';

interface UseDashboardProps {
  currentUser: user;
  onLogout: () => void;
  settings: appsettings;
  onBedsideMode: (patients: patient[], displayCount?: 1 | 2) => void;
}

export const useDashboard = ({
  currentUser,
  onLogout,
  settings,
  onBedsideMode
}: UseDashboardProps) => {
  // Main state management
  const [selectedWard, setSelectedWard] = useState<string>('My Patients');
  const [roomProximity, setRoomProximity] = useState<roomproximity | null>(null);
  const [proximityScanning, setProximityScanning] = useState(false);
  const [showAllDepartments, setShowAllDepartments] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  // Modal states
  const [selectedPatient, setSelectedPatient] = useState<patient | null>(null);
  const [showVitalChart, setShowVitalChart] = useState<{patient: patient, vital: string} | null>(null);
  const [showECGViewer, setShowECGViewer] = useState<patient | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showDeviceAssignment, setShowDeviceAssignment] = useState(false);
  const [showPatientAdmission, setShowPatientAdmission] = useState(false);
  const [showDeviceProvisioning, setShowDeviceProvisioning] = useState(false);
  const [showNurseAdmission, setShowNurseAdmission] = useState(false);
  const [showStaffManagement, setShowStaffManagement] = useState(false);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const PATIENTS_PER_PAGE = 20;
  const alertTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map());
  const isMountedRef = useRef(true);

  // Auto-logout hook
  useAutoLogout({
    settings,
    onLogout,
    userId: currentUser.id
  });

  // Patient data hook
  const {
    patients,
    loading,
    lastSync,
    loadPatients,
    updatePatient,
    removePatient,
    totalPatients
  } = usePatientData({
    userId: currentUser.id,
    selectedWard,
    showAllDepartments,
    refreshInterval: 30000
  });

  // Initialize audit service
  useEffect(() => {
    auditService.setUserId(currentUser.id);
    auditService.logNavigation('login', 'dashboard', {
      userRole: currentUser.role,
      dashboardMode: 'main'
    });
  }, [currentUser.id, currentUser.role]);

  // Clean up alert timeouts on unmount
  useEffect(() => {
    return () => {
      // Mark as unmounted to prevent zombie updates
      isMountedRef.current = false;
      // Clear all pending timeouts
      const timeouts = alertTimeoutsRef.current;
      timeouts.forEach((timeout) => clearTimeout(timeout));
      timeouts.clear();
    };
  }, []);

  // Network status monitoring
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Load patients based on user role and room proximity
  useEffect(() => {
    if (currentUser) {
      setCurrentPage(1);
      loadPatients();
    }
  }, [currentUser, selectedWard, showAllDepartments, loadPatients]);

  // Proximity detection
  const detectProximity = useCallback(async () => {
    if (!currentUser || !PermissionUtils.isNurseOrTechnician(currentUser.role)) return;

    setProximityScanning(true);
    try {
      const proximity = await VitalService.detectRoomProximity();
      setRoomProximity(proximity);
    } catch (error) {
      // Failed to detect room proximity - handle silently
    } finally {
      setProximityScanning(false);
    }
  }, [currentUser]);

  // Auto-proximity detection for nurses and technicians
  useEffect(() => {
    if (currentUser && PermissionUtils.isNurseOrTechnician(currentUser.role)) {
      detectProximity();

      const proximityInterval = setInterval(() => {
        detectProximity();
      }, 10000);

      return () => clearInterval(proximityInterval);
    }
  }, [currentUser, detectProximity]);

  // Event handlers
  const handleToggleECGMode = async (patient: patient) => {
    if (!patient.vitals) return;
    try {
      // Send ECG mode toggle to backend first
      await PatientService.toggleECGMode(patient.id, !patient.vitals.isEcgMode);
      // Refetch fresh patient data from backend (single source of truth)
      loadPatients();
    } catch (error) {
      // Failed to toggle ECG mode - handle silently
    }
  };

  const handleVitalClick = async (patient: patient, vitalType: string) => {
    if (vitalType === 'ecgReading' || vitalType === 'eegReading') {
      setShowECGViewer(patient);
    } else {
      setShowVitalChart({ patient, vital: vitalType });
    }
  };

  const handlePatientDischarge = (patientId: string) => {
    removePatient(patientId);
    auditService.logPatientInteraction('discharged', patientId, 'Patient successfully discharged from hospital', {
      dischargedBy: currentUser.id,
      timestamp: new Date().toISOString()
    });
  };

  const handleAcknowledgeAlert = async (patient: patient, alertId: string) => {
    try {
      await PatientService.acknowledgeAlert(patient.id, alertId, currentUser.id);

      // Refetch fresh patient data from backend (single source of truth)
      loadPatients();

      const existingTimeout = alertTimeoutsRef.current.get(alertId);
      if (existingTimeout) {
        clearTimeout(existingTimeout);
      }

      const timeout = setTimeout(() => {
        // Only execute if component is still mounted (prevent zombie updates)
        if (isMountedRef.current) {
          // Refetch fresh data from backend after alert auto-hide period
          loadPatients();
        }
        alertTimeoutsRef.current.delete(alertId);
      }, 2000);

      alertTimeoutsRef.current.set(alertId, timeout);
    } catch (error) {
      // Failed to acknowledge alert - handle silently
      alert('Failed to acknowledge alert. Please try again.');
    }
  };

  const handleSingleBedsideMode = (patient: patient) => {
    onBedsideMode([patient], 1);
  };

  const handleDualBedsideMode = () => {
    if (patients.length >= 2) {
      onBedsideMode(patients.slice(0, 2), 2);
    } else if (patients.length === 1) {
      onBedsideMode(patients, 1);
    }
  };

  const toggleReferralMode = () => {
    setShowAllDepartments(!showAllDepartments);
  };

  const handlePatientSelection = async (patient: patient) => {
    try {
      // Fetching complete details for patient - processing silently

      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error('Request timeout')), 10000);
      });

      const fullPatientData = await Promise.race([
        PatientService.getPatient(patient.id),
        timeoutPromise
      ]);

      if (fullPatientData) {
        // Removed console.log for production
        setSelectedPatient(fullPatientData);
      } else {
        // Failed to fetch complete patient data - handle silently
        setSelectedPatient(patient);
      }
    } catch (error) {
      // Error fetching complete patient data - handle silently
      setSelectedPatient(patient);
    }
  };

  const getWardOptions = () => {
    if (PermissionUtils.isNurseOrTechnician(currentUser.role)) {
      return [];
    } else if (currentUser.role === 'Doctor') {
      const options = ['My Patients'];
      if (showAllDepartments) {
        options.push('All', 'ICU', 'General', 'Emergency', 'Cardiology');
      }
      return options;
    } else {
      return ['All', 'ICU', 'General', 'Emergency', 'Cardiology'];
    }
  };

  // Modal control functions
  const closeAllModals = () => {
    setSelectedPatient(null);
    setShowVitalChart(null);
    setShowECGViewer(null);
    setShowSettings(false);
    setShowDeviceAssignment(false);
    setShowPatientAdmission(false);
    setShowDeviceProvisioning(false);
    setShowNurseAdmission(false);
    setShowStaffManagement(false);
  };

  // Pagination calculations
  const totalPages = Math.ceil(totalPatients / PATIENTS_PER_PAGE);

  return {
    // State
    selectedWard,
    roomProximity,
    proximityScanning,
    showAllDepartments,
    isOnline,
    selectedPatient,
    showVitalChart,
    showECGViewer,
    showSettings,
    showDeviceAssignment,
    showPatientAdmission,
    showDeviceProvisioning,
    showNurseAdmission,
    showStaffManagement,
    currentPage,
    PATIENTS_PER_PAGE,
    totalPages,

    // Patient data
    patients,
    loading,
    lastSync,
    totalPatients,

    // State setters
    setSelectedWard,
    setCurrentPage,
    setShowSettings,
    setShowDeviceAssignment,
    setShowPatientAdmission,
    setShowDeviceProvisioning,
    setShowNurseAdmission,
    setShowStaffManagement,
    setSelectedPatient,
    setShowVitalChart,
    setShowECGViewer,

    // Handlers
    handleToggleECGMode,
    handleVitalClick,
    handlePatientDischarge,
    handleAcknowledgeAlert,
    handleSingleBedsideMode,
    handleDualBedsideMode,
    toggleReferralMode,
    handlePatientSelection,
    getWardOptions,
    detectProximity,
    loadPatients,
    closeAllModals
  };
};