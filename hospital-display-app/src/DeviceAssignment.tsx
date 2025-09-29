import React, { useState, useEffect } from 'react';
import { user as UserType, patient } from './types';
import { DeviceService, PatientService } from './services';
import {
  DeviceAssignmentHeader,
  MessageDisplay,
  TabNavigation,
  DeviceSelectionPanel,
  PatientSelectionPanel,
  AssignedDevicesTab,
  DevicePoolTab
} from './components/DeviceAssignment';

// Type definitions
interface Device {
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

interface DeviceAssignmentRecord {
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

interface PoolStatus {
  summary: {
    totalDevices: number;
    availableDevices: number;
    assignedDevices: number;
    offlineDevices: number;
    lowBatteryDevices: number;
  };
}

interface DeviceAssignmentProps {
  currentUser: UserType;
  onBack: () => void;
}

type TabType = 'assign' | 'assigned' | 'pool';

export const DeviceAssignment: React.FC<DeviceAssignmentProps> = ({
  currentUser,
  onBack
}) => {
  // State management
  const [activeTab, setActiveTab] = useState<TabType>('assign');
  const [freeDevices, setFreeDevices] = useState<Device[]>([]);
  const [patients, setPatients] = useState<patient[]>([]);
  const [assignedDevices, setAssignedDevices] = useState<DeviceAssignmentRecord[]>([]);
  const [poolStatus, setPoolStatus] = useState<PoolStatus | null>(null);
  const [availableWatches, setAvailableWatches] = useState<Device[]>([]);
  const [assignedWatches, setAssignedWatches] = useState<DeviceAssignmentRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<string>('');
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [assignmentReason, setAssignmentReason] = useState('patientAdmission');
  const [deviceFilter, setDeviceFilter] = useState('all');
  const [locationFilter, setLocationFilter] = useState('all');
  const [patientFilter, setPatientFilter] = useState('all');
  const [wardFilter, setWardFilter] = useState('all');
  const [showSuccess, setShowSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load initial data
  useEffect(() => {
    refreshData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Message handling
  const showMessage = (message: string, isError = false) => {
    if (isError) {
      setError(message);
      setTimeout(() => setError(null), 5000);
    } else {
      setShowSuccess(message);
      setTimeout(() => setShowSuccess(null), 3000);
    }
  };

  // Data loading functions
  const loadFreeDevices = async () => {
    try {
      const devices = await DeviceService.getFreeDevices(currentUser.staffId, deviceFilter, locationFilter);
      setFreeDevices(devices || []);
      setAvailableWatches(devices || []);
    } catch (error) {
      console.error('Error loading free devices:', error);
      setFreeDevices([]);
      setAvailableWatches([]);
    }
  };

  const loadPatients = async () => {
    try {
      const patients = await PatientService.getPatients();
      setPatients(patients || []);
    } catch (error) {
      console.error('Error loading patients:', error);
      setPatients([]);
    }
  };

  const loadPoolStatus = async () => {
    try {
      const [availableData, assignedData] = await Promise.all([
        DeviceService.getFreeDevices(currentUser.staffId, 'all', 'all'),
        DeviceService.getAssignmentHistory(currentUser.staffId)
      ]);

      const availableDevicesList = availableData || [];
      const assignedDevicesList = assignedData || [];

      const totalDevices = availableDevicesList.length + assignedDevicesList.length;
      const availableDevices = availableDevicesList.length;
      const assignedDevices = assignedDevicesList.length;
      const offlineDevices = availableDevicesList.filter(d => d.status === 'offline').length;
      const lowBatteryDevices = availableDevicesList.filter(d => d.batteryLevel && d.batteryLevel < 20).length;

      const poolStatusData = {
        summary: {
          totalDevices,
          availableDevices,
          assignedDevices,
          offlineDevices,
          lowBatteryDevices
        }
      };

      setPoolStatus(poolStatusData);
    } catch (error) {
      console.error('Error loading pool status:', error);
    }
  };

  const loadAssignmentHistory = async () => {
    try {
      const data = await DeviceService.getAssignmentHistory(currentUser.staffId, undefined, undefined, 20);
      setAssignedWatches(data || []);
    } catch (error) {
      console.error('Error loading assignment history:', error);
      setAssignedWatches([]);
    }
  };

  const loadAssignedDevices = async () => {
    try {
      const assignedData = await DeviceService.getAssignmentHistory(currentUser.staffId);
      const assignedWithPatients = (assignedData || []).map((assignment: DeviceAssignmentRecord) => ({
        ...assignment,
        patientName: assignment.patientName || 'Unknown Patient',
        location: assignment.location || 'N/A',
        deviceName: assignment.watchDisplay || `Watch ${assignment.serialNumber}`
      }));

      setAssignedDevices(assignedWithPatients);
    } catch (error) {
      console.error('Error loading assigned devices:', error);
    }
  };

  // Device assignment functionality
  const assignDevice = async () => {
    if (!selectedDevice || !selectedPatient) {
      showMessage('Please select both a device and a patient', true);
      return;
    }

    setLoading(true);
    try {
      await DeviceService.assignDevice(currentUser.staffId, selectedDevice, selectedPatient, assignmentReason);
      showMessage('Device assigned successfully!');
      setSelectedDevice('');
      setSelectedPatient('');
      await refreshData();
    } catch (error: any) {
      console.error('Error assigning device:', error);
      showMessage(error.message || 'Assignment failed', true);
    }
    setLoading(false);
  };

  const unassignDevice = async (deviceId: string, reason: string = 'patientDischarge') => {
    if (loading) return;

    setLoading(true);
    try {
      await DeviceService.unassignDevice(currentUser.staffId, deviceId, reason);
      showMessage('Device unassigned successfully!');
      await refreshData();
    } catch (error: any) {
      console.error('Error unassigning device:', error);
      showMessage(error.message || 'Unassignment failed', true);
    }
    setLoading(false);
  };

  const refreshData = async () => {
    setLoading(true);
    await Promise.all([
      loadFreeDevices(),
      loadPatients(),
      loadPoolStatus(),
      loadAssignmentHistory(),
      loadAssignedDevices()
    ]);
    setLoading(false);
  };

  // Filter patients based on search and filters
  const filteredPatients = patients.filter(patient => {
    const matchesSearch = !searchTerm ||
      patient.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      patient.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      patient.bedNumber.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesWard = wardFilter === 'all' || patient.ward === wardFilter;

    const hasDevice = patient.assignedDeviceId != null;
    const matchesAssignment =
      patientFilter === 'all' ||
      (patientFilter === 'assigned' && hasDevice) ||
      (patientFilter === 'unassigned' && !hasDevice);

    return matchesSearch && matchesWard && matchesAssignment;
  });

  // Handle device filter changes
  const handleDeviceFilterChange = (filter: string) => {
    setDeviceFilter(filter);
    loadFreeDevices();
  };

  const handleLocationFilterChange = (filter: string) => {
    setLocationFilter(filter);
    loadFreeDevices();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <DeviceAssignmentHeader
        currentUser={currentUser}
        loading={loading}
        onBack={onBack}
        onRefresh={refreshData}
      />

      <MessageDisplay
        showSuccess={showSuccess}
        error={error}
      />

      <TabNavigation
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Assign Tab */}
        {activeTab === 'assign' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <DeviceSelectionPanel
              devices={freeDevices}
              selectedDevice={selectedDevice}
              deviceFilter={deviceFilter}
              locationFilter={locationFilter}
              onDeviceSelect={setSelectedDevice}
              onDeviceFilterChange={handleDeviceFilterChange}
              onLocationFilterChange={handleLocationFilterChange}
            />

            <PatientSelectionPanel
              patients={filteredPatients}
              selectedPatient={selectedPatient}
              selectedDevice={selectedDevice}
              assignmentReason={assignmentReason}
              searchTerm={searchTerm}
              patientFilter={patientFilter}
              wardFilter={wardFilter}
              loading={loading}
              onPatientSelect={setSelectedPatient}
              onSearchChange={setSearchTerm}
              onPatientFilterChange={setPatientFilter}
              onWardFilterChange={setWardFilter}
              onAssignmentReasonChange={setAssignmentReason}
              onAssign={assignDevice}
            />
          </div>
        )}

        {/* Assigned Devices Tab */}
        {activeTab === 'assigned' && (
          <AssignedDevicesTab
            assignedDevices={assignedDevices}
            loading={loading}
            onUnassign={unassignDevice}
          />
        )}

        {/* Device Pool Tab */}
        {activeTab === 'pool' && (
          <DevicePoolTab
            poolStatus={poolStatus}
            availableWatches={availableWatches}
            assignedWatches={assignedWatches}
            onTabChange={setActiveTab}
          />
        )}
      </div>
    </div>
  );
};