import React from 'react';
import { Watch, Activity, User, Battery } from 'lucide-react';

interface PoolStatus {
  summary: {
    totalDevices: number;
    availableDevices: number;
    assignedDevices: number;
    offlineDevices: number;
    lowBatteryDevices: number;
  };
}

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

interface DevicePoolTabProps {
  poolStatus: PoolStatus | null;
  availableWatches: Device[];
  assignedWatches: DeviceAssignmentRecord[];
  onTabChange: (tab: 'assigned') => void;
}

export const DevicePoolTab: React.FC<DevicePoolTabProps> = ({
  poolStatus,
  availableWatches,
  assignedWatches,
  onTabChange
}) => {
  return (
    <div className="space-y-6">
      {/* Pool Status Summary */}
      {poolStatus && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Device Pool Overview</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">
                {poolStatus.summary?.totalDevices || 0}
              </div>
              <div className="text-sm text-gray-600">Total</div>
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
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Available Devices */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Available Devices ({availableWatches.length})</h2>
            <p className="text-sm text-gray-600 mt-1">Ready for assignment</p>
          </div>

          {availableWatches.length > 0 ? (
            <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
              {availableWatches.map((watch) => (
                <div key={watch.id} className="p-4 hover:bg-gray-50 transition-colors">
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
                          <span className="font-medium text-gray-900">{watch.displayName || `Watch ${watch.serialNumber}`}</span>
                          <span className={`text-xs px-2 py-1 rounded-full ${
                            (watch.connectionStatus || watch.status) === 'connected' ? 'bg-green-100 text-green-800' :
                            (watch.connectionStatus || watch.status) === 'recently_seen' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {watch.connectionStatus || watch.status}
                          </span>
                        </div>
                        <div className="text-sm text-gray-600">{watch.location}</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      {watch.batteryLevel && (
                        <div className="flex items-center space-x-1">
                          <Battery className={`w-4 h-4 ${
                            watch.batteryLevel >= 60 ? 'text-green-500' :
                            watch.batteryLevel >= 30 ? 'text-yellow-500' : 'text-red-500'
                          }`} />
                          <span className="text-xs text-gray-600">{watch.batteryLevel}%</span>
                        </div>
                      )}
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
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
                  onClick={() => onTabChange('assigned')}
                  className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="relative">
                        <Watch className="w-6 h-6 text-green-600" />
                        <div className={`absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-white ${
                          (watch.connectionStatus || watch.status) === 'connected' ? 'bg-green-500' :
                          (watch.connectionStatus || watch.status) === 'recently_seen' ? 'bg-yellow-500' : 'bg-red-500'
                        }`} title={`Status: ${watch.connectionStatus || watch.status}`}></div>
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-gray-900">{watch.watchDisplay || `Watch ${watch.serialNumber}`}</span>
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
                      {watch.batteryLevel && (
                        <div className="flex items-center space-x-1">
                          <Battery className={`w-4 h-4 ${
                            watch.batteryLevel >= 60 ? 'text-green-500' :
                            watch.batteryLevel >= 30 ? 'text-yellow-500' : 'text-red-500'
                          }`} />
                          <span className="text-xs text-gray-600">{watch.batteryLevel}%</span>
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
    </div>
  );
};