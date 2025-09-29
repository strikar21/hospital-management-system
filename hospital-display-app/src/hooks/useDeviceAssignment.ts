/**
 * useDeviceAssignment - Device assignment management hook
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade device assignment management with real-time tracking
 */

import { useState, useEffect, useCallback } from 'react';
import { user as UserType, patient } from '../types';
import { DeviceService, PatientService } from '../services';

// Type definitions
export interface Device {
  id: string;
  deviceId: string;
  serialNumber: string;
  macAddress: string;
  firmwareVersion: string;
  deviceType: string;
  location: string;
  status: string;
  connectionStatus?: string;
  displayName?: string;
  batteryLevel: number | null;
  lastSeen: string | null;
  assignedPatientId: string | null;
  calibrationDate: string | null;
  nextMaintenanceDate: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface DeviceAssignmentRecord {
  id: number;
  deviceId: string;
  patientId: string;
  performedBy: string;
  assignmentReason: string;
  assignedAt: string;
  status: string;
  deviceName: string;
  deviceType: string;
  patientName?: string;
  location?: string;
  watchDisplay?: string;
  serialNumber?: string;
  connectionStatus?: string;
  batteryLevel?: number | null;
}

export interface PoolStatus {
  summary: {
    totalDevices: number;
    availableDevices: number;
    assignedDevices: number;
    offlineDevices: number;
    lowBatteryDevices: number;
  };
}

export type TabType = 'assign' | 'assigned' | 'pool';

export interface UseDeviceAssignmentOptions {
  autoRefresh?: boolean;
  refreshInterval?: number;
  messageTimeout?: number;
}

export interface UseDeviceAssignmentReturn {
  // Tab state
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;

  // Data state
  freeDevices: Device[];
  patients: patient[];
  assignedDevices: DeviceAssignmentRecord[];
  poolStatus: PoolStatus | null;
  availableWatches: Device[];
  assignedWatches: DeviceAssignmentRecord[];

  // UI state
  loading: boolean;
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  selectedPatient: string;
  setSelectedPatient: (patientId: string) => void;
  selectedDevice: string;
  setSelectedDevice: (deviceId: string) => void;
  assignmentReason: string;
  setAssignmentReason: (reason: string) => void;

  // Filter state
  deviceFilter: string;
  setDeviceFilter: (filter: string) => void;
  locationFilter: string;
  setLocationFilter: (filter: string) => void;
  patientFilter: string;
  setPatientFilter: (filter: string) => void;
  wardFilter: string;
  setWardFilter: (filter: string) => void;

  // Message state
  showSuccess: string | null;
  error: string | null;
  showMessage: (message: string, isError?: boolean) => void;
  clearMessages: () => void;

  // Actions
  refreshData: () => Promise<void>;
  assignDevice: (deviceId: string, patientId: string, reason: string) => Promise<boolean>;
  unassignDevice: (deviceId: string, reason: string) => Promise<boolean>;
  calibrateDevice: (deviceId: string) => Promise<boolean>;

