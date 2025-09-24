// Header.tsx - Compact Header Component with Settings and Auto-logout Integration

import React from 'react';
import { Tablet, MapPin, Wifi, WifiOff, Clock, RefreshCw, LogOut, Activity, Settings, Watch, UserPlus, Plus, Users } from 'lucide-react';
import { user, roomproximity, patient, appsettings } from './types';
import { isNurseOrTechnician } from './utils';

interface HeaderProps {
  currentUser: user;
  isOnline: boolean;
  lastsync: Date;
  roomProximity: roomproximity | null;
  proximityScanning: boolean;
  showAllDepartments: boolean;
  loading: boolean;
  selectedWard: string;
  patients: patient[];
  settings: appsettings;
  getWardOptions: () => string[];
  onWardChange: (ward: string) => void;
  onDetectProximity: () => void;
  onToggleReferralMode: () => void;
  onRefreshData: () => void;
  onShowSettings: () => void;
  onShowDeviceAssignment?: () => void;
  onShowPatientAdmission?: () => void;
  onShowDeviceProvisioning?: () => void;
  onShowNurseAdmission?: () => void;
  onShowStaffManagement?: () => void;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentUser,
  isOnline,
  lastsync,
  roomProximity,
  proximityScanning,
  showAllDepartments,
  loading,
  selectedWard,
  patients,
  settings,
  getWardOptions,
  onWardChange,
  onDetectProximity,
  onToggleReferralMode,
  onRefreshData,
  onShowSettings,
  onShowDeviceAssignment,
  onShowPatientAdmission,
  onShowDeviceProvisioning,
  onShowNurseAdmission,
  onShowStaffManagement,
  onLogout
}) => {
  const getCurrentWardInfo = () => {
    if (isNurseOrTechnician(currentUser.role) && roomProximity) {
      return `Room ${roomProximity.roomNumber} (${roomProximity.patientsInRoom.length} patients detected)`;
    } else if (isNurseOrTechnician(currentUser.role)) {
      return 'Detecting room location...';
    }
    return currentUser.department;
  };

  return (
    <header className="bg-white shadow-sm border-b">
      <div className="px-4 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-3">
              <div className="bg-blue-600 p-1.5 rounded-lg">
                <Tablet className="w-4 h-4 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900">
                  {settings.bedsidemode ? 'Bedside Monitor Mode' : 'Hospital Display System'}
                </h1>
                <p className="text-xs text-gray-600">
                  Welcome, {currentUser.name} ({currentUser.role}) - {currentUser.department}
                </p>
              </div>
            </div>

            {/* Ward Filter integrated in header */}
            <div className="flex items-center space-x-3 border-l pl-4">
              {!isNurseOrTechnician(currentUser.role) ? (
                <div className="flex items-center space-x-1.5">
                  <label className="text-xs font-medium text-gray-700">View:</label>
                  <select
                    value={selectedWard}
                    onChange={(e) => onWardChange(e.target.value)}
                    className="px-2 py-1 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-xs"
                  >
                    {getWardOptions().map(option => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </div>
              ) : (
                <div className={`flex items-center space-x-1.5 px-2 py-1 rounded-lg text-xs ${
                  roomProximity 
                    ? 'bg-green-50 border border-green-200 text-green-800' 
                    : 'bg-orange-50 border border-orange-200 text-orange-800'
                }`}>
                  <Activity className={`w-3 h-3 ${proximityScanning ? 'animate-pulse' : ''}`} />
                  <span className="font-medium">
                    {roomProximity 
                      ? `Room ${roomProximity.roomNumber}`
                      : 'Detecting...'
                    }
                  </span>
                </div>
              )}
              
              {/* Patient Count */}
              <div className="flex items-center space-x-1.5">
                <span className="text-xs text-gray-600">Patients:</span>
                <span className="bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded-full text-xs font-medium">
                  {patients.length}
                </span>
                {patients.length > 6 && (
                  <span className="text-xs text-gray-500">(Auto-scrolling)</span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* Bedside Mode Indicator */}
            {settings.bedsidemode && (
              <div className="flex items-center space-x-1.5 text-xs px-2 py-1 rounded-lg bg-purple-100 border border-purple-300 text-purple-700">
                <div className="w-1.5 h-1.5 bg-purple-600 rounded-full animate-pulse"></div>
                <span className="font-medium">Bedside Active</span>
              </div>
            )}

            {/* Room Proximity Detection Status */}
            <div className={`flex items-center space-x-1.5 text-xs px-2 py-1 rounded-lg border ${
              isNurseOrTechnician(currentUser.role)
                ? roomProximity 
                  ? 'text-green-700 bg-green-100 border-green-300' 
                  : proximityScanning
                  ? 'text-blue-700 bg-blue-100 border-blue-300'
                  : 'text-orange-700 bg-orange-100 border-orange-300'
                : 'text-gray-600 bg-gray-100 border-gray-300'
            }`}>
              <MapPin className={`w-3 h-3 ${proximityScanning ? 'animate-pulse' : ''}`} />
              <div>
                <span className="font-medium">
                  {isNurseOrTechnician(currentUser.role)
                    ? roomProximity 
                      ? `📍 Room ${roomProximity.roomNumber}`
                      : proximityScanning
                      ? '🔍 Detecting...'
                      : '⚠️ Unknown'
                    : `Current: ${getCurrentWardInfo()}`
                  }
                </span>
              </div>
            </div>

            {/* Manual Proximity Detection */}
            {isNurseOrTechnician(currentUser.role) && (
              <button
                onClick={onDetectProximity}
                disabled={proximityScanning}
                className={`flex items-center space-x-1.5 px-2 py-1 rounded-lg text-xs font-medium transition-colors ${
                  proximityScanning
                    ? 'bg-blue-400 text-white cursor-not-allowed'
                    : 'bg-indigo-600 text-white hover:bg-indigo-700'
                }`}
              >
                {proximityScanning ? (
                  <>
                    <RefreshCw className="w-3 h-3 animate-spin" />
                    <span>Scanning...</span>
                  </>
                ) : (
                  <>
                    <Activity className="w-3 h-3" />
                    <span>Detect</span>
                  </>
                )}
              </button>
            )}

            {/* Network Status */}
            <div className={`flex items-center space-x-1 ${isOnline ? 'text-green-600' : 'text-red-600'}`}>
              {isOnline ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
              <span className="text-xs">{isOnline ? 'Online' : 'Offline'}</span>
            </div>

            {/* Last Sync */}
            <div className="text-xs text-gray-500">
              <Clock className="w-3 h-3 inline mr-1" />
              Synced: {lastsync.toLocaleTimeString()}
            </div>

            {/* Referral Mode Toggle (Doctors only) */}
            {currentUser.role === 'Doctor' && (
              <button
                onClick={onToggleReferralMode}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                  showAllDepartments
                    ? 'bg-orange-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {showAllDepartments ? 'Exit' : 'Enter'} Referral Mode
              </button>
            )}

            {/* Patient Admission Button (Doctors only) */}
            {(currentUser.role === 'Doctor' || currentUser.role === 'Administrator') && onShowPatientAdmission && (
              <button
                onClick={onShowPatientAdmission}
                className="flex items-center space-x-1.5 px-2 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                title="Create Admission Recommendation"
              >
                <UserPlus className="w-3 h-3" />
                <span className="text-xs font-medium">Recommend</span>
              </button>
            )}

            {/* Nurse Admission Processing Button (Nurses only) */}
            {(currentUser.role === 'Nurse') && onShowNurseAdmission && (
              <button
                onClick={onShowNurseAdmission}
                className="flex items-center space-x-1.5 px-2 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                title="Process Admission Recommendations"
              >
                <Plus className="w-3 h-3" />
                <span className="text-xs font-medium">Admit</span>
              </button>
            )}

            {/* Device Assignment Button (Nurses only) */}
            {(isNurseOrTechnician(currentUser.role) || currentUser.role === 'Administrator') && onShowDeviceAssignment && (
              <button
                onClick={onShowDeviceAssignment}
                className="flex items-center space-x-1.5 px-2 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                title="Manage Device Assignments"
              >
                <Watch className="w-3 h-3" />
                <span className="text-xs font-medium">Assign</span>
              </button>
            )}

            {/* Device Provisioning Button (Tech staff only) */}
            {(currentUser.role === 'Technician' || currentUser.role === 'Administrator') && onShowDeviceProvisioning && (
              <button
                onClick={onShowDeviceProvisioning}
                className="flex items-center space-x-1.5 px-2 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                title="Add New Devices"
              >
                <Plus className="w-3 h-3" />
                <span className="text-xs font-medium">Provision</span>
              </button>
            )}

            {/* Staff Management Button (Provisioner and Administrator only) */}
            {(currentUser.role === 'Provisioner' || currentUser.role === 'Administrator') && onShowStaffManagement && (
              <button
                onClick={onShowStaffManagement}
                className="flex items-center space-x-1.5 px-2 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                title="Manage Staff Members"
              >
                <Users className="w-3 h-3" />
                <span className="text-xs font-medium">Staff</span>
              </button>
            )}

            {/* Settings Button */}
            <button
              onClick={onShowSettings}
              className="p-1.5 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              title="System Settings"
            >
              <Settings className="w-4 h-4" />
            </button>

            {/* Refresh Button */}
            <button
              onClick={onRefreshData}
              disabled={loading}
              className="p-1.5 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>

            {/* Logout */}
            <button
              onClick={onLogout}
              className="flex items-center space-x-1.5 px-3 py-1 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              <LogOut className="w-3 h-3" />
              <span className="text-xs">Logout</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};