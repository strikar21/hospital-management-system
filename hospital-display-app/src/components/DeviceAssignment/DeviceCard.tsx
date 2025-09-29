import React from 'react';
import { Watch, Activity, MapPin, Battery } from 'lucide-react';

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

interface DeviceCardProps {
  device: Device;
  isSelected?: boolean;
  onClick?: () => void;
  showBattery?: boolean;
}

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

export const DeviceCard: React.FC<DeviceCardProps> = ({
  device,
  isSelected = false,
  onClick,
  showBattery = true
}) => {
  const DeviceIcon = getDeviceIcon(device.deviceType);

  return (
    <div
      onClick={onClick}
      className={`p-3 border rounded-lg transition-colors ${
        onClick ? 'cursor-pointer' : ''
      } ${
        isSelected
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
              <span className="font-medium text-gray-900">
                {device.displayName || device.serialNumber}
              </span>
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
          {showBattery && device.batteryLevel && (
            <div className="flex items-center space-x-1">
              <Battery className={`w-4 h-4 ${getBatteryColor(device.batteryLevel)}`} />
              <span className="text-xs text-gray-600">{device.batteryLevel}%</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};