  // Computed values
  filteredDevices: Device[];
  filteredPatients: patient[];
  filteredAssignedDevices: DeviceAssignmentRecord[];
  deviceStats: {
    total: number;
    available: number;
    assigned: number;
    offline: number;
    lowBattery: number;
  };
}

export const useDeviceAssignment = (
  currentUser: UserType,
  options: UseDeviceAssignmentOptions = {}
): UseDeviceAssignmentReturn => {

  const {
    autoRefresh = false,
    refreshInterval = 30000,
    messageTimeout = 3000
  } = options;

  // Tab state
  const [activeTab, setActiveTab] = useState<TabType>('assign');

  // Data state
  const [freeDevices, setFreeDevices] = useState<Device[]>([]);
  const [patients, setPatients] = useState<patient[]>([]);
  const [assignedDevices, setAssignedDevices] = useState<DeviceAssignmentRecord[]>([]);
  const [poolStatus, setPoolStatus] = useState<PoolStatus | null>(null);
  const [availableWatches, setAvailableWatches] = useState<Device[]>([]);
  const [assignedWatches, setAssignedWatches] = useState<DeviceAssignmentRecord[]>([]);

  // UI state
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<string>('');
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [assignmentReason, setAssignmentReason] = useState('patientAdmission');

  // Filter state
  const [deviceFilter, setDeviceFilter] = useState('all');
  const [locationFilter, setLocationFilter] = useState('all');
  const [patientFilter, setPatientFilter] = useState('all');
  const [wardFilter, setWardFilter] = useState('all');

  // Message state
  const [showSuccess, setShowSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Message handling
  const showMessage = useCallback((message: string, isError = false) => {
    if (isError) {
      setError(message);
      setTimeout(() => setError(null), 5000);
    } else {
      setShowSuccess(message);
      setTimeout(() => setShowSuccess(null), messageTimeout);
    }
  }, [messageTimeout]);

  const clearMessages = useCallback(() => {
    setShowSuccess(null);
    setError(null);
  }, []);

  // Data loading functions
  const loadFreeDevices = useCallback(async () => {
    try {
      const devices = await DeviceService.getFreeDevices(currentUser.staffId, deviceFilter, locationFilter);
      setFreeDevices(devices || []);
      setAvailableWatches(devices || []);
    } catch (error) {
      console.error('Error loading free devices:', error);
      setFreeDevices([]);
      setAvailableWatches([]);
    }
  }, [currentUser.staffId, deviceFilter, locationFilter]);

  const loadPatients = useCallback(async () => {
    try {
      const patients = await PatientService.getPatients();
      setPatients(patients || []);
    } catch (error) {
      console.error('Error loading patients:', error);
      setPatients([]);
    }
  }, []);

  const loadAssignedDevices = useCallback(async () => {
    try {
      const assigned = await DeviceService.getAssignmentHistory(currentUser.staffId);
      setAssignedDevices(assigned || []);
      setAssignedWatches(assigned || []);
    } catch (error) {
      console.error('Error loading assigned devices:', error);
      setAssignedDevices([]);
      setAssignedWatches([]);
    }
  }, [currentUser.staffId]);

  const loadPoolStatus = useCallback(async () => {
    try {
      const status = await DeviceService.getDevicePoolStatus(currentUser.staffId);
      setPoolStatus(status);
    } catch (error) {
      console.error('Error loading pool status:', error);
      setPoolStatus(null);
    }
  }, [currentUser.staffId]);

  // Refresh all data
  const refreshData = useCallback(async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadFreeDevices(),
        loadPatients(),
        loadAssignedDevices(),
        loadPoolStatus()
      ]);
    } catch (error) {
      console.error('Error refreshing data:', error);
      showMessage('Failed to refresh device data', true);
    } finally {
      setLoading(false);
    }
  }, [loadFreeDevices, loadPatients, loadAssignedDevices, loadPoolStatus, showMessage]);

  // Device assignment actions
  const assignDevice = useCallback(async (deviceId: string, patientId: string, reason: string): Promise<boolean> => {
    try {
      setLoading(true);
      await DeviceService.assignDevice(deviceId, patientId, currentUser.staffId, reason);
      showMessage('Device assigned successfully');
      await refreshData();

      // Clear selections
      setSelectedDevice('');
      setSelectedPatient('');
      setAssignmentReason('patientAdmission');

      return true;
    } catch (error) {
      console.error('Error assigning device:', error);
      showMessage('Failed to assign device', true);
      return false;
    } finally {
      setLoading(false);
    }
  }, [currentUser.staffId, showMessage, refreshData]);

  const unassignDevice = useCallback(async (deviceId: string, reason: string): Promise<boolean> => {
    try {
      setLoading(true);
      await DeviceService.unassignDevice(deviceId, currentUser.staffId, reason);
      showMessage('Device unassigned successfully');
      await refreshData();
      return true;
    } catch (error) {
      console.error('Error unassigning device:', error);
      showMessage('Failed to unassign device', true);
      return false;
    } finally {
      setLoading(false);
    }
  }, [currentUser.staffId, showMessage, refreshData]);

  const calibrateDevice = useCallback(async (deviceId: string): Promise<boolean> => {
    try {
      setLoading(true);
      await DeviceService.calibrateDevice(deviceId, currentUser.staffId);
      showMessage('Device calibration initiated');
      await refreshData();
      return true;
    } catch (error) {
      console.error('Error calibrating device:', error);
      showMessage('Failed to calibrate device', true);
      return false;
    } finally {
      setLoading(false);
    }
  }, [currentUser.staffId, showMessage, refreshData]);

  // Computed values
  const filteredDevices = freeDevices.filter(device => {
    const matchesSearch = !searchTerm ||
      device.deviceId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      device.serialNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      device.location.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesType = deviceFilter === 'all' || device.deviceType === deviceFilter;
    const matchesLocation = locationFilter === 'all' || device.location === locationFilter;

    return matchesSearch && matchesType && matchesLocation;
  });

  const filteredPatients = patients.filter(patient => {
    const matchesSearch = !searchTerm ||
      patient.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      patient.mrn?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      patient.roomNumber.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = patientFilter === 'all' || patient.status === patientFilter;
    const matchesWard = wardFilter === 'all' || patient.ward === wardFilter;

    return matchesSearch && matchesStatus && matchesWard;
  });

  const filteredAssignedDevices = assignedDevices.filter(device => {
    const matchesSearch = !searchTerm ||
      device.deviceId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      device.patientName?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      device.location?.toLowerCase().includes(searchTerm.toLowerCase());

    return matchesSearch;
  });

  const deviceStats = {
    total: poolStatus?.summary.totalDevices || 0,
    available: poolStatus?.summary.availableDevices || 0,
    assigned: poolStatus?.summary.assignedDevices || 0,
    offline: poolStatus?.summary.offlineDevices || 0,
    lowBattery: poolStatus?.summary.lowBatteryDevices || 0
  };

  // Initial data load
  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // Auto-refresh if enabled
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      if (!loading) {
        refreshData();
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, loading, refreshData]);

  // Refresh when filters change
  useEffect(() => {
    loadFreeDevices();
  }, [loadFreeDevices]);

  return {
    // Tab state
    activeTab,
    setActiveTab,

    // Data state
    freeDevices,
    patients,
    assignedDevices,
    poolStatus,
    availableWatches,
    assignedWatches,

    // UI state
    loading,
    searchTerm,
    setSearchTerm,
    selectedPatient,
    setSelectedPatient,
    selectedDevice,
    setSelectedDevice,
    assignmentReason,
    setAssignmentReason,

    // Filter state
    deviceFilter,
    setDeviceFilter,
    locationFilter,
    setLocationFilter,
    patientFilter,
    setPatientFilter,
    wardFilter,
    setWardFilter,

    // Message state
    showSuccess,
    error,
    showMessage,
    clearMessages,

    // Actions
    refreshData,
    assignDevice,
    unassignDevice,
    calibrateDevice,

    // Computed values
    filteredDevices,
    filteredPatients,
    filteredAssignedDevices,
    deviceStats
  };
};