import React, { useState, useEffect } from 'react';
import { 
  Watch, Activity, User, MapPin, Battery, Wifi, WifiOff, 
  CheckCircle, AlertCircle, Clock, RotateCcw, X, Plus,
  Search, Filter, RefreshCw
} from 'lucide-react';
import { User as UserType, Patient } from './types';
import { HospitalAPI } from './api';

interface Device {
  deviceId: string;
  name: string;
  deviceType: string;
  location: string;
  status: string;
  batteryLevel: number | null;
  lastHeartbeat: string | null;
  assignmentStatus?: string;
  assignedTo?: string;
  assignedAt?: string;
}

interface DeviceAssignment {
  id: number;
  deviceId: string;
  patientId: string;
  performedBy: string;
  assignmentReason: string;
  assignedAt: string;
  status: string;
  deviceName: string;
  deviceType: string;
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
  const [patients, setPatients] = useState<Patient[]>([]);
  const [assignments, setAssignments] = useState<DeviceAssignment[]>([]);
  const [assignedDevices, setAssignedDevices] = useState<any[]>([]);
  const [poolStatus, setPoolStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<string>('');
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [assignmentReason, setAssignmentReason] = useState('patientAdmission');
  const [deviceFilter, setDeviceFilter] = useState('all');
  const [locationFilter, setLocationFilter] = useState('all');
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
      const deviceType = deviceFilter === 'all' ? undefined : deviceFilter;
      const location = locationFilter === 'all' ? undefined : locationFilter;
      
      const data = await HospitalAPI.getFreeDevices(currentUser.staffId, deviceType, location);
      setFreeDevices(data);
    } catch (error) {
      console.error('Error loading free devices:', error);
      showMessage('Failed to load available devices', true);
    }
  };

  const loadPatients = async () => {
    try {
      const data = await HospitalAPI.getPatients();
      setPatients(data);
    } catch (error) {
      console.error('Error loading patients:', error);
      showMessage('Failed to load patient list', true);
    }
  };

  const loadPoolStatus = async () => {
    try {
      const data = await HospitalAPI.getDevicePoolStatus(currentUser.staffId);
      setPoolStatus(data);
    } catch (error) {
      console.error('Error loading pool status:', error);
    }
  };

  const loadAssignmentHistory = async () => {
    try {
      const data = await HospitalAPI.getAssignmentHistory(currentUser.staffId, undefined, undefined, 20);
      setAssignments(data);
    } catch (error) {
      console.error('Error loading assignment history:', error);
    }
  };

  const loadAssignedDevices = async () => {
    try {
      // Get all active assignments
      const allAssignments = await HospitalAPI.getAssignmentHistory(currentUser.staffId, undefined, undefined, 100);
      const activeAssignments = allAssignments.filter(assignment => assignment.status === 'active');
      
      // Enhance with patient names
      const assignedWithPatients = await Promise.all(
        activeAssignments.map(async (assignment) => {
          const patient = patients.find(p => p.id === assignment.patientId);
          return {
            ...assignment,
            patientName: patient?.name || 'Unknown Patient',
            patientBed: patient?.bedNumber || 'N/A',
            patientWard: patient?.ward || 'N/A'
          };
        })
      );
      
      setAssignedDevices(assignedWithPatients);
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
      await HospitalAPI.assignDevice(currentUser.staffId, selectedDevice, selectedPatient, assignmentReason);
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
    setLoading(true);
    try {
      await HospitalAPI.unassignDevice(currentUser.staffId, deviceId, reason);
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

  const filteredPatients = patients.filter(patient =>
    patient.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    patient.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    patient.bedNumber.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getDeviceIcon = (deviceType: string) => {
    switch (deviceType) {
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
                  const DeviceIcon = getDeviceIcon(device.deviceType);
                  return (
                    <div
                      key={device.deviceId}
                      onClick={() => setSelectedDevice(device.deviceId)}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                        selectedDevice === device.deviceId
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <DeviceIcon className="w-5 h-5 text-gray-600" />
                          <div>
                            <div className="font-medium text-gray-900">{device.name}</div>
                            <div className="text-sm text-gray-600">{device.deviceId}</div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className="flex items-center space-x-1">
                            <MapPin className="w-4 h-4 text-gray-400" />
                            <span className="text-xs text-gray-600">{device.location}</span>
                          </div>
                          {device.status === 'online' ? (
                            <Wifi className="w-4 h-4 text-green-500" />
                          ) : (
                            <WifiOff className="w-4 h-4 text-red-500" />
                          )}
                          {device.batteryLevel && (
                            <div className="flex items-center space-x-1">
                              <Battery className={`w-4 h-4 ${getBatteryColor(device.batteryLevel)}`} />
                              <span className="text-xs text-gray-600">{device.batteryLevel}%</span>
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
                Select Patient
              </h2>
              
              {/* Patient Search */}
              <div className="mb-4">
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
                        <User className="w-5 h-5 text-gray-600" />
                        <div>
                          <div className="font-medium text-gray-900">{patient.name}</div>
                          <div className="text-sm text-gray-600">
                            {patient.id} • Bed {patient.bedNumber} • {patient.ward}
                          </div>
                        </div>
                      </div>
                      <div className={`px-2 py-1 rounded text-xs font-medium ${
                        patient.status === 'stable' ? 'bg-green-100 text-green-800' :
                        patient.status === 'critical' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {patient.status}
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
          <div className="bg-white rounded-lg shadow">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Device Pool Overview</h2>
            </div>
            
            {poolStatus && (
              <div className="p-6">
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
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
                      {poolStatus.summary?.assignedDevices || 0}
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

                {/* Device Type Breakdown */}
                <div className="space-y-4">
                  <h3 className="text-lg font-medium text-gray-900">By Device Type</h3>
                  {Object.entries(poolStatus.byType || {}).map(([deviceType, stats]: [string, any]) => (
                    <div key={deviceType} className="border rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <h4 className="font-medium capitalize">{deviceType.replace('_', ' ')}s</h4>
                        <div className="text-sm text-gray-600">
                          {stats.available} of {stats.total} available
                        </div>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-green-500 h-2 rounded-full"
                          style={{ width: `${(stats.available / stats.total) * 100}%` }}
                        ></div>
                      </div>
                      <div className="flex justify-between text-xs text-gray-600 mt-1">
                        <span>Available: {stats.available}</span>
                        <span>Assigned: {stats.assigned}</span>
                        <span>Offline: {stats.offline}</span>
                        <span>Low Battery: {stats.lowBattery}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
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
                          Bed {assignment.patientBed} • {assignment.patientWard}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          Assigned: {new Date(assignment.assignedAt).toLocaleDateString()} at {new Date(assignment.assignedAt).toLocaleTimeString()}
                        </div>
                      </div>
                      
                      <div className="ml-6">
                        <button
                          onClick={() => unassignDevice(assignment.deviceId, 'patientDischarge')}
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