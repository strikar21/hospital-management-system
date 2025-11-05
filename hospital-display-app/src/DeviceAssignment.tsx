import React, { useState, useEffect } from 'react';
import { user as UserType, patient, device, deviceAssignmentRecord, poolStatus } from './types';
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
  const [freeDevices, setFreeDevices] = useState<device[]>([]);
  const [patients, setPatients] = useState<patient[]>([]);
  const [assignedDevices, setAssignedDevices] = useState<deviceAssignmentRecord[]>([]);
  const [poolStatus, setPoolStatus] = useState<poolStatus | null>(null);
  const [availableWatches, setAvailableWatches] = useState<device[]>([]);
  const [assignedWatches, setAssignedWatches] = useState<deviceAssignmentRecord[]>([]);
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
      // Error handled silently
      setFreeDevices([]);
      setAvailableWatches([]);
    }
  };

  const loadPatients = async () => {
    try {
      const patients = await PatientService.getPatients();
      setPatients(patients || []);
    } catch (error) {
      // Error handled silently
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
      // Error handled silently
    }
  };

  const loadAssignmentHistory = async () => {
    try {
      const data = await DeviceService.getAssignmentHistory(currentUser.staffId, undefined, undefined, 20);
      setAssignedWatches(data || []);
    } catch (error) {
      // Error handled silently
      setAssignedWatches([]);
    }
  };

  const loadAssignedDevices = async () => {
    try {
      const assignedData = await DeviceService.getAssignmentHistory(currentUser.staffId);

      // Filter out inactive assignments (safety net - backend should already filter)
      const activeOnly = (assignedData || []).filter((assignment: deviceAssignmentRecord) =>
        assignment.status === 'active' && assignment.patientId
      );

      const assignedWithPatients = activeOnly.map((assignment: deviceAssignmentRecord) => ({
        ...assignment,
        patientName: assignment.patientName || 'Unknown Patient',
        location: assignment.location || 'N/A',
        deviceName: assignment.watchDisplay || `Watch ${assignment.serialNumber}`
      }));

      setAssignedDevices(assignedWithPatients);
    } catch (error) {
      // Error handled silently
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
      // Error handled silently
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
      // Error handled silently
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