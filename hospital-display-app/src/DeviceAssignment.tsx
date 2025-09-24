import React, { useState, useEffect } from 'react';
import {
  Watch, Activity, User, MapPin, Battery,
  CheckCircle, AlertCircle, X, Plus,
  Search, RefreshCw
} from 'lucide-react';
import { user as UserType, patient } from './types';
import { DeviceService, PatientService } from './services';
// Removed unused imports

interface Device {
  id: string;
  deviceId: string;
  serialnumber: string;
  macaddress: string;
  firmwareversion: string;
  devicetype: string;
  location: string;
  status: string;
  batterylevel: number | null;
  lastseen: string | null;
  assignedpatientId: string | null;
  calibrationdate: string | null;
  nextmaintenancedate: string | null;
  createdat: string;
  updatedat: string;
}

interface DeviceAssignment {
  id: number;
  deviceId: string;
  patientId: string;
  performedby: string;
  assignmentReason: string;
  assignedat: string;
  status: string;
  deviceName: string;
  devicetype: string;
}

interface DeviceAssignmentProps {
  currentUser: UserType;
  onBack: () => void;
}


export const DeviceAssignment: React.FC<DeviceAssignmentProps> = ({ 
  currentUser, 
  onBack 
}) => {
  const [activeTab, setActiveTab] = useState<'assign' | 'assigned' | 'pool'>('assign');
  const [freeDevices, setFreeDevices] = useState<Device[]>([]);
  const [patients, setPatients] = useState<patient[]>([]);
  const [assignments, setAssignments] = useState<DeviceAssignment[]>([]);
  const [assignedDevices, setAssignedDevices] = useState<any[]>([]);
  const [poolStatus, setPoolStatus] = useState<any>(null);
  const [availableWatches, setAvailableWatches] = useState<any[]>([]);
  const [assignedWatches, setAssignedWatches] = useState<any[]>([]);
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
    loadFreeDevices();
    loadPatients();
    loadPoolStatus();
    loadAssignmentHistory();
    loadAssignedDevices();
  }, []);

  const showMessage = (message: string, isError = false) => {
    if (isError) {
      setError(message);
      setTimeout(() => setError(null), 5000);
    } else {
      setShowSuccess(message);
      setTimeout(() => setShowSuccess(null), 3000);
    }
  };

  const loadFreeDevices = async () => {
    try {
      const devicetype = deviceFilter === 'all' ? undefined : deviceFilter;
      const location = locationFilter === 'all' ? undefined : locationFilter;
      
      const data = await DeviceService.getFreeDevices(currentUser.staffId, devicetype, location);
      setFreeDevices(data);
    } catch (error) {
      console.error('Error loading free devices:', error);
      showMessage('Failed to load available devices', true);
    }
  };

  const loadPatients = async () => {
    try {
      const data = await PatientService.getPatients();
      setPatients(data);
      console.log('👥 Loaded patients with device assignments:', data.map((p: any) => `${p.name || p.firstname + ' ' + p.lastname} - Device: ${p.assignedDeviceId || 'None'}`));
    } catch (error) {
      console.error('Error loading patients:', error);
      showMessage('Failed to load patient list', true);
    }
  };

  const loadPoolStatus = async () => {
    try {
      // Get available and assigned watches
      const [availableData, assignedData] = await Promise.all([
        DeviceService.getDevicePoolStatus(currentUser.staffId), // /watch-management/available
        DeviceService.getAssignmentHistory(currentUser.staffId) // /watch-management/assigned
      ]);

      const availableWatchesList = availableData.availableWatches || [];
      const assignedWatchesList = assignedData || [];

      // Store the actual device lists
      setAvailableWatches(availableWatchesList);
      setAssignedWatches(assignedWatchesList);

      // Create pool status summary
      const totalDevices = availableWatchesList.length + assignedWatchesList.length;
      const availableDevices = availableWatchesList.length;
      const assignedDevices = assignedWatchesList.length;
      const offlineDevices = availableWatchesList.filter((w: any) => w.connectionStatus === 'offline').length;
      const lowBatteryDevices = availableWatchesList.filter((w: any) => w.batterylevel && w.batterylevel <= 20).length;

      const poolStatusData = {
        summary: {
          totalDevices,
          availableDevices,
          assignedDevices,
          offlineDevices,
          lowBatteryDevices
        },
        byType: {
          watch: {
            total: totalDevices,
            available: availableDevices,
            assigned: assignedDevices,
            offline: offlineDevices,
            lowBattery: lowBatteryDevices
          }
        }
      };

      setPoolStatus(poolStatusData);
      console.log('🔍 Pool status loaded:', { available: availableWatchesList.length, assigned: assignedWatchesList.length });
    } catch (error) {
      console.error('Error loading pool status:', error);
    }
  };

  const loadAssignmentHistory = async () => {
    try {
      const data = await DeviceService.getAssignmentHistory(currentUser.staffId, undefined, undefined, 20);
      setAssignments(data);
    } catch (error) {
      console.error('Error loading assignment history:', error);
    }
  };

  const loadAssignedDevices = async () => {
    try {
      // Use the same data source as pool status for consistency
      const assignedData = await DeviceService.getAssignmentHistory(currentUser.staffId);
      const activeAssignments = assignedData || [];

      // Backend already includes patient names - use them directly
      const assignedWithPatients = activeAssignments.map((assignment: any) => ({
        ...assignment,
        // Use backend-provided patient data, with fallbacks only if truly missing
        patientName: assignment.patientName || 'Unknown Patient',
        location: assignment.location || 'N/A',
        deviceName: assignment.watchDisplay || `Watch ${assignment.serialnumber}`
      }));

      setAssignedDevices(assignedWithPatients);
      console.log('🔍 Loaded assigned devices with patient names:', assignedWithPatients.map((a: any) => `${a.deviceId || a.id} -> ${a.patientName}`));
    } catch (error) {
      console.error('Error loading assigned devices:', error);
    }
  };

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
      await Promise.all([
        loadFreeDevices(),
        loadPoolStatus(),
        loadAssignmentHistory(),
        loadAssignedDevices()
      ]);
    } catch (error: any) {
      console.error('Error assigning device:', error);
      showMessage(error.message || 'Assignment failed', true);
    }
    setLoading(false);
  };

  const unassignDevice = async (deviceId: string, reason: string = 'patientDischarge') => {
    console.log('🔧 DeviceAssignment.unassignDevice called for device:', deviceId, 'reason:', reason);
    console.trace('Call stack for unassign device');
    
    if (loading) {
      console.log('⚠️ Unassign already in progress, ignoring duplicate call');
      return;
    }
    
    setLoading(true);
    try {
      console.log('🔧 DeviceAssignment: About to call DeviceService.unassignDevice from ADMIN interface');
      await DeviceService.unassignDevice(currentUser.staffId, deviceId, reason);
      showMessage('Device unassigned successfully!');
      await Promise.all([
        loadFreeDevices(),
        loadPoolStatus(),
        loadAssignmentHistory(),
        loadAssignedDevices()
      ]);
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
      loadPoolStatus(),
      loadAssignmentHistory(),
      loadAssignedDevices()
    ]);
    setLoading(false);
  };

  const filteredPatients = patients.filter(patient => {
    // Text search filter
    const matchesSearch = !searchTerm ||
      patient.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      patient.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      patient.bedNumber.toLowerCase().includes(searchTerm.toLowerCase());

    // Ward filter
    const matchesWard = wardFilter === 'all' || patient.ward === wardFilter;

    // Assignment status filter
    const hasDevice = patient.assignedDeviceId != null;
    const matchesAssignment =
      patientFilter === 'all' ||
      (patientFilter === 'assigned' && hasDevice) ||
      (patientFilter === 'unassigned' && !hasDevice);


    return matchesSearch && matchesWard && matchesAssignment;
  });

  const getDeviceIcon = (devicetype: string) => {
    switch (devicetype) {
      case 'watch': return Watch;
      case 'vitalMonitor': return Activity;
      default: return Activity;
    }
  };

  const getBatteryColor = (level: number | null) => {
    if (!level) return 'text-gray-400';
    if (level < 20) return 'text-red-500';
    if (level < 50) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'text-green-500';
      case 'offline': return 'text-red-500';
      case 'maintenance': return 'text-yellow-500';
      default: return 'text-gray-500';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <button
                onClick={onBack}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Device Assignment</h1>
                <p className="text-sm text-gray-600">Manage patient device assignments</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={refreshData}
                disabled={loading}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
              >
                <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
              </button>
              <div className="text-sm text-gray-600">
                Logged in as: <span className="font-medium">{currentUser.name}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Success/Error Messages */}
      {showSuccess && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mx-4 mt-4">
          <CheckCircle className="w-5 h-5 inline mr-2" />
          {showSuccess}
        </div>
      )}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mx-4 mt-4">
          <AlertCircle className="w-5 h-5 inline mr-2" />
          {error}
        </div>
      )}

      {/* Tab Navigation */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'assign', label: 'Assign Device', icon: Plus },
              { id: 'assigned', label: 'Assigned Devices', icon: Watch },
              { id: 'pool', label: 'Device Pool', icon: Activity }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Assign Tab */}
        {activeTab === 'assign' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Device Selection */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Available Devices ({freeDevices.length})
              </h2>
              
              {/* Device Filters */}
              <div className="flex space-x-4 mb-4">
                <select
                  value={deviceFilter}
                  onChange={(e) => { setDeviceFilter(e.target.value); loadFreeDevices(); }}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                >
                  <option value="all">All Types</option>
                  <option value="watch">Watches</option>
                  <option value="vitalMonitor">Vital Monitors</option>
                </select>
                <select
                  value={locationFilter}
                  onChange={(e) => { setLocationFilter(e.target.value); loadFreeDevices(); }}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                >
                  <option value="all">All Locations</option>
                  <option value="ICU">ICU</option>
                  <option value="General Ward">General Ward</option>
                  <option value="Emergency">Emergency</option>
                </select>
              </div>

              <div className="space-y-3 max-h-96 overflow-y-auto">
                {freeDevices.map((device) => {
                  const DeviceIcon = getDeviceIcon(device.devicetype);
                  return (
                    <div
                      key={device.id}
                      onClick={() => setSelectedDevice(device.id)}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                        selectedDevice === device.id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="relative">
                            <DeviceIcon className="w-5 h-5 text-gray-600" />
                            {/* Device Status Dot */}
                            <div className={`absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-white ${
                              device.status === 'online' ? 'bg-green-500' : 'bg-red-500'
                            }`} title={`Status: ${device.status}`}></div>
                          </div>
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="font-medium text-gray-900">{device.serialnumber}</span>
                              <span className={`text-xs px-2 py-1 rounded-full ${
                                device.status === 'online' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                              }`}>
                                {device.status}
                              </span>
                            </div>
                            <div className="text-sm text-gray-600">{device.id}</div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className="flex items-center space-x-1">
                            <MapPin className="w-4 h-4 text-gray-400" />
                            <span className="text-xs text-gray-600">{device.location}</span>
                          </div>
                          {device.batterylevel && (
                            <div className="flex items-center space-x-1">
                              <Battery className={`w-4 h-4 ${getBatteryColor(device.batterylevel)}`} />
                              <span className="text-xs text-gray-600">{device.batterylevel}%</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
                {freeDevices.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <Activity className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                    <p>No available devices</p>
                    <p className="text-sm">All devices are currently assigned</p>
                  </div>
                )}
              </div>
            </div>

            {/* Patient Selection & Assignment */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Select Patient ({filteredPatients.length})
              </h2>
              
              {/* Patient Search and Filters */}
              <div className="mb-4 space-y-3">
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-3 text-gray-400" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search patients by name, ID, or bed..."
                    className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-md"
                  />
                </div>

                {/* Patient Filters */}
                <div className="flex space-x-2">
                  <select
                    value={patientFilter}
                    onChange={(e) => setPatientFilter(e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
                  >
                    <option value="all">All Patients</option>
                    <option value="unassigned">No Device Assigned</option>
                    <option value="assigned">Has Device Assigned</option>
                  </select>
                  <select
                    value={wardFilter}
                    onChange={(e) => setWardFilter(e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
                  >
                    <option value="all">All Wards</option>
                    <option value="ICU">ICU</option>
                    <option value="General Ward">General Ward</option>
                    <option value="Emergency">Emergency</option>
                    <option value="Cardiology">Cardiology</option>
                  </select>
                </div>
              </div>

              {/* Assignment Controls */}
              <div className="mb-4 space-y-3">
                <select
                  value={assignmentReason}
                  onChange={(e) => setAssignmentReason(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="patientAdmission">Patient Admission</option>
                  <option value="deviceReplacement">Device Replacement</option>
                  <option value="additionalMonitoring">Additional Monitoring</option>
                  <option value="transfer">Patient Transfer</option>
                </select>

                <button
                  onClick={assignDevice}
                  disabled={!selectedDevice || !selectedPatient || loading}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-md font-medium disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
                >
                  {loading ? 'Assigning...' : 'Assign Device to Patient'}
                </button>
              </div>

              {/* Patient List */}
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {filteredPatients.map((patient) => (
                  <div
                    key={patient.id}
                    onClick={() => setSelectedPatient(patient.id)}
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      selectedPatient === patient.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="relative">
                          <User className="w-5 h-5 text-gray-600" />
                          {/* Device Assignment Status Dot */}
                          <div className={`absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-white ${
                            patient.assignedDeviceId ? 'bg-green-500' : 'bg-gray-300'
                          }`} title={patient.assignedDeviceId ? 'Has device assigned' : 'No device assigned'}></div>
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="font-medium text-gray-900">{patient.name}</span>
                            {patient.assignedDeviceId && (
                              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                                Device Assigned
                              </span>
                            )}
                          </div>
                          <div className="text-sm text-gray-600">
                            {patient.id} • Bed {patient.bedNumber} • {patient.ward}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className={`px-2 py-1 rounded text-xs font-medium ${
                          patient.status === 'stable' ? 'bg-green-100 text-green-800' :
                          patient.status === 'critical' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {patient.status}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                {filteredPatients.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <User className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                    <p>No patients found</p>
                    <p className="text-sm">Try adjusting your search</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Pool Status Tab */}
        {activeTab === 'pool' && (
          <div className="space-y-6">
            {/* Summary Cards */}
            {poolStatus && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Device Pool Overview</h2>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">
                      {poolStatus.summary?.totalDevices || 0}
                    </div>
                    <div className="text-sm text-gray-600">Total Devices</div>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-green-600">
                      {poolStatus.summary?.availableDevices || 0}
                    </div>
                    <div className="text-sm text-gray-600">Available</div>
                  </div>
                  <div className="bg-yellow-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-yellow-600">
                      {poolStatus.summary?.assigneddevices || 0}
                    </div>
                    <div className="text-sm text-gray-600">Assigned</div>
                  </div>
                  <div className="bg-red-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-red-600">
                      {poolStatus.summary?.offlineDevices || 0}
                    </div>
                    <div className="text-sm text-gray-600">Offline</div>
                  </div>
                  <div className="bg-orange-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-orange-600">
                      {poolStatus.summary?.lowBatteryDevices || 0}
                    </div>
                    <div className="text-sm text-gray-600">Low Battery</div>
                  </div>
                </div>
              </div>
            )}

            {/* Available Devices */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Available Devices ({availableWatches.length})</h2>
                <p className="text-sm text-gray-600 mt-1">Click on a device to view details or assign to a patient</p>
              </div>

              {availableWatches.length > 0 ? (
                <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
                  {availableWatches.map((watch) => (
                    <div
                      key={watch.id}
                      onClick={() => {
                        setSelectedDevice(watch.id);
                        setActiveTab('assign'); // Switch to assignment tab
                      }}
                      className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="relative">
                            <Watch className="w-6 h-6 text-blue-600" />
                            {/* Connection Status Dot */}
                            <div className={`absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-white ${
                              (watch.connectionStatus || watch.status) === 'connected' ? 'bg-green-500' :
                              (watch.connectionStatus || watch.status) === 'recently_seen' ? 'bg-yellow-500' : 'bg-red-500'
                            }`} title={`Status: ${watch.connectionStatus || watch.status}`}></div>
                          </div>
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="font-medium text-gray-900">{watch.displayName || `Watch ${watch.serialnumber}`}</span>
                              <span className={`text-xs px-2 py-1 rounded-full ${
                                (watch.connectionStatus || watch.status) === 'connected' ? 'bg-green-100 text-green-800' :
                                (watch.connectionStatus || watch.status) === 'recently_seen' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-red-100 text-red-800'
                              }`}>
                                {watch.connectionStatus || watch.status}
                              </span>
                            </div>
                            <div className="text-sm text-gray-600">ID: {watch.id}</div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-4">
                          {watch.batterylevel && (
                            <div className="flex items-center space-x-1">
                              <Battery className={`w-4 h-4 ${
                                watch.batterylevel >= 60 ? 'text-green-500' :
                                watch.batterylevel >= 30 ? 'text-yellow-500' : 'text-red-500'
                              }`} />
                              <span className="text-xs text-gray-600">{watch.batterylevel}%</span>
                            </div>
                          )}
                          <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                            Available
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Watch className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p className="text-gray-500 text-lg">No available devices</p>
                  <p className="text-gray-400 text-sm">All devices are currently assigned</p>
                </div>
              )}
            </div>

            {/* Assigned Devices */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Assigned Devices ({assignedWatches.length})</h2>
                <p className="text-sm text-gray-600 mt-1">Currently assigned to patients</p>
              </div>

              {assignedWatches.length > 0 ? (
                <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
                  {assignedWatches.map((watch) => (
                    <div
                      key={watch.id}
                      onClick={() => {
                        setActiveTab('assigned'); // Switch to assignment management tab
                      }}
                      className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="relative">
                            <Watch className="w-6 h-6 text-green-600" />
                            {/* Connection Status Dot */}
                            <div className={`absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-white ${
                              (watch.connectionStatus || watch.status) === 'connected' ? 'bg-green-500' :
                              (watch.connectionStatus || watch.status) === 'recently_seen' ? 'bg-yellow-500' : 'bg-red-500'
                            }`} title={`Status: ${watch.connectionStatus || watch.status}`}></div>
                          </div>
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="font-medium text-gray-900">{watch.watchDisplay || `Watch ${watch.serialnumber}`}</span>
                              <span className={`text-xs px-2 py-1 rounded-full ${
                                (watch.connectionStatus || watch.status) === 'connected' ? 'bg-green-100 text-green-800' :
                                (watch.connectionStatus || watch.status) === 'recently_seen' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-red-100 text-red-800'
                              }`}>
                                {watch.connectionStatus || watch.status}
                              </span>
                            </div>
                            <div className="text-sm text-gray-600">Patient: {watch.patientName}</div>
                            <div className="text-sm text-gray-600">{watch.location}</div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-4">
                          {watch.batterylevel && (
                            <div className="flex items-center space-x-1">
                              <Battery className={`w-4 h-4 ${
                                watch.batterylevel >= 60 ? 'text-green-500' :
                                watch.batterylevel >= 30 ? 'text-yellow-500' : 'text-red-500'
                              }`} />
                              <span className="text-xs text-gray-600">{watch.batterylevel}%</span>
                            </div>
                          )}
                          <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                            Assigned
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <User className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p className="text-gray-500 text-lg">No assigned devices</p>
                  <p className="text-gray-400 text-sm">All devices are available in the pool</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Currently Assigned Devices Tab */}
        {activeTab === 'assigned' && (
          <div className="bg-white rounded-lg shadow">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Currently Assigned Devices</h2>
              <p className="text-sm text-gray-600 mt-1">Devices currently assigned to patients - ready for unassignment on discharge</p>
            </div>
            
            {assignedDevices.length > 0 ? (
              <div className="divide-y divide-gray-200">
                {assignedDevices.map((assignment) => (
                  <div key={assignment.id} className="p-6 hover:bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <div className="flex-shrink-0">
                          <Watch className="w-8 h-8 text-blue-600" />
                        </div>
                        <div>
                          <div className="flex items-center space-x-3">
                            <h3 className="text-lg font-medium text-gray-900">{assignment.deviceName}</h3>
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              Assigned
                            </span>
                          </div>
                          <p className="text-sm text-gray-600">Device ID: {assignment.deviceId}</p>
                        </div>
                      </div>
                      
                      <div className="text-right">
                        <div className="flex items-center space-x-2 mb-2">
                          <User className="w-4 h-4 text-gray-400" />
                          <span className="font-medium text-gray-900">{assignment.patientName}</span>
                        </div>
                        <div className="text-sm text-gray-600">
                          {assignment.location || 'Ward N/A'}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          Assigned: {assignment.assignedat ? new Date(assignment.assignedat).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) + ' • ' + new Date(assignment.assignedat).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : 'Unknown date'}
                        </div>
                      </div>
                      
                      <div className="ml-6">
                        <button
                          onClick={() => {
                            if (window.confirm(`Are you sure you want to unassign this device from ${assignment.patientName}? This will stop monitoring for this patient.`)) {
                              unassignDevice(assignment.deviceId, 'patientDischarge');
                            }
                          }}
                          disabled={loading}
                          className="inline-flex items-center px-3 py-2 border border-red-300 shadow-sm text-sm leading-4 font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                        >
                          <X className="w-4 h-4 mr-1" />
                          Unassign
                        </button>
                        <p className="text-xs text-gray-500 mt-1 text-center">
                          (Patient discharge)
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <Watch className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p className="text-gray-500 text-lg">No devices currently assigned</p>
                <p className="text-gray-400 text-sm">All devices are available in the pool</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};