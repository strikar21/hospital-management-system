/**
 * WatchDetailsModal - Detailed watch information modal
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Shows detailed device information, connection status, and battery
 */

import React from 'react';
import { X, Watch, Battery, Signal, Calendar } from 'lucide-react';
import { patient } from '../types';

interface WatchDetailsModalProps {
  patient: patient;
  onClose: () => void;
}

export const WatchDetailsModal: React.FC<WatchDetailsModalProps> = ({
  patient,
  onClose
}) => {
  if (!patient.assignedDeviceId) return null;

  const getBatteryIcon = (level: number) => {
    if (level > 80) return '🔋';
    if (level > 60) return '🔋';
    if (level > 40) return '🔋';
    if (level > 20) return '⚡';
    return '🪫';
  };

  const getTimeSinceLastSeen = (lastSeen?: string) => {
    if (!lastSeen) return 'Unknown';
    const now = new Date();
    const then = new Date(lastSeen);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Watch className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Watch Details</h2>
              <p className="text-sm text-gray-600">{patient.assignedDeviceId}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Close"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Patient Info */}
        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Assigned Patient</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-600">Name:</span>{' '}
              <span className="text-gray-900">{patient.name}</span>
            </div>
            <div>
              <span className="font-medium text-gray-600">Location:</span>{' '}
              <span className="text-gray-900">
                {patient.roomNumber}, Bed {patient.bedNumber}
              </span>
            </div>
            <div>
              <span className="font-medium text-gray-600">Department:</span>{' '}
              <span className="text-gray-900">{patient.department}</span>
            </div>
            <div>
              <span className="font-medium text-gray-600">Ward:</span>{' '}
              <span className="text-gray-900">{patient.ward}</span>
            </div>
          </div>
        </div>

        {/* Device Status */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Signal className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-medium text-gray-600">Connection</span>
            </div>
            <div className={`text-lg font-bold ${
              patient.deviceStatus === 'connected'
                ? 'text-green-600'
                : 'text-amber-600'
            }`}>
              {patient.deviceStatus === 'connected' ? 'Connected' : 'Disconnected'}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {getTimeSinceLastSeen(patient.deviceLastSeen)}
            </div>
          </div>

          <div className="bg-green-50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Battery className="w-4 h-4 text-green-600" />
              <span className="text-xs font-medium text-gray-600">Battery</span>
            </div>
            <div className={`text-lg font-bold ${
              (patient.deviceBatteryLevel || 0) <= 20 ? 'text-red-600' :
              (patient.deviceBatteryLevel || 0) <= 40 ? 'text-amber-600' :
              'text-green-600'
            }`}>
              {getBatteryIcon(patient.deviceBatteryLevel || 0)} {patient.deviceBatteryLevel || '--'}%
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {(patient.deviceBatteryLevel || 0) <= 20 ? 'Critical' :
               (patient.deviceBatteryLevel || 0) <= 40 ? 'Low' : 'Good'}
            </div>
          </div>

          <div className="bg-purple-50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Calendar className="w-4 h-4 text-purple-600" />
              <span className="text-xs font-medium text-gray-600">Last Seen</span>
            </div>
            <div className="text-lg font-bold text-purple-600">
              {patient.deviceLastSeen
                ? new Date(patient.deviceLastSeen).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })
                : '--:--'}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {patient.deviceLastSeen
                ? new Date(patient.deviceLastSeen).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric'
                  })
                : 'Unknown'}
            </div>
          </div>
        </div>

        {/* Device Technical Details */}
        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">📋 Device Specifications</h3>
          <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div>
              <span className="font-medium text-gray-600">Serial Number:</span>{' '}
              <span className="text-gray-900 font-mono text-xs">{patient.deviceSerialNumber || '--'}</span>
            </div>
            <div>
              <span className="font-medium text-gray-600">Device Name:</span>{' '}
              <span className="text-gray-900">{patient.deviceName || '--'}</span>
            </div>
            <div>
              <span className="font-medium text-gray-600">MAC Address:</span>{' '}
              <span className="text-gray-900 font-mono text-xs">{patient.deviceMacAddress || '--'}</span>
            </div>
            <div>
              <span className="font-medium text-gray-600">Firmware Version:</span>{' '}
              <span className="text-gray-900">{patient.deviceFirmwareVersion || '--'}</span>
            </div>
            {patient.deviceModel && (
              <div>
                <span className="font-medium text-gray-600">Model:</span>{' '}
                <span className="text-gray-900">{patient.deviceModel}</span>
              </div>
            )}
            {patient.deviceManufacturer && (
              <div>
                <span className="font-medium text-gray-600">Manufacturer:</span>{' '}
                <span className="text-gray-900">{patient.deviceManufacturer}</span>
              </div>
            )}
            <div>
              <span className="font-medium text-gray-600">Location:</span>{' '}
              <span className="text-gray-900">{patient.deviceLocation || '--'}</span>
            </div>
            <div>
              <span className="font-medium text-gray-600">Assigned:</span>{' '}
              <span className="text-gray-900">
                {patient.deviceAssignedAt
                  ? new Date(patient.deviceAssignedAt).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric'
                    })
                  : '--'}
              </span>
            </div>
          </div>
        </div>

        {/* Maintenance Info (if available) */}
        {(patient.deviceCalibrationDate || patient.deviceNextMaintenanceDate) && (
          <div className="bg-amber-50 rounded-lg p-4 mb-6">
            <h3 className="text-sm font-semibold text-amber-800 mb-3">🔧 Maintenance Schedule</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              {patient.deviceCalibrationDate && (
                <div>
                  <span className="font-medium text-gray-600">Last Calibration:</span>{' '}
                  <span className="text-gray-900">
                    {new Date(patient.deviceCalibrationDate).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric'
                    })}
                  </span>
                </div>
              )}
              {patient.deviceNextMaintenanceDate && (
                <div>
                  <span className="font-medium text-gray-600">Next Maintenance:</span>{' '}
                  <span className="text-gray-900">
                    {new Date(patient.deviceNextMaintenanceDate).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric'
                    })}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
