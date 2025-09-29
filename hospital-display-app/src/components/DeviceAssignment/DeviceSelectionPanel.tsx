import React from 'react';
import { Activity } from 'lucide-react';
import { DeviceCard } from './DeviceCard';

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

interface DeviceSelectionPanelProps {
  devices: Device[];
  selectedDevice: string;
  deviceFilter: string;
  locationFilter: string;
  onDeviceSelect: (deviceId: string) => void;
  onDeviceFilterChange: (filter: string) => void;
  onLocationFilterChange: (filter: string) => void;
}

export const DeviceSelectionPanel: React.FC<DeviceSelectionPanelProps> = ({
  devices,
  selectedDevice,
  deviceFilter,
  locationFilter,
  onDeviceSelect,
  onDeviceFilterChange,
  onLocationFilterChange
}) => {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        Available Devices ({devices.length})
      </h2>

      {/* Device Filters */}
      <div className="flex space-x-4 mb-4">
        <select
          value={deviceFilter}
          onChange={(e) => onDeviceFilterChange(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md text-sm"
        >
          <option value="all">All Types</option>
          <option value="watch">Watches</option>
          <option value="vitalMonitor">Vital Monitors</option>
        </select>
        <select
          value={locationFilter}
          onChange={(e) => onLocationFilterChange(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md text-sm"
        >
          <option value="all">All Locations</option>
          <option value="ICU">ICU</option>
          <option value="General Ward">General Ward</option>
          <option value="Emergency">Emergency</option>
        </select>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {devices.map((device) => (
          <DeviceCard
            key={device.id}
            device={device}
            isSelected={selectedDevice === device.id}
            onClick={() => onDeviceSelect(device.id)}
            showBattery={true}
          />
        ))}
        {devices.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <Activity className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>No available devices</p>
            <p className="text-sm">All devices are currently assigned</p>
          </div>
        )}
      </div>
    </div>
  );
